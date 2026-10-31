"""The channel's content: complete, never-ending course series for CS students (GetYr_CSE).

Each course is an ordered playlist from beginner to advanced (Python, Java, Git & GitHub,
DBMS, OS, Computer Networks, OOP, ML, Gen AI ...). Every episode is the next lesson of one
course; courses take turns, so several playlists grow at the same time. Lessons are
explained in depth, with intuition, real examples and code walkthroughs, so students
understand instead of memorising. A strict technical review checks every concept and code
example. Each video is added to its course playlist automatically.
Lesson plans are made by the AI in small parts (each video under 10 minutes) and extended
forever; a finished course is replaced by the next one in QUEUE.
Progress: state/course_progress.json and state/course_plan.json.
"""

import datetime as dt
import json
import logging
from pathlib import Path

from pipeline import llm

log = logging.getLogger(__name__)

PROGRESS_FILE = Path("state/course_progress.json")

COURSES = {
    "Python": [
        "What is programming and why Python", "Installing Python and writing your first program",
        "Variables and data types", "Numbers and math operators", "Strings and string methods",
        "Taking input and printing output", "Conditions: if, elif, else", "Loops: for and while",
        "break, continue and loop patterns", "Lists in depth", "Tuples and when to use them",
        "Sets and set operations", "Dictionaries in depth", "Functions: defining and calling",
        "Function arguments: default, keyword, *args, **kwargs", "Scope: local and global",
        "Recursion explained visually", "Lambda, map, filter and reduce", "List comprehensions",
        "Error handling with try, except, finally", "Reading and writing files",
        "Modules and packages", "pip and virtual environments", "Classes and objects",
        "Inheritance and polymorphism in Python", "Magic (dunder) methods", "Iterators and generators",
        "Decorators", "Context managers and with", "Working with JSON and APIs",
        "Date and time", "Regular expressions", "Type hints", "Testing with pytest",
        "Multithreading vs multiprocessing", "Async and await", "Memory management and garbage collection",
        "How Python runs your code (interpreter, bytecode)", "Writing clean, Pythonic code",
        "Python project: build a complete mini app",
    ],
    "Java": [
        "What is Java and how the JVM works", "Setting up Java and your first program",
        "Variables, data types and type casting", "Operators", "Taking input with Scanner",
        "if-else and switch", "Loops", "Arrays", "Strings and StringBuilder", "Methods",
        "Classes and objects", "Constructors and the this keyword", "static explained",
        "Encapsulation", "Inheritance", "Polymorphism: overloading and overriding",
        "Abstraction: abstract classes and interfaces", "Packages and access modifiers",
        "Exception handling", "Wrapper classes and autoboxing", "Collections framework overview",
        "ArrayList and LinkedList", "HashMap and HashSet", "Iterators and Comparable vs Comparator",
        "Generics", "File handling", "Multithreading basics", "Synchronization",
        "Lambda expressions and functional interfaces", "Streams API", "Java memory: stack, heap, GC",
        "Java project: build a complete mini app",
    ],
    "Git & GitHub": [
        "What is version control and why Git", "Installing and configuring Git",
        "Your first repository: init, add, commit", "How Git stores data (snapshots, SHA)",
        "git status, log and diff", "Undoing changes: restore, reset, revert", "Branches explained",
        "Merging and merge conflicts", "Rebasing vs merging", "What is GitHub",
        "Remotes: push, pull, fetch, clone", "Pull requests and code review", "Forks and open source",
        ".gitignore", "Stash and cherry-pick", "Tags and releases", "GitHub Actions basics",
        "Git workflows used in companies", "Fixing common Git mistakes",
    ],
    "DBMS": [
        "What is a database and a DBMS", "Why not just files: problems DBMS solves",
        "Data models and the relational model", "Keys: primary, candidate, foreign",
        "ER diagrams", "From ER diagram to tables", "Relational algebra", "SQL basics: SELECT",
        "Filtering, sorting and aggregate functions", "GROUP BY and HAVING", "Joins explained visually",
        "Subqueries", "INSERT, UPDATE, DELETE", "Constraints", "Functional dependencies",
        "Normalization: 1NF, 2NF, 3NF", "BCNF", "Transactions and ACID",
        "Concurrency control and locks", "Deadlocks in databases", "Recovery and logs",
        "Indexing and B+ trees", "Hashing in databases", "How a query is executed",
        "SQL vs NoSQL", "Views, stored procedures and triggers",
    ],
    "Operating Systems": [
        "What is an operating system", "Types of operating systems", "System calls",
        "Processes and process states", "Process control block and context switching",
        "Threads", "CPU scheduling: FCFS, SJF", "Round Robin and priority scheduling",
        "Process synchronization and race conditions", "Mutex and semaphores",
        "Classic problems: producer-consumer, dining philosophers", "Deadlocks",
        "Banker's algorithm", "Memory management basics", "Paging", "Segmentation",
        "Virtual memory", "Page replacement: FIFO, LRU, Optimal", "Thrashing",
        "File systems", "Disk scheduling", "Booting: what happens when you switch on a computer",
        "Linux basics for students",
    ],
    "Computer Networks": [
        "What is a computer network", "Types of networks: LAN, MAN, WAN", "Network topologies",
        "OSI model explained", "TCP/IP model", "Physical layer and transmission media",
        "Data link layer: framing and error detection", "MAC addresses and switches",
        "IP addresses", "Subnetting made easy", "Routing and routers", "ARP",
        "TCP vs UDP", "TCP three-way handshake", "Flow and congestion control", "Ports and sockets",
        "DNS: how a website name becomes an address", "HTTP and HTTPS", "What happens when you type a URL",
        "DHCP", "NAT", "Firewalls and VPNs", "Wi-Fi explained", "Network security basics",
    ],
    "OOP": [
        "What is object-oriented programming", "Classes and objects", "Encapsulation",
        "Abstraction", "Inheritance and its types", "Polymorphism", "Constructors and destructors",
        "Interfaces vs abstract classes", "Composition vs inheritance", "SOLID principles",
        "Design patterns: Singleton and Factory", "Design patterns: Observer and Strategy",
        "OOP interview questions explained",
    ],
    "Machine Learning": [
        "What is machine learning", "Types of ML: supervised, unsupervised, reinforcement",
        "The ML workflow", "Data preprocessing", "Train, validation and test sets",
        "Linear regression", "Gradient descent explained", "Logistic regression",
        "Overfitting and underfitting", "Bias and variance", "Regularization",
        "Decision trees", "Random forests", "K-nearest neighbours", "Support vector machines",
        "Naive Bayes", "K-means clustering", "PCA and dimensionality reduction",
        "Evaluation metrics: accuracy, precision, recall, F1", "Cross-validation",
        "Neural networks basics", "How a neural network learns: backpropagation",
        "CNNs for images", "RNNs and sequences", "Building your first ML project",
    ],
    "Generative AI": [
        "What is generative AI", "How AI generates text: next-token prediction",
        "Tokens and embeddings", "The Transformer architecture", "Attention explained simply",
        "How large language models are trained", "Fine-tuning vs prompting", "Prompt engineering",
        "RAG: retrieval augmented generation", "Vector databases", "AI agents and tool use",
        "How image generation works: diffusion models", "Evaluating and testing LLM apps",
        "Hallucinations and how to reduce them", "Building a chatbot app step by step",
        "Responsible and safe AI",
    ],
    "Data Structures & Algorithms": [
        "What are data structures and algorithms", "Time and space complexity (Big O)",
        "Arrays", "Strings problems", "Linked lists", "Stacks", "Queues", "Hashing",
        "Recursion and backtracking", "Binary search", "Sorting: bubble, selection, insertion",
        "Merge sort and quick sort", "Trees and binary trees", "Binary search trees", "Heaps",
        "Graphs and representations", "BFS and DFS", "Shortest paths: Dijkstra", "Greedy algorithms",
        "Dynamic programming", "Tries", "Two pointers and sliding window",
    ],
}

