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
                  "comptia security+", "ceh", "ransomware", "dark web", "sql injection"],
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
                  "placement preparation", "projects for resume", "vs code"],
        "safety": "",
    },
    "ece": {
        "about": "electronics, electrical engineering and how technology works",
        "seeds": ["how does", "how it works", "electronics", "arduino", "arduino projects",
                  "esp32", "raspberry pi", "how phone charger works", "how 5g works",
                  "how solar panel works", "electric car battery", "semiconductor",
                  "how chips are made", "pcb design", "transistor", "inverter",
                  "electronics projects", "ece projects", "vlsi", "embedded systems",
                  "how wifi works", "how batteries work", "motor"],
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


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9+#]+", s.lower()) if len(w) > 2}


def candidates() -> list[tuple[str, float]]:
    """Live search phrases with a popularity score (higher = searched more)."""
    scores: dict[str, float] = {}
    for seed in _domain()["seeds"]:
        for rank, phrase in enumerate(search_suggestions(seed, limit=10)):
            scores[phrase] = scores.get(phrase, 0) + (10 - rank)
    done = [_words(u) for u in _made_before()]
    out = []
    for phrase, score in scores.items():
        w = _words(phrase)
        if len(w) < 2 or any(len(w & d) >= max(2, len(w) - 1) for d in done):
            continue  # too vague, or already made
        out.append((phrase, score))
    return sorted(out, key=lambda x: -x[1])[:60]


def pick_topic() -> dict:
    cands = candidates()
    d = _domain()
    listing = "\n".join(f"- {p} (score {s:.0f})" for p, s in cands) or (
        "- (live data unavailable: use your knowledge of the most-searched YouTube topics in this field)")
    r = llm.chat_json(f"""Our channel covers {d["about"]}. Goal: grow fast and reach YouTube
monetization (watch hours). These are phrases people are typing into YouTube search right
now, with a popularity score:
{listing}

Already made (do not repeat, not even reworded): {"; ".join(_made_before()[-80:]) or "none"}

Pick the ONE best next video: high search demand, broad audience, beginner-friendly but with
depth, evergreen enough to get views for months, and something a 8-10 minute animated
explainer can cover really well. {d["safety"]}

Return JSON: {{"topic": "<the video topic in plain words>", "search_phrase": "<the exact
search phrase it targets>", "angle": "<the hook/angle that makes people click and stay>"}}""",
                      SYSTEM, temperature=0.5, max_tokens=600, prefer=llm.WRITER_MODEL)
    log.info("Search-led topic: %s (targets '%s')", r.get("topic"), r.get("search_phrase"))
    return r


def write_script(pick: dict) -> dict:
    d = _domain()
    result = llm.chat_json(f"""Write the narration for a YouTube video.
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
    for _ in range(2):  # too short: expand it instead of giving up
        words = len(result.get("script", "").split())
        if words >= 900:
            break
        log.info("Script has %d words - expanding", words)
        longer = llm.chat_json(f"""Expand this narration to 1100-1300 words: more depth, more
real examples, more step-by-step detail and teasers. Keep the hook, structure and accuracy.

{result.get("script", "")}

Return JSON: {{"title": "<working title>", "script": "<the full narration>"}}""",
                               SYSTEM, temperature=0.5, max_tokens=6000, prefer=llm.WRITER_MODEL)
        if len(longer.get("script", "").split()) > words:
            result = longer
    if len(result.get("script", "").split()) < 500:
        raise RuntimeError("Script too short")
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
        if len(r.get("script", "").split()) >= 600:
            result["script"] = r["script"]
    except Exception as exc:
        log.warning("Fact-check failed, keeping the script: %s", exc)
    return result


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
- title: 45-65 characters, contains the search phrase (or its natural form) near the start,
  plus an honest curiosity hook. Professional tone like Fireship, Veritasium, NetworkChuck.
  No filler such as "Explained Simply", "for Students", "for Beginners", no emojis.
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
