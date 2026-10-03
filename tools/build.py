#!/usr/bin/env python3
"""Build the Engineering Handbooks from their chapter sources, and check them.

    python3 tools/build.py            assemble the three books (HTML)
    python3 tools/build.py check      verify code excerpts, links, anchors, figures, wording
    python3 tools/build.py figures    export every figure as a standalone SVG

Chapters live in src/<book>/<slug>.html as <section class="chapter"> fragments.
Code excerpts carry data-repo, data-path and data-lines, and `check` compares
them with the pinned commit of the reference repository.
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

# The reference implementation, pinned to a tag. Links name the tag; excerpts are checked against
# the commit it points to. A local checkout of it: TA_REPO, or a folder named triage-assistant next
# to this repository (fetch its tags). TA_REF overrides the tag, to preview a newer commit.
TA_REPO = os.environ.get("TA_REPO", str(ROOT.parent / "triage-assistant"))
TA_REF = os.environ.get("TA_REF", "handbook-1")


def ta_commit() -> str:
    out = subprocess.run(["git", "-C", TA_REPO, "rev-parse", f"{TA_REF}^{{commit}}"],
                         capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


TA_URL = "https://github.com/Parzon/triage-assistant"
EH_URL = "https://github.com/Parzon/engineering-handbooks"
LABS_DIR = ROOT / "labs"

PLACEHOLDERS = {
    "{{TA}}": f"{TA_URL}/blob/{TA_REF}",
    "{{TATREE}}": f"{TA_URL}/tree/{TA_REF}",
    "{{TAREPO}}": TA_URL,
    "{{EH}}": f"{EH_URL}/blob/main",
    "{{EHTREE}}": f"{EH_URL}/tree/main",
    "{{REF}}": f"{TA_REF} ({ta_commit()[:7]})",
}

SERIES = [
    ("ai", "ai-engineering.html", "AI Engineering &amp; Architecture",
     "The new layer: models, retrieval, agents, evaluation, safety."),
    ("sw", "software-engineering.html", "Modern Software Engineering",
     "Your skills, brought up to date: the service and its repository."),
    ("ops", "cloud-delivery.html", "Cloud Delivery &amp; DevOps",
     "From a laptop to production: pipelines, identity, the cloud."),
]

BOOKS = {
    "ai": {
        "n": 1,
        "file": "ai-engineering.html",
        "title": "AI Engineering &amp; Architecture",
        "plain": "AI Engineering & Architecture",
        "subtitle": "The new layer in software: how models run, how to build with them, and how to prove they work.",
        "for": "For engineers and architects who know how software is built and are coming back to it as AI becomes part of every system. It explains what is genuinely new, what is your existing skill applied to a new component, and where each idea runs in a real, public codebase.",
        "description": "Handbook 1 of the Engineering Handbooks: how models run, retrieval, agents, evaluation, security and operations for AI systems, shown on a real public codebase.",
        "parts": [
            ("Part I · The new layer", [("ch01", "What changed, and what did not")]),
            ("Part II · How models run", [("ch02", "How a model produces text"), ("ch03", "Serving models")]),
            ("Part III · Building with models", [("ch04", "Retrieval-augmented generation"), ("ch05", "Knowledge graphs and GraphRAG"), ("ch06", "Agents, tools and MCP")]),
            ("Part IV · Proving it works", [("ch07", "Evaluation"), ("ch08", "AI observability")]),
            ("Part V · Making it safe", [("ch09", "AI security")]),
            ("Part VI · Running it", [("ch10", "Cost and performance"), ("ch11", "Distributed AI systems"), ("ch12", "Production AI operations")]),
            ("Part VII · The data platform", [("ch13", "Warehouses, lakehouses and streams"), ("ch14", "Data engineering for AI")]),
            ("Part VIII · Architecture and leadership", [("ch15", "Making and recording decisions"), ("ch16", "Stack defaults and the complexity dial"), ("ch17", "Leading AI delivery"), ("ch18", "Working with AI coding agents")]),
        ],
    },
    "sw": {
        "n": 2,
        "file": "software-engineering.html",
        "title": "Modern Software Engineering",
        "plain": "Modern Software Engineering",
        "subtitle": "Your skills, brought up to date: how a production service and its repository are built today.",
        "for": "For engineers who have built and run services before and are returning to the work. It assumes you know what a database, a web server and a test are, and shows how each is done now, why it changed, and where to see it working in a real, public codebase.",
        "description": "Handbook 2 of the Engineering Handbooks: the modern service and its repository, from the network and the database to containers, testing, observability and reliability.",
        "parts": [
            ("Part I · The service and its repository", [("ch01", "The anatomy of a modern service repository"), ("ch02", "The system end to end")]),
            ("Part II · Foundations, refreshed", [("ch03", "Linux and processes"), ("ch04", "Networks: DNS, TCP, TLS and HTTP"), ("ch05", "Concurrency and the Python backend")]),
            ("Part III · Data", [("ch06", "Postgres: schema changes and indexes"), ("ch07", "Connections, pooling and row-level security")]),
            ("Part IV · Identity and protection", [("ch08", "Sign-in, sessions and roles"), ("ch09", "Secrets, personal data and least privilege")]),
            ("Part V · The web tier", [("ch10", "Frontend decisions and streaming"), ("ch11", "The edge: TLS, nginx and proxies")]),
            ("Part VI · Containers", [("ch12", "Containers and Compose")]),
            ("Part VII · Quality", [("ch13", "Testing, code style and review")]),
            ("Part VIII · Running it", [("ch14", "Observability and debugging"), ("ch15", "Reliability: timeouts, failures and drills"), ("ch16", "Performance and load testing"), ("ch17", "Incidents, runbooks and service levels")]),
            ("Part IX · Choosing and starting", [("ch18", "The stack catalog"), ("ch19", "Starting a new service")]),
        ],
    },
    "ops": {
        "n": 3,
        "file": "cloud-delivery.html",
        "title": "Cloud Delivery &amp; DevOps",
        "plain": "Cloud Delivery & DevOps",
        "subtitle": "From a laptop to production, the way teams ship today.",
        "for": "For engineers who have shipped software before and are coming back to it. It assumes you know what a server, a build and a deployment are. It shows how each is done now, why it changed, and where to see it working in a real, public codebase.",
        "description": "Handbook 3 of the Engineering Handbooks: Git, CI/CD, keyless identity, infrastructure as code, AWS containers and operations, shown on a real deployment.",
        "parts": [
            ("Part I · What changed", [("ch01", "From laptop to production")]),
            ("Part II · Source and build", [("ch02", "Git and the pull request"), ("ch03", "CI/CD and artifacts"), ("ch04", "The software supply chain")]),
            ("Part III · Identity", [("ch05", "Identity without keys")]),
            ("Part IV · Getting code onto servers", [("ch06", "The deployment ladder, and one VM done properly"), ("ch07", "Infrastructure as code")]),
            ("Part V · Running on AWS", [("ch08", "Networking on AWS"), ("ch09", "Containers on ECS Fargate"), ("ch10", "Kubernetes and EKS"), ("ch11", "The same ideas on Azure and Google Cloud")]),
            ("Part VI · The reference build", [("ch12", "Case studies from a real deployment")]),
            ("Part VII · Operating it", [("ch13", "Environments, releases and rollback"), ("ch14", "Cost, teardown and lessons learned")]),
        ],
    },
}

APPENDICES = [("app-a", "A", "Glossary"), ("app-b", "B", "Decision index"),
              ("app-c", "C", "Repository index"), ("app-d", "D", "Trap index")]

FONTS = ("https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900"
         "&amp;family=JetBrains+Mono:wght@400..700"
         "&amp;family=Source+Serif+4:ital,opsz,wght@0,8..60,300..700;1,8..60,300..700&amp;display=swap")

MARKERS = """<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
  <defs>
    <marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path class="m" d="M0,1 L10,5 L0,9 z"/></marker>
    <marker id="a-acc" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto-start-reverse"><path class="m-acc" d="M0,1 L10,5 L0,9 z"/></marker>
    <marker id="a-good" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path class="m-good" d="M0,1 L10,5 L0,9 z"/></marker>
    <marker id="a-bad" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path class="m-bad" d="M0,1 L10,5 L0,9 z"/></marker>
  </defs>