SYSTEM = (
    "You are an outstanding computer science teacher and the head writer of an educational "
    "YouTube channel for students in India and the US. You explain concepts in depth, from "
    "intuition to real details, with analogies, step-by-step examples and correct code, so "
    "students understand instead of memorising."
)

VISUAL_STYLE = (
    "Animate the whole video as a clean, modern computer-science explainer: smooth motion "
    "graphics, animated diagrams that build step by step (memory boxes, arrows, tables, "
    "trees, network packets, flowcharts), short code snippets shown in a clean code editor "
    "with the current line highlighted and the output appearing, and simple real-life "
    "analogies drawn as friendly animations. Clear colours on a clean dark or light "
    "background. Keep every diagram and code example technically correct and in sync with "
    "the narration. Every scene moves - no still slides. On-screen text only for the title, "
    "short labels and code."
)


QUEUE = [
    "C Programming", "C++", "JavaScript", "SQL", "Linux and Shell", "Web Development (HTML, CSS)",
    "React", "Node.js", "Docker", "Kubernetes", "Cloud Computing (AWS basics)", "System Design",
    "Cybersecurity", "Data Science with Python", "Deep Learning", "Computer Architecture",
    "Compiler Design", "Theory of Computation", "Software Engineering", "DevOps and CI/CD",
    "Android Development", "Blockchain", "Big Data", "Discrete Mathematics", "Rust", "Go",
]
ACTIVE_COURSES = 10       # courses that take turns at the same time
COURSE_LESSONS_MAX = 120  # a course is "complete" after this many lessons (a queued one starts)
PLAN_FILE = Path("state/course_plan.json")


