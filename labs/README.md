# Labs

Four hands-on labs that accompany Handbook 1, *AI Engineering & Architecture*.
Each one breaks or measures one part of the reference service,
[triage-assistant](https://github.com/Parzon/triage-assistant), and shows
what that looks like from the outside.

| Lab | What it shows | Needs |
|---|---|---|
| [rag-debugging](rag-debugging/README.md) | one fault per retrieval stage, recognized from the outside (Handbook 1, Chapter 4) | Ollama models for most steps |
| [ai-observability](ai-observability/README.md) | a worse or slower answer, diagnosed from telemetry alone (Chapter 8) | the monitoring stack; a real model for some steps |
| [ai-security](ai-security/README.md) | redaction measured, an investigation with the audit trail, a tool design review (Chapter 9) | the dev stack; the mock model is enough |
| [ai-cost](ai-cost/README.md) | what an answer costs, where its tokens go, and which settings move the bill (Chapter 10) | Ollama models |

## Running them

Each lab runs against a checkout of triage-assistant, inside its dev api
container. Clone it next to this repository, or point `TRIAGE_DIR` at it:

```bash
git clone https://github.com/Parzon/triage-assistant.git
export TRIAGE_DIR=/path/to/triage-assistant
```

Then follow each lab's README. Every lab has an `answers.md` with what was
observed when it was written: the model samples, so your numbers will
differ, but the diagnoses should not.