</svg>"""

SHAPE = """<div class="shape">
    <div><b>In one sentence</b>What the topic is, in words you can use in a meeting.</div>
    <div><b>At a glance</b>The points to keep if you read nothing else.</div>
    <div><b>Then and now</b>How it was usually done, how it is done today, and why it changed.</div>
    <div><b>Figures</b>The mechanism, drawn. The text explains the figure.</div>
    <div><b>In the repo</b>Where the idea lives in the reference code, with the lines quoted beside the explanation.</div>
    <div><b>How to say it</b>A few sentences for a design review.</div>
    <div><b>Traps</b>What goes wrong in practice, and the fix.</div>
    <div><b>Going deeper</b>Detail for when you need it. Collapsed on the web, printed in full.</div>
    <div><b>Questions</b>To check your understanding. Answers follow.</div>
  </div>"""


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def strip_tags(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment))


def chapter_meta(fragment: str) -> dict:
    sec = re.search(r'<section class="chapter[^"]*" id="([^"]+)"', fragment)
    num = re.search(r'<span class="ch-num">([^<]+)</span>', fragment)
    title = re.search(r"<h2>(.*?)</h2>", fragment, re.S)
    subs = re.findall(r'<h3 id="([^"]+)"[^>]*>(.*?)</h3>', fragment, re.S)
    return {
        "id": sec.group(1) if sec else "",
        "num": num.group(1).strip() if num else "",
        "title": title.group(1).strip() if title else "",
        "subs": [(i, strip_tags(t).strip()) for i, t in subs],
    }


def short_sub(text: str) -> str:
    # The rail has little room: keep a section title to its first clause.
    text = re.split(r"[:,]| and when", text)[0].strip()
    return text if len(text) <= 38 else text[:36].rsplit(" ", 1)[0] + "…"


def load(book: str, slug: str) -> str | None:
    path = SRC / book / f"{slug}.html"
    return path.read_text() if path.exists() else None


def expand(text: str) -> str:
    for key, value in PLACEHOLDERS.items():
        text = text.replace(key, value)
    return text


# ---------- Generated appendices ----------

def trap_index(chapters: list[tuple[dict, str]]) -> str:
    rows = []
    for meta, frag in chapters:
        for table in re.findall(r'<table class="grid traps[^"]*">(.*?)</table>', frag, re.S):
            for tr in re.findall(r"<tr>(.*?)</tr>", table, re.S):
                cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
                if len(cells) >= 3:
                    rows.append((meta, cells[0], cells[2]))
    if not rows:
        return ""
    body = "\n".join(
        f'<tr><td data-label="Symptom">{sym}</td><td data-label="Fix">{fix}</td>'
        f'<td data-label="Chapter"><a href="#{m["id"]}">{m["num"]} · {m["title"]}</a></td></tr>'
        for m, sym, fix in rows
    )
    return f"""<div class="table-wrap"><table class="grid traps stack">