def progress() -> dict:
    return json.loads(PROGRESS_FILE.read_text()) if PROGRESS_FILE.exists() else {}


def save_progress(p: dict) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(p, indent=1, ensure_ascii=False))


def load_plan() -> dict:
    if PLAN_FILE.exists():
        return json.loads(PLAN_FILE.read_text())
    return {"active": list(COURSES)[:ACTIVE_COURSES], "queue": list(COURSES)[ACTIVE_COURSES:] + QUEUE,
            "done": [], "lessons": {}}


def save_plan(plan: dict) -> None:
    PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLAN_FILE.write_text(json.dumps(plan, indent=1, ensure_ascii=False))


def plan_lessons(course: str, taught: list[str]) -> list[str]:
    """Ask the AI for the next lessons of a course: small, focused parts (each fits in a
    video under 10 minutes), in teaching order, never repeating what was taught."""
    seed = COURSES.get(course, [])
    r = llm.chat_json(f"""You are designing the "{course}" course for a YouTube channel, from
absolute beginner to advanced/master level, like the best structured tutorials (W3Schools,
GeeksforGeeks, university courses), but each lesson explained in depth.

{"Already taught: " + json.dumps(taught[-80:], ensure_ascii=False) if taught else "Nothing taught yet."}
{"Suggested topic outline: " + json.dumps(seed, ensure_ascii=False) if seed and not taught else ""}

Plan the NEXT 25 lessons in the right teaching order. Split big topics into several focused
parts ("... Part 1", "... Part 2") so each lesson is one clear idea that fits in a video under
10 minutes. {"Continue deeper: advanced topics, internals, real-world projects, best practices, interview questions." if taught else ""}
If the course is fully covered, return an empty list.

Return JSON: {{"lessons": ["<lesson title>", ...]}}""", SYSTEM, temperature=0.4, max_tokens=3000,
                      prefer=llm.WRITER_MODEL)
    return [x for x in r.get("lessons", []) if isinstance(x, str) and x not in taught][:30]


