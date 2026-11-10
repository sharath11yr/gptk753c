"""Growth mode: videos on what people are searching for right now in the channel's field
(e.g. "how to install kali linux", "python roadmap 2026", "how does 5g work").

Each run gathers live YouTube search suggestions (autocomplete) for the channel's seed
searches, scores the phrases (how often and how high they appear), drops anything already
made, lets the AI pick the strongest video idea, writes an in-depth script, fact-checks
it and packages it professionally. Topics are never repeated (state/search_topics_used.json).
Set CONTENT_MODE=courses (or electronics) to go back to the courses later.
"""

import datetime as dt
import json
import logging
import os
import re
from pathlib import Path

from pipeline import llm
from pipeline.packaging import search_suggestions

log = logging.getLogger(__name__)
USED_FILE = Path("state/search_topics_used.json")

DOMAINS = {
    "cybersec": {
        "about": "cybersecurity and ethical hacking (legal, educational, defensive mindset)",
        "seeds": ["kali linux", "how to install kali linux", "ethical hacking", "how hackers",
                  "nmap", "wireshark", "metasploit", "burp suite", "cybersecurity roadmap",
                  "how to become ethical hacker", "bug bounty", "tryhackme", "hack the box",
                  "password cracking", "phishing", "wifi hacking", "osint", "ctf for beginners",
                  "linux for hackers", "vpn", "is my phone hacked", "cybersecurity jobs",
                  "comptia security+", "ceh", "ransomware", "dark web", "sql injection",
                  "hashcat", "hydra", "john the ripper", "nmap tutorial", "metasploit tutorial",
                  "sqlmap", "aircrack-ng", "gobuster", "burp suite tutorial", "wireshark tutorial",
                  "kali linux tools", "password attacks", "cyber security course"],
        "safety": "Teach only legal, ethical use on your own lab or with permission. Never "
                  "give steps to attack real people or systems; focus on how it works and "
                  "how to defend.",
    },
    "cse": {
        "about": "programming, computer science, AI and developer careers",
        "seeds": ["python", "learn python", "java", "javascript", "dsa", "leetcode",
                  "how to learn coding", "coding roadmap", "web development", "react",
                  "chatgpt", "ai agents", "machine learning", "how to get a job as software engineer",
                  "git and github", "sql", "linux commands", "system design", "c programming",
                  "best programming language", "how computers work", "how ai works",
                  "placement preparation", "projects for resume", "vs code",
                  "python tutorial", "python for beginners", "python course", "java tutorial",
                  "java course", "c programming tutorial", "dsa course", "oops concepts",
                  "sql tutorial", "operating system", "computer networks", "dbms"],
        "safety": "",
    },
    "ece": {
        "about": "electronics, electrical engineering and how technology works",
        "seeds": ["how does", "how it works", "electronics", "arduino", "arduino projects",
                  "esp32", "raspberry pi", "how phone charger works", "how 5g works",
                  "how solar panel works", "electric car battery", "semiconductor",
                  "how chips are made", "pcb design", "transistor", "inverter",
                  "electronics projects", "ece projects", "vlsi", "embedded systems",
                  "how wifi works", "how batteries work", "motor",
                  "filters in electronics", "rectifier", "clipper circuit", "clamper circuit",
                  "zener diode", "diode", "voltage regulator", "bjt transistor", "mosfet",
                  "op amp", "oscillator", "amplifier", "analog electronics",
                  "digital electronics", "logic gates", "flip flop", "multiplexer",
                  "network theory", "signals and systems", "power electronics"],
        "safety": "Include electrical safety where relevant.",
    },
}

SYSTEM = (
    "You are the head writer of a fast-growing, professional educational YouTube channel. "
    "You make videos on exactly what people search for, accurate and in depth, with a hook "
    "that keeps viewers watching to the end."
)

VISUAL_STYLE = (
    "Animate the whole video as a premium, modern explainer: smooth motion graphics, "
    "animated diagrams that build step by step, realistic screens and terminals where "
    "relevant, cutaways and zoom-ins, clear labels and arrows. Every scene moves - no still "
    "slides. On-screen text only for the title and short labels. No logos or brand names."
)