<thead><tr><th>Symptom</th><th>Fix</th><th>Chapter</th></tr></thead>
<tbody>
{body}
</tbody></table></div>"""


def repo_index(chapters: list[tuple[dict, str]]) -> str:
    files: dict[str, list[dict]] = {}
    for meta, frag in chapters:
        for path in re.findall(r'data-path="([^"]+)"', frag):
            files.setdefault(path, [])
            if meta not in files[path]:
                files[path].append(meta)
    if not files:
        return ""
    rows = []
    for path in sorted(files, key=lambda p: (p.count("/") > 0, p)):
        link = f"{{{{TA}}}}/{path}" if not path.startswith("labs/") else f"{{{{EH}}}}/{path}"
        where = ", ".join(f'<a href="#{m["id"]}">{m["num"]}</a>' for m in files[path])
        rows.append(f'<tr><td data-label="File"><a href="{link}"><code>{esc(path)}</code></a></td><td data-label="Chapters">{where}</td></tr>')
    return ('<div class="table-wrap"><table class="grid stack"><thead><tr><th>File</th><th>Quoted in chapter</th></tr></thead><tbody>\n'
            + "\n".join(rows) + "\n</tbody></table></div>")


def repo_adr_titles() -> dict[str, str]:
    """ADR titles from the reference repository at the pinned commit."""
    try:
        out = subprocess.run(["git", "-C", TA_REPO, "ls-tree", "--name-only", TA_REF, "docs/adr/"],
                             capture_output=True, check=True, text=True).stdout.split()
    except subprocess.CalledProcessError:
        return {}
    titles = {}
    for path in out:
        lines = git_file(path) or [""]
        m = re.match(r"#\s*(ADR-\d+):\s*(.+)", lines[0])
        if m:
            titles[m.group(1)] = esc(m.group(2).replace(" \u2014 ", ": ").replace("\u2014", ": ").strip())
    return titles


def decision_index(chapters: list[tuple[dict, str]]) -> str:
    seen: dict[str, tuple[str, list[dict]]] = {}
    for meta, frag in chapters:
        for adr_id, title in re.findall(r'<span class="adr-id">([^<]+)</span>.*?<p class="adr-title">(.*?)</p>', frag, re.S):
            entry = seen.setdefault(adr_id.strip(), (title.strip(), []))
            if not entry[0]:
                entry = seen[adr_id.strip()] = (title.strip(), entry[1])
            if meta not in entry[1]:
                entry[1].append(meta)
        for adr_id in re.findall(r'data-adr="([^"]+)"', frag):
            entry = seen.setdefault(adr_id, ("", []))
            if meta not in entry[1]:
                entry[1].append(meta)
    if not seen:
        return ""
    rows = []
    repo_titles = repo_adr_titles()
    for adr_id in sorted(seen):
        title, metas = seen[adr_id]
        title = title or repo_titles.get(adr_id, "")
        where = ", ".join(f'<a href="#{m["id"]}">{m["num"]}</a>' for m in metas)
        rows.append(f'<tr><td data-label="Record"><code>{adr_id}</code></td><td data-label="Decision">{title}</td><td data-label="Chapters">{where}</td></tr>')
    return ('<div class="table-wrap"><table class="grid stack decisions"><thead><tr><th>Record</th><th>Decision</th><th>Discussed in</th></tr></thead><tbody>\n'
            + "\n".join(rows) + "\n</tbody></table></div>")


def appendix(book: str, key: str, letter: str, title: str, chapters) -> str:
    intro = load(book, key) or ""
    generated = ""
    if key == "app-b":
        generated = decision_index(chapters)
    elif key == "app-c":
        generated = repo_index(chapters)
    elif key == "app-d":
        generated = trap_index(chapters)
    if not intro and not generated:
        return ""
    if intro.lstrip().startswith("<section"):
        return intro.replace("<!--GENERATED-->", generated)
    return f"""<section class="chapter appendix" id="{key}">
  <header class="ch-head">
    <span class="ch-num">{letter}</span>
    <p class="eyebrow">Appendix</p>
    <h2>{title}</h2>
  </header>
  {intro}
  {generated}
