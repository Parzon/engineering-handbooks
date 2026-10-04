# Engineering Handbooks

Three handbooks for experienced engineers coming back to the field: what
changed, why, and where to see it working in real code. Each handbook is a
single web page with a printable PDF, and every chapter is anchored to one
real, public service, [triage-assistant](https://github.com/Parzon/triage-assistant).

| Handbook | Online | PDF |
|---|---|---|
| 1 · AI Engineering & Architecture | [ai-engineering.html](ai-engineering.html) | [pdf/ai-engineering.pdf](pdf/ai-engineering.pdf) |
| 2 · Modern Software Engineering | [software-engineering.html](software-engineering.html) | [pdf/software-engineering.pdf](pdf/software-engineering.pdf) |
| 3 · Cloud Delivery & DevOps | [cloud-delivery.html](cloud-delivery.html) | [pdf/cloud-delivery.pdf](pdf/cloud-delivery.pdf) |

Each chapter has the same parts: the idea in one sentence, the points to
keep, how it was done then and now, figures, the code that implements it
(quoted beside the explanation and linked to GitHub), the decision records
behind it, how to say it in a design review, common traps, and questions
with answers.

## The reference implementation

Code excerpts are checked line by line against triage-assistant at the tag
[`handbook-1`](https://github.com/Parzon/triage-assistant/tree/handbook-1)
(commit `0b81c10`), and every code link points to that tag, so line numbers
match what you see on GitHub.

## What is in this repository

| Path | What |
|---|---|
| `index.html` | the series landing page |
| `ai-engineering.html`, `software-engineering.html`, `cloud-delivery.html` | the three handbooks, built |
| `pdf/` | the handbooks printed to A4 PDF |
| `figures/` | every diagram as a standalone SVG |
| `labs/` | four hands-on labs that accompany Handbook 1 |
| `src/<book>/` | the source: one HTML fragment per chapter, plus the glossary and reading paths |
| `assets/` | the stylesheet, the script and a vendored syntax highlighter |
| `tools/` | the build, the checks and the browser-based QA |

## Building

The build needs Python 3 and a local checkout of triage-assistant (for the
excerpt check); the PDFs and screenshots need Node.js and Google Chrome.

```bash
python3 tools/build.py            # assemble the three handbooks from src/
python3 tools/build.py check      # verify excerpts against the pinned commit, links, anchors, figures and style rules
python3 tools/build.py figures    # export each figure as a standalone SVG

cd tools && npm install && cd ..
node tools/qa.mjs check ai-engineering.html                 # console errors and overflow at three widths
node tools/qa.mjs pdf ai-engineering.html software-engineering.html cloud-delivery.html
```

`tools/build.py` reads the triage-assistant checkout at `TA_REPO` (default:
`../triage-assistant`, with its tags fetched) and pins to the tag in `TA_REF`
(default: `handbook-1`).