def _domain() -> dict:
    return DOMAINS[os.getenv("SEARCH_DOMAIN") or DEFAULT_DOMAIN]


DEFAULT_DOMAIN = "cse"


def used() -> list[str]:
    return json.loads(USED_FILE.read_text()) if USED_FILE.exists() else []


def mark_used(topic: str) -> None:
    USED_FILE.parent.mkdir(parents=True, exist_ok=True)
    USED_FILE.write_text(json.dumps(used() + [topic], indent=1, ensure_ascii=False))


_CHANNEL: dict = {}


def channel_videos() -> dict:
    """The channel's real long videos from YouTube: {"titles": [...], "winners": [(views, title)]}.
    Winners = most-viewed videos; new topics follow what this audience already watches."""
    if _CHANNEL:
        return _CHANNEL
    titles, winners = [], []
    try:
        from pipeline.youtube_upload import _client
        yt = _client()
        up = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0][
            "contentDetails"]["relatedPlaylists"]["uploads"]
        ids, tok = [], None
        while len(ids) < 200:
            r = yt.playlistItems().list(part="contentDetails", playlistId=up, maxResults=50,
                                        pageToken=tok).execute()
            ids += [i["contentDetails"]["videoId"] for i in r["items"]]
            tok = r.get("nextPageToken")
            if not tok:
                break
        for i in range(0, len(ids), 50):
            for v in yt.videos().list(part="snippet,statistics,contentDetails",
                                      id=",".join(ids[i:i + 50])).execute()["items"]:
                t = v["snippet"]["title"]
                titles.append(t)
                if "M" in v["contentDetails"]["duration"] or "H" in v["contentDetails"]["duration"]:
                    if "#shorts" not in t.lower():
                        winners.append((int(v["statistics"].get("viewCount", 0)), t))
        winners = [w for w in sorted(winners, reverse=True)[:12] if w[0] >= 20]
        log.info("Channel winners: %s", "; ".join(f"{t[:50]} ({n})" for n, t in winners[:6]))
    except Exception as exc:
        log.warning("Could not read the channel's videos: %s", exc)
    _CHANNEL.update({"titles": titles, "winners": winners})
    return _CHANNEL


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9+#]+", s.lower()) if len(w) > 2}


_CANDS: list = []


def candidates() -> list[tuple[str, float]]:
    """Live search phrases with a popularity score (higher = searched more)."""
    if _CANDS:
        return _CANDS
    scores: dict[str, float] = {}
    for seed in _domain()["seeds"]:
        for rank, phrase in enumerate(search_suggestions(seed, limit=10)):
            scores[phrase] = scores.get(phrase, 0) + (10 - rank)
    done = [_words(u) for u in _made_before() + channel_videos()["titles"]]
    out = []
    for phrase, score in scores.items():
        w = _words(phrase)
        if len(w) < 2 or any(len(w & d) >= max(2, len(w) - 1) for d in done):
            continue  # too vague, or already made
        out.append((phrase, score))
    _CANDS.extend(sorted(out, key=lambda x: -x[1])[:60])
    return _CANDS


LOW_DEMAND_FILE = Path("state/low_demand.json")