</section>"""


# ---------- Assembly ----------

def build_book(book: str) -> Path:
    cfg = BOOKS[book]
    chapters: list[tuple[dict, str]] = []
    contents_parts = []
    rail = []
    mobile = []
    for part, items in cfg["parts"]:
        lis = []
        rail_items = []
        for slug, title in items:
            frag = load(book, slug)
            num = str(int(slug[2:]))
            if frag:
                meta = chapter_meta(frag)
                chapters.append((meta, frag))
                lis.append(f'<li><span class="num">{num}</span><a href="#{meta["id"]}">{meta["title"]}</a></li>')
                subs = "".join(f'<li class="toc-sub"><a href="#{sid}">{esc(short_sub(st))}</a></li>' for sid, st in meta["subs"])
                rail_items.append(f'<li><a href="#{meta["id"]}">{num} · {meta["title"]}</a></li>{subs}')
                mobile.append(f'<li><a href="#{meta["id"]}">{num} · {meta["title"]}</a></li>')
            else:
                lis.append(f'<li><span class="num">{num}</span><span>{title}</span></li>')
        contents_parts.append(f'<div><h3>{part}</h3><ol>{"".join(lis)}</ol></div>')
        if rail_items:
            rail.append(f'<li class="toc-part"><span class="label">{part}</span><ol>{"".join(rail_items)}</ol></li>')

    apps_html = []
    app_lis = []
    for key, letter, title in APPENDICES:
        block = appendix(book, key, letter, title, chapters)
        if block:
            apps_html.append(block)
            app_lis.append(f'<li><span class="num">{letter}</span><a href="#{key}">{title}</a></li>')
            mobile.append(f'<li><a href="#{key}">{letter} · {title}</a></li>')
        else:
            app_lis.append(f'<li><span class="num">{letter}</span><span>{title}</span></li>')
    contents_parts.append(f'<div><h3>Appendices</h3><ol>{"".join(app_lis)}</ol></div>')
    if apps_html:
        rail.append('<li class="toc-part"><span class="label">Appendices</span><ol>'
                    + "".join(f'<li><a href="#{k}">{l} · {t}</a></li>' for k, l, t in APPENDICES if f'id="{k}"' in "".join(apps_html))
                    + "</ol></li>")

    series = []
    for key, file, title, blurb in SERIES:
        n = BOOKS[key]["n"]
        if key == book:
            series.append(f'<div class="here"><span class="n">{n} · {title}</span><span>{blurb}</span></div>')
        else:
            series.append(f'<a href="{file}"><span class="n">{n} · {title}</span><span>{blurb}</span></a>')

    reading = load(book, "reading") or ""
    body_chapters = "\n\n".join(frag for _, frag in chapters)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%231f2937'/%3E%3Cpath d='M9 8h11a3 3 0 0 1 3 3v13H12a3 3 0 0 1-3-3z' fill='none' stroke='%23fff' stroke-width='2'/%3E%3Cpath d='M13 13h6M13 17h6' stroke='%23fff' stroke-width='2'/%3E%3C/svg%3E">
<title>{cfg["title"]}</title>
<meta name="description" content="{cfg["description"]}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="assets/handbook.css">
<style>@page {{ @bottom-left {{ content: "Handbook {cfg["n"]} \\00b7  {cfg["plain"]}"; font-family: "Archivo", Arial, sans-serif; font-size: 8.5pt; color: #6a727b; }} }}</style>
</head>
<body data-book="{book}">
{MARKERS}

<div class="page">
<nav class="toc" aria-label="Contents">
  <a class="toc-book" href="#top">{cfg["title"]}</a>
  <ol>
    <li><a href="#how-to-read">How to read this handbook</a></li>
    <li><a href="#contents">Contents</a></li>
    {"".join(rail)}
  </ol>
</nav>

<main class="book" id="top">
<details class="toc-mobile"><summary>Contents</summary>
  <ol>
    <li><a href="#how-to-read">How to read this handbook</a></li>
    <li><a href="#contents">Contents</a></li>
    {"".join(mobile)}
  </ol>
</details>

<header class="cover">
  <p class="series">Engineering Handbooks</p>
  <h1><span class="book-n">Handbook {cfg["n"]} of 3</span>{cfg["title"]}</h1>
  <p class="subtitle">{cfg["subtitle"]}</p>
  <p class="for">{cfg["for"]}</p>
  <div class="series-list">
    {"".join(series)}
  </div>
  <p class="edition">Edition 1 · Reference implementation: <code>triage-assistant</code> at <code>{{{{REF}}}}</code></p>
</header>

<section class="front" id="how-to-read">
  <h2>How to read this handbook</h2>
  <p>Every chapter is anchored to one real system: <strong>triage-assistant</strong>, an on-call assistant built as the template a team starts its AI services from. Alerts live in Postgres, owned by teams. People sign in with the organization's identity provider and see only their teams' alerts. A model answers their questions from those alerts and the team's runbooks, and cites what it used. The service was load-tested, broken on purpose, and deployed to AWS through a real pipeline. Its code is public at <a href="{{{{TAREPO}}}}">github.com/Parzon/triage-assistant</a>.</p>
  <p>Numbers in this handbook come from that system unless the text says otherwise, and each is given with the setup it was measured on. Code links point to the exact version this edition was checked against, so the line numbers beside an excerpt are the ones you will see on GitHub.</p>
  {reading}
  <p>Each chapter has the same parts, so you can read at the depth you need:</p>
  {SHAPE}
</section>

<section class="front" id="contents">
  <h2>Contents</h2>
  <div class="contents">
    {"".join(contents_parts)}
  </div>
</section>

{body_chapters}

{"".join(apps_html)}

<footer class="series-foot">
  <p>Engineering Handbooks · Handbook {cfg["n"]} of 3 · {cfg["title"]} · Edition 1</p>
  <p>Reference implementation: <a href="{{{{TAREPO}}}}">triage-assistant</a> at <code>{{{{REF}}}}</code>.</p>
</footer>
</main>
</div>
<script src="assets/vendor/highlight.min.js"></script>
<script src="assets/handbook.js"></script>
</body>
</html>
"""
    out = ROOT / cfg["file"]
    out.write_text(expand(page))
    return out