def next_lesson() -> tuple[str, int]:
    """Round-robin over the active courses. Lesson lists are planned by the AI and extended
    forever; a finished course is replaced by the next one in the queue."""
    plan, p = load_plan(), progress()
    order = plan["active"]
    last = p.get("_last_course")
    start = (order.index(last) + 1) % len(order) if last in order else 0
    for i in range(len(order)):
        course = order[(start + i) % len(order)]
        lessons = plan["lessons"].setdefault(course, [])
        n = p.get(course, 0)
        if n >= len(lessons) and n < COURSE_LESSONS_MAX:
            try:
                more = plan_lessons(course, lessons[:n])
            except Exception as exc:  # planning failed: use the built-in outline if any
                log.warning("Lesson planning failed for %s: %s", course, exc)
                more = [x for x in COURSES.get(course, []) if x not in lessons]
            lessons.extend(more)
            save_plan(plan)
        if n < len(lessons) and n < COURSE_LESSONS_MAX:
            return course, n
        # course complete -> start the next queued course in its place
        plan["active"].remove(course)
        plan["done"].append(course)
        if plan["queue"]:
            plan["active"].append(plan["queue"].pop(0))
            log.info("Course complete: %s - starting %s", course, plan["active"][-1])
        save_plan(plan)
        return next_lesson()
    raise RuntimeError("No active courses left - add courses to QUEUE in pipeline/courses.py")


def lesson_list(course: str) -> list[str]:
    return load_plan()["lessons"].get(course) or COURSES.get(course, [])


def mark_done(course: str, index: int) -> None:
    p = progress()
    p[course] = max(p.get(course, 0), index + 1)
    p["_last_course"] = course
    save_progress(p)


def write_script(course: str, index: int) -> dict:
    lessons = lesson_list(course)
    lesson = lessons[index]
    before = "; ".join(lessons[max(0, index - 3):index]) or "none - this is the first lesson"
    after = lessons[index + 1] if index + 1 < len(lessons) else "the end of the course"
    result = llm.chat_json(f"""Write the narration for lesson {index + 1} of the
"{course}" course: {lesson}.

Previous lessons: {before}. Next lesson: {after}.

Structure (spoken narration only, 1000-1250 words - the video must stay under 10 minutes):
1. Hook: why this matters / a real problem it solves (2-3 sentences).
2. The intuition first: explain the idea with a simple real-life analogy.
3. The concept in depth, step by step, using correct terminology (define each new word).
4. Worked examples: walk through 2-3 concrete examples, including how it is used in the
   real world (real apps, systems, companies' kind of use). For code, describe short, correct
   snippets line by line (say what each line does and what the output is).
5. Under the hood: how it actually works internally (memory, execution, protocol, maths...).
6. Common mistakes and misconceptions students have, and how to avoid them.
7. Where it is used in real projects / interviews.
8. A 3-point recap and a one-line teaser for the next lesson.

Rules: 100% technically correct; if unsure, leave it out. Simple English for students in
India and the US. Build on the previous lessons; don't use concepts not yet taught without
explaining them. No brand promotion, no scene directions, no [brackets], no emojis. Write
code inside the narration as spoken explanation (e.g. "we write: print, open bracket...")
only when short; otherwise describe it clearly.

Return JSON: {{"title": "<working title>", "script": "<the full narration>"}}""",
                           SYSTEM, temperature=0.4, max_tokens=6000, prefer=llm.WRITER_MODEL)
    words = len(result.get("script", "").split())
    if words > 1350:  # keep the video under 10 minutes: tighten, don't cut off the ending
        try:
            short = llm.chat_json(f"""Tighten this lesson narration to 1100-1250 words without
losing any key concept, example or the recap. Same style.

{result["script"]}

Return JSON: {{"title": "<working title>", "script": "<the tightened narration>"}}""",
                                  SYSTEM, temperature=0.3, max_tokens=6000, prefer=llm.WRITER_MODEL)
            if 700 <= len(short.get("script", "").split()) <= 1400:
                result, words = short, len(short["script"].split())
        except Exception as exc:
            log.warning("Could not tighten the script: %s", exc)
    if words < 750:
        longer = llm.chat_json(f"""This lesson narration is too short ({words} words). Expand it to
1000-1250 words (under 10 minutes): deeper explanation, more worked examples, more under-the-hood detail. Same
structure, accuracy and style.

{result.get("script", "")}

Return JSON: {{"title": "<working title>", "script": "<the full narration>"}}""",
                               SYSTEM, temperature=0.4, max_tokens=6000,
                               prefer=llm.WRITER_MODEL)
        if len(longer.get("script", "").split()) > words:
            result, words = longer, len(longer["script"].split())
    if words < 500:
        raise RuntimeError(f"Script too short ({words} words)")
    return review(course, lesson, result)