def search_demand(phrase: str) -> int | None:
    """How big the audience for a search is. YouTube doesn't publish search counts, so we use
    the next best proof: the median views of the top 10 YouTube results for that phrase.
    Many people search it -> the top results have many views. None = could not check."""
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return _demand_from_page(phrase)
    import httpx
    try:
        r = httpx.get("https://www.googleapis.com/youtube/v3/search", timeout=30, params={
            "part": "id", "q": phrase, "type": "video", "maxResults": 10,
            "relevanceLanguage": "en", "key": key})
        r.raise_for_status()
        ids = [i["id"]["videoId"] for i in r.json().get("items", [])]
        if not ids:
            return 0
        r = httpx.get("https://www.googleapis.com/youtube/v3/videos", timeout=30, params={
            "part": "statistics", "id": ",".join(ids), "key": key})
        r.raise_for_status()
        views = sorted(int(v["statistics"].get("viewCount", 0)) for v in r.json()["items"])
        return views[len(views) // 2] if views else 0
    except Exception as exc:
        log.warning("Could not check search demand for '%s': %s", phrase, exc)
        return None


def _demand_from_page(phrase: str) -> int | None:
    """Same measure without an API key: read the view counts on YouTube's public search page."""
    import httpx
    try:
        r = httpx.get("https://www.youtube.com/results", timeout=30, follow_redirects=True,
                      params={"search_query": phrase, "sp": "EgIQAQ%3D%3D", "hl": "en", "gl": "US"},
                      headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                               "Accept-Language": "en-US,en;q=0.9"},
                      cookies={"CONSENT": "YES+1", "SOCS": "CAI"})
        r.raise_for_status()
        counts = [int(n.replace(",", "")) for n in re.findall(
            r'"viewCountText":\{"simpleText":"([\d,]+) views"', r.text)][:10]
        if not counts:
            log.warning("No view counts on the YouTube search page for '%s'", phrase)
            return None
        counts.sort()
        return counts[len(counts) // 2]
    except Exception as exc:
        log.warning("Could not read the YouTube search page for '%s': %s", phrase, exc)
        return None


_STOP = {"the", "and", "for", "how", "what", "why", "with", "your", "you", "are", "does",
         "work", "works", "explained", "tutorial", "beginners", "beginner", "guide", "complete",
         "full", "course", "simple", "simply", "step", "from", "into", "that", "this", "best",
         "2024", "2025", "2026", "part", "basics", "introduction", "learn", "real", "method"}


def _key(s: str) -> set[str]:
    return _words(s) - _STOP


def already_made(pick: dict) -> str | None:
    """The existing topic/video this pick repeats, or None. Checked in code, not left to the AI."""
    new = _key(pick.get("topic", "")) | _key(pick.get("search_phrase", ""))
    if not new:
        return None
    for old in _made_before() + channel_videos()["titles"]:
        o = _key(old)
        if o and len(new & o) >= max(2, int(0.6 * min(len(new), len(o)))):
            return old
    return None


def _low_demand() -> list[str]:
    return json.loads(LOW_DEMAND_FILE.read_text()) if LOW_DEMAND_FILE.exists() else []


def pick_topic() -> dict:
    """Pick a topic with proven big search demand. Topics whose top YouTube results have a
    median below MIN_SEARCH_VIEWS (default 50,000) are skipped and never suggested again."""
    need = int(os.getenv("MIN_SEARCH_VIEWS") or 50000)
    rejected: list[str] = []
    for attempt in range(6):
        r = _pick_once(rejected + _low_demand()[-60:])
        dup = already_made(r)
        if dup:
            log.info("Skipping '%s': the channel already has '%s'", r.get("topic"), dup)
            rejected.append(r.get("search_phrase") or r.get("topic", ""))
            continue
        demand = search_demand(r.get("search_phrase") or r.get("topic", ""))
        if demand is None:  # can't measure (no key / quota): don't block the channel
            log.warning("Search demand unknown - using the pick")
            return r
        log.info("Search demand for '%s': median %s views of the top 10 results (need %s)",
                 r.get("search_phrase"), f"{demand:,}", f"{need:,}")
        if demand >= need:
            r["search_demand"] = demand
            return r
        rejected.append(r.get("search_phrase") or r.get("topic", ""))
        LOW_DEMAND_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOW_DEMAND_FILE.write_text(json.dumps(_low_demand() + rejected[-1:], indent=1))
    raise RuntimeError(f"No new topic with enough search demand found this run (tried: {'; '.join(rejected)}) - "
                       "trying again next hour")


def _pick_once(avoid: list[str]) -> dict:
    cands = [c for c in candidates() if c[0] not in avoid]
    d = _domain()
    listing = "\n".join(f"- {p} (score {s:.0f})" for p, s in cands) or (
        "- (live data unavailable: use your knowledge of the most-searched YouTube topics in this field)")
    r = llm.chat_json(f"""Our channel covers {d["about"]}. Goal: grow fast and reach YouTube
monetization (watch hours). These are phrases people are typing into YouTube search right
now, with a popularity score:
{listing}

Already made (do not repeat, not even reworded): {"; ".join(_made_before()[-80:]) or "none"}
Too few searches - never pick these or anything similar: {"; ".join(avoid) or "none"}
Already on the channel: {"; ".join(t[:60] for t in channel_videos()["titles"][:120]) or "none"}

OUR MOST-VIEWED VIDEOS (a hint about who watches us and which title style works - NOT a
limit on topics):
{chr(10).join(f"- {t} ({n} views)" for n, t in channel_videos()["winners"]) or "- none yet"}
Choose mainly by SEARCH DEMAND: the topic millions of people are actively searching for
right now in our field (highest score above, plus your own knowledge of the biggest evergreen
YouTube searches in this field). Prefer searches with huge demand where a clear, complete,
well-animated answer can win - tutorials, "what is X", "how X works", courses, roadmaps,
installs, exam topics. Use our most-viewed videos only to break ties.

The video MUST be about {d["about"]} - nothing outside this field (no history, no general
science, no entertainment).

Pick the ONE best next video: the highest search demand, beginner-friendly but with
depth, evergreen enough to get views for months, and something a 8-10 minute animated
explainer can cover really well. {d["safety"]}

Return JSON: {{"topic": "<the video topic in plain words>", "search_phrase": "<the exact
search phrase it targets>", "angle": "<the hook/angle that makes people click and stay>"}}""",
                      SYSTEM, temperature=0.5, max_tokens=600, prefer=llm.WRITER_MODEL)
    log.info("Search-led topic: %s (targets '%s')", r.get("topic"), r.get("search_phrase"))
    return r


def write_script(pick: dict) -> dict:
    d = _domain()
    def draft() -> dict:
        return llm.chat_json(f"""Write the narration for a YouTube video.
    Topic: {pick["topic"]}
    People search: "{pick["search_phrase"]}"
    Angle: {pick.get("angle", "")}

    Spoken narration only, 1100-1300 words (about 9 minutes):
    1. Hook (first 15 seconds): answer why this matters right now, with a surprising fact or a
       question, and promise exactly what the viewer gets by the end.
    2. Deliver exactly what the searcher wants, step by step, in depth, with correct details,
       real examples and an everyday analogy for the hard part.
    3. Keep tension: every 60-90 seconds tease the next part ("but here's the part most people
       get wrong...").
    4. Common mistakes / myths, and pro tips.
    5. Short recap, then one line inviting viewers to subscribe for the next video.

    Rules: 100% accurate; if unsure, leave it out. Simple, confident English for viewers in
    India and the US. {d["safety"]} No brand promotion, no scene directions, no [brackets], no
    emojis.

    Return JSON: {{"title": "<working title>", "script": "<the full narration>"}}""",
                               SYSTEM, temperature=0.5, max_tokens=6000, prefer=llm.WRITER_MODEL)

    result = {}
    for _ in range(3):  # an empty or off-topic answer is thrown away and written again
        result = draft()
        if len(result.get("script", "").split()) >= 300 and on_topic(pick, result["script"]):
            break
        log.warning("Draft unusable (%d words, on topic: %s) - writing it again",
                    len(result.get("script", "").split()), on_topic(pick, result.get("script", "")))
    else:
        raise RuntimeError(f"Could not get a usable script about '{pick['topic']}'")
    for _ in range(2):  # too short: expand it instead of giving up
        words = len(result.get("script", "").split())
        if words >= 900:
            break
        log.info("Script has %d words - expanding", words)
        longer = llm.chat_json(f"""This narration is about: {pick["topic"]} (people search
"{pick["search_phrase"]}"). Stay on exactly this topic.
Expand it to 1100-1300 words: more depth, more
real examples, more step-by-step detail and teasers. Keep the hook, structure and accuracy.

{result.get("script", "")}

Return JSON: {{"title": "<working title>", "script": "<the full narration>"}}""",
                               SYSTEM, temperature=0.5, max_tokens=6000, prefer=llm.WRITER_MODEL)
        if len(longer.get("script", "").split()) > words and on_topic(pick, longer["script"]):
            result = longer
    if len(result.get("script", "").split()) < 500:
        raise RuntimeError("Script too short")
    if not on_topic(pick, result["script"]):
        raise RuntimeError(f"Script is not about '{pick['topic']}' - not making this video")
    try:
        r = llm.chat_json(f"""You are a strict expert reviewer of {d["about"]}. Check every
claim, command, number and step in this script; fix anything wrong or misleading. Keep the
length and spoken style. {d["safety"]}

SCRIPT:
{result["script"]}

Return JSON: {{"errors_found": ["..."], "script": "<the corrected script>"}}""",
                          SYSTEM, temperature=0.2, max_tokens=6000, prefer=llm.WRITER_MODEL)
        for e in r.get("errors_found", [])[:15]:
            log.info("Fact-check fix: %s", e)
        if len(r.get("script", "").split()) >= 600 and on_topic(pick, r["script"]):
            result["script"] = r["script"]
    except Exception as exc:
        log.warning("Fact-check failed, keeping the script: %s", exc)
    return result


def on_topic(pick: dict, script: str) -> bool:
    """True when the script is really about the picked topic: most of the topic's key words
    appear in it. Stops a wandering AI answer (e.g. a pyramid story) from becoming a video."""
    key = _key(pick.get("topic", "")) | _key(pick.get("search_phrase", ""))
    if not key or not script:
        return bool(script)
    text = _words(script)
    hits = {w for w in key if w in text or (len(w) > 4 and any(t.startswith(w[:5]) for t in text))}
    return len(hits) >= max(1, (len(key) + 1) // 2)


def _made_before() -> list[str]:
    """Everything this channel already covered (search topics + older topic lists)."""
    out = list(used())
    for f in ("state/used_topics.json",):
        try:
            out += json.loads(Path(f).read_text())
        except Exception:
            pass
    return out


def create_script() -> dict:
    pick = pick_topic()
    mark_used(pick["topic"])  # remembered at once, so a failed run never repeats it
    result = write_script(pick)
    result.update({"topic": pick["topic"], "search_topic": pick["topic"],
                   "search_phrase": pick.get("search_phrase", pick["topic"]),
                   "visual_style": VISUAL_STYLE, "sources": [], "research": {},
                   "date": dt.date.today().isoformat()})
    return result


PLAYLIST_FILE = Path("state/search_playlists.json")


def _playlists() -> list[str]:
    return json.loads(PLAYLIST_FILE.read_text()) if PLAYLIST_FILE.exists() else []


def make_metadata(script: dict) -> dict:
    meta = _package(script)
    name = (meta.get("playlist") or "").strip()[:60]
    if name:
        if name not in _playlists():
            PLAYLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
            PLAYLIST_FILE.write_text(json.dumps(_playlists() + [name], indent=1))
        meta["playlist"] = name
    else:
        meta.pop("playlist", None)
    return meta


def _package(script: dict) -> dict:
    return llm.chat_json(f"""You are the packaging lead of a professional YouTube channel
about {_domain()["about"]}. Package this video so it ranks in search and gets clicked.

Search phrase it targets: "{script["search_phrase"]}"
SCRIPT:
{script["script"][:6000]}

Write:
- title: 50-90 characters, the search phrase (or its natural form) at the start, then
  " | " and the subject/series, like this channel's most-viewed titles:
  {"; ".join(t for _, t in channel_videos()["winners"][:5]) or "What Is X? | How It Actually Works | Subject"}
  Honest, clear, may end with one fitting emoji. No clickbait that the video doesn't deliver.
- cover_text: 2-4 bold words for the thumbnail/title screen.
- short_hook: one gripping sentence (max 12 words) for the vertical Short.
- description: 1) two sentences that naturally contain the search phrase and close
  variations, 2) "In this video:" with 5 lines starting with "- ", 3) one line asking a
  question for viewers to answer in the comments. No links, no hashtags.
- hashtags: 3 relevant hashtags.
- tags: 15 search tags people really type, most important first.
- playlist: a short series name (2-4 words) this video belongs to, so related videos
  autoplay one after another, e.g. "Kali Linux", "Ethical Hacking", "Python", "AI Tools",
  "Arduino Projects", "How Phones Work". Reuse one of these if it fits: {", ".join(_playlists()) or "none yet"}.

Return JSON: {{"title": "...", "cover_text": "...", "short_hook": "...", "description": "...",
"hashtags": ["#..."], "tags": ["..."], "playlist": "..."}}""", temperature=0.5, max_tokens=2000,
                          prefer=llm.WRITER_MODEL)