# ---------- Checks ----------

def git_file(path: str) -> list[str] | None:
    try:
        out = subprocess.run(["git", "-C", TA_REPO, "show", f"{TA_REF}:{path}"],
                             capture_output=True, check=True)
    except subprocess.CalledProcessError:
        return None
    return out.stdout.decode("utf-8", "replace").split("\n")


def source_lines(repo: str, path: str) -> list[str] | None:
    if repo == "triage-assistant":
        return git_file(path)
    if repo == "labs":
        p = ROOT / path
        return p.read_text().split("\n") if p.exists() else None
    return None


def normalise(lines: list[str]) -> str:
    return textwrap.dedent("\n".join(l.rstrip() for l in lines)).strip("\n")


BRITISH = re.compile(r"\b(?:[Bb]ehaviours?|[Oo]rganisations?|[Ll]icences?|[Cc]atalogue[ds]?|[Ll]abelled|[Nn]eighbours?|[Rr]ecognis\w*|[Nn]ormalis\w*|[Oo]ptimis(?:e|ed|es|ing|ation)|[Ss]ummaris\w*|[Ss]anitis\w*|[Aa]uthoris\w*|[Mm]inimis\w*|[Dd]efences?|[Jj]udgement|[Gg]rey|[Cc]olours?|[Ff]avour\w*|[Cc]entres?|[Pp]ractised|[Mm]odelled|[Ww]hilst|[Aa]mongst|for ever|LABELLED|[Mm]aths|[Cc]ancell(?:ed|ing)|[Aa]cknowledgement)\b")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌]")
FORBIDDEN = [
    (re.compile(r"\b\d{12}\b"), "a 12-digit number (an AWS account id?)"),
    (re.compile(r"/opt/|/home/|/Users/", re.I), "a local path"),
    (re.compile(r"\b20\d\d-\d\d-\d\d\b"), "a date"),
    (re.compile(r"\b(TODO|FIXME|XXX|lorem)\b"), "a placeholder"),
    (re.compile(r"\bPR #\d+|#7[2-9]\b|#8[0-3]\b"), "a pull request number"),
]
# Terms that must never appear, kept out of the repository: one per line in
# tools/private-terms.txt (git-ignored), matched case-insensitively.
_PRIVATE = ROOT / "tools" / "private-terms.txt"
if _PRIVATE.exists():
    _terms = [t.strip() for t in _PRIVATE.read_text().splitlines() if t.strip() and not t.startswith("#")]
    if _terms:
        FORBIDDEN.append((re.compile("|".join(re.escape(t) for t in _terms), re.I), "a private term"))