def review(course: str, lesson: str, result: dict) -> dict:
    """Strict technical review of every concept, term and code example."""
    try:
        r = llm.chat_json(f"""You are a strict computer science professor reviewing a lesson
script ("{course}": {lesson}) for students. Check every definition, explanation, example and
code statement for correctness (syntax, output, complexity, behaviour). Fix every error or
misleading simplification; improve clarity where students would get confused. Keep the
structure, length and spoken style.

SCRIPT:
{result["script"]}

Return JSON: {{"errors_found": ["<each problem and fix>"], "script": "<the corrected script>"}}""",
                          SYSTEM, temperature=0.2, max_tokens=6000, prefer=llm.WRITER_MODEL)
    except Exception as exc:
        log.warning("Review failed, keeping the script: %s", exc)
        return result
    for e in r.get("errors_found", [])[:15]:
        log.info("Review fix: %s", e)
    if len(r.get("script", "").split()) >= 500:
        result["script"] = r["script"]
    return result


def create_script() -> dict:
    course, index = next_lesson()
    lesson = lesson_list(course)[index]
    log.info("Next lesson: %s #%d - %s", course, index + 1, lesson)
    result = write_script(course, index)
    result.update({"topic": f"{course}: {lesson}", "course": course, "lesson": lesson,
                   "lesson_index": index, "lesson_count": len(lesson_list(course)),
                   "series": f"{course} course", "visual_style": VISUAL_STYLE,
                   "sources": [], "research": {}, "date": dt.date.today().isoformat()})
    return result


def make_metadata(script: dict) -> dict:
    course, lesson, n = script["course"], script["lesson"], script["lesson_index"] + 1
    meta = llm.chat_json(f"""You are a YouTube SEO expert for an educational computer science
channel. Package lesson {n} of the "{course}" course: {lesson}.

SCRIPT:
{script["script"]}

Write:
- title: 45-70 characters in this form: "<clear lesson title> | {course} Course #{n}", the
  way students search, e.g. "Python Lists Explained in Depth | Python Course #10".
- cover_text: 2-4 words for the title screen and thumbnail, e.g. "PYTHON LISTS".
- short_hook: one sentence (max 12 words) for the vertical Short.
- description: 1) two sentences with the main keywords, 2) "In this lesson:" with 5 short
  lines starting with "- ", 3) "This is lesson {n} of our complete {course} course - watch
  the full playlist from the beginning." and an invitation to ask doubts in the comments.
  No links, no hashtags.
- hashtags: 3, e.g. "#{course.replace(' ', '').replace('&', '')}", "#programming", "#computerscience"
- tags: 15 search tags, most important first.

Return JSON: {{"title": "...", "cover_text": "...", "short_hook": "...", "description": "...",
"hashtags": ["#..."], "tags": ["..."]}}""", temperature=0.4, max_tokens=2000,
                         prefer=llm.WRITER_MODEL)
    meta["playlist"] = f"{course} Course - Beginner to Advanced"
    return meta