def check() -> int:
    problems: list[str] = []
    for book, cfg in BOOKS.items():
        out = ROOT / cfg["file"]
        if not out.exists():
            continue
        page = out.read_text()
        ids = set(re.findall(r'\sid="([^"]+)"', page))
        # Duplicate ids
        all_ids = re.findall(r'\sid="([^"]+)"', page)
        dups = {i for i in all_ids if all_ids.count(i) > 1}
        for d in sorted(dups):
            problems.append(f"{book}: duplicate id {d}")
        # Internal anchors
        for target in set(re.findall(r'href="#([^"]+)"', page)):
            if target not in ids and target != "top":
                problems.append(f"{book}: link to missing #{target}")
        # Unexpanded placeholders
        for ph in sorted(set(re.findall(r"\{\{[A-Z]+\}\}", page))):
            problems.append(f"{book}: unexpanded placeholder {ph}")
        # American English in prose (code excerpts and inline code are quoted as written)
        prose = re.sub(r"<pre.*?</pre>|<code>.*?</code>", " ", page, flags=re.S)
        for word in sorted(set(re.findall(BRITISH, prose))):
            problems.append(f"{book}: British spelling in prose: {word}")
        # HTML elements inside SVG figures render outside the drawing
        for fid, body in re.findall(r'<figure class="fig[^"]*" id="([^"]+)">(.*?)</figure>', page, re.S):
            svg = "".join(re.findall(r"<svg.*?</svg>", body, re.S))
            for tag in sorted(set(re.findall(r"<(code|em|strong|b|i|br|span|a)\b", svg))):
                problems.append(f"{book}: <{tag}> inside the SVG of {fid}")
        # Excerpts
        for attrs, body in re.findall(r'<pre class="code"([^>]*)><code[^>]*>(.*?)</code></pre>', page, re.S):
            repo = re.search(r'data-repo="([^"]+)"', attrs)
            path = re.search(r'data-path="([^"]+)"', attrs)
            lines = re.search(r'data-lines="(\d+)-(\d+)"', attrs)
            if not (repo and path and lines):
                continue
            src = source_lines(repo.group(1), path.group(1))
            if src is None:
                problems.append(f"{book}: excerpt source missing: {repo.group(1)}:{path.group(1)}")
                continue
            a, b = int(lines.group(1)), int(lines.group(2))
            want = normalise(src[a - 1:b])
            got = normalise(html.unescape(body).split("\n"))
            if want != got:
                problems.append(f"{book}: excerpt differs from {path.group(1)} lines {a}-{b}")
        # Links into the reference repository
        prefix = f"{TA_URL}/blob/{TA_REF}/"
        for link in set(re.findall(r'href="(' + re.escape(prefix) + r'[^"]+)"', page)):
            rest = link[len(prefix):]
            path, _, anchor = rest.partition("#")
            src = git_file(path)
            if src is None:
                problems.append(f"{book}: link to missing file {path}")
                continue
            m = re.match(r"L(\d+)(?:-L(\d+))?$", anchor)
            if anchor and not m:
                problems.append(f"{book}: odd anchor {link}")
            elif m and int(m.group(2) or m.group(1)) > len(src):
                problems.append(f"{book}: anchor past the end of {path}: {anchor}")
        tprefix = f"{TA_URL}/tree/{TA_REF}/"
        for link in set(re.findall(r'href="(' + re.escape(tprefix) + r'[^"]+)"', page)):
            path = link[len(tprefix):].rstrip("/")
            r = subprocess.run(["git", "-C", TA_REPO, "cat-file", "-e", f"{TA_REF}:{path}"], capture_output=True)
            if r.returncode:
                problems.append(f"{book}: link to missing folder {path}")
        for link in set(re.findall(r'href="' + re.escape(EH_URL) + r'/(?:blob|tree)/main/([^"#]+)', page)):
            if not (ROOT / link).exists():
                problems.append(f"{book}: link to missing handbook-repo path {link}")
        # Figures: numbering follows the chapter, in order, without gaps
        for sec in re.split(r'(?=<section class="chapter)', page)[1:]:
            num = re.search(r'<span class="ch-num">([^<]+)</span>', sec)
            if not num:
                continue
            n = num.group(1).strip()
            figs = re.findall(r'<span class="fig-n">Figure ([^<]+)</span>', sec)
            expected = [f"{n}.{i}" for i in range(1, len(figs) + 1)]
            if figs != expected:
                problems.append(f"{book}: chapter {n} figure numbers {figs}")
            for ref in re.findall(r"Figure (\d+\.\d+)", strip_tags(re.sub(r'<span class="fig-n">.*?</span>', "", sec))):
                if ref.split(".")[0] == n and ref not in figs:
                    problems.append(f"{book}: chapter {n} mentions missing Figure {ref}")
        # Wording outside code
        prose = re.sub(r"<pre.*?</pre>|<code>.*?</code>|<style>.*?</style>|<script.*?</script>|href=\"[^\"]*\"", " ", page, flags=re.S)
        text = strip_tags(prose)
        if EMOJI.search(text):
            problems.append(f"{book}: emoji {EMOJI.findall(text)[:5]}")
        for rx, what in FORBIDDEN:
            for hit in sorted(set(rx.findall(text)))[:5]:
                problems.append(f"{book}: {what}: {hit!r}")
        for word in ("—",):
            if word in text:
                problems.append(f"{book}: em dash used {text.count(word)} times")
    # The rest of what is published: the landing page, the README and the labs.
    for f in [ROOT / "index.html", ROOT / "README.md", *sorted((ROOT / "labs").rglob("*.md"))]:
        raw = f.read_text()
        if f.suffix == ".md":
            text = re.sub(r"```.*?```|`[^`\n]*`|\]\([^)]*\)", " ", raw, flags=re.S)
        else:
            text = strip_tags(re.sub(r"<style>.*?</style>|<pre.*?</pre>|<code>.*?</code>|href=\"[^\"]*\"", " ", raw, flags=re.S))
        name = f.relative_to(ROOT)
        if EMOJI.search(text):
            problems.append(f"{name}: emoji {EMOJI.findall(text)[:5]}")
        for word in sorted(set(re.findall(BRITISH, text))):
            problems.append(f"{name}: British spelling: {word}")
        for rx, what in FORBIDDEN:
            for hit in sorted(set(rx.findall(text)))[:5]:
                problems.append(f"{name}: {what}: {hit!r}")
    for p in problems:
        print("PROBLEM", p)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


# ---------- Figures ----------

LIGHT = {
    "--paper": "#f6f7f5", "--surface": "#ffffff", "--sunk": "#eef0ed", "--ink": "#1a1e23", "--ink-2": "#48505a",
    "--muted": "#6a727b", "--line": "#d8dcd9", "--line-strong": "#a6adb2", "--good": "#2b7a3d",
    "--good-tint": "#e4f2e6", "--warn": "#965a00", "--warn-tint": "#fbf0dc", "--bad": "#b3261e",
    "--bad-tint": "#fae3e0", "--s1": "#2a78d6", "--s2": "#eb6834", "--s3": "#1baf7a",
}
ACCENTS = {"ai": ("#7b2d84", "#f5e9f6"), "sw": ("#2349a3", "#e7edf9"), "ops": ("#146b55", "#e2f1eb")}


def svg_style(book: str) -> str:
    css = (ROOT / "assets" / "handbook.css").read_text()
    rules = "\n".join(re.findall(r"^svg [^{]+\{[^}]*\}", css, re.M))
    rules = rules.replace("svg ", "")
    tokens = dict(LIGHT)
    tokens["--accent"], tokens["--accent-tint"] = ACCENTS[book]
    tokens["--font-ui"] = '"Archivo", Arial, Helvetica, sans-serif'
    tokens["--font-mono"] = '"JetBrains Mono", Menlo, Consolas, monospace'
    for k, v in sorted(tokens.items(), key=lambda kv: -len(kv[0])):
        rules = rules.replace(f"var({k})", v)
    return rules


def figures() -> int:
    count = 0
    for book, cfg in BOOKS.items():
        out = ROOT / cfg["file"]
        if not out.exists():
            continue
        page = out.read_text()
        style = svg_style(book)
        defs = re.search(r"<defs>.*?</defs>", MARKERS, re.S).group(0)
        target = ROOT / "figures" / book
        target.mkdir(parents=True, exist_ok=True)
        for fid, body in re.findall(r'<figure class="fig[^"]*" id="([^"]+)">(.*?)</figure>', page, re.S):
            found = re.search(r"<svg.*?</svg>", body, re.S)
            if not found:
                continue
            svg = found.group(0)
            svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
            vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
            open_tag_end = svg.index(">") + 1
            bg = f'<rect width="{vb.group(1)}" height="{vb.group(2)}" fill="#ffffff"/>' if vb else ""
            svg = svg[:open_tag_end] + f"<style>{style}</style>{defs}{bg}" + svg[open_tag_end:]
            (target / f"{fid}.svg").write_text(svg)
            count += 1
    print(f"{count} figure(s) exported")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        for book in BOOKS:
            print("built", build_book(book).name)
        return 0
    if cmd == "check":
        return check()
    if cmd == "figures":
        return figures()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
