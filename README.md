# Construct Lab — v0.2.0

A local research prototype for evidence-linked construct development. This release adds an **executable AI research loop** to the evidence extraction and researcher-review workspaces. It supersedes the October 7 repository and October 10 demonstration package.

## Start here

Download the **v0.2.0 release**, extract it, and follow [INSTALL-FIRST.txt](INSTALL-FIRST.txt). Python 3.12 on macOS is the tested environment. Linux is a portability target; native Windows is unsupported (file locking currently uses `fcntl`). This is a local, unauthenticated app; do not expose its port to a network.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
chmod +x *.command
.venv/bin/python scripts/load_immersiveness_demo.py
.venv/bin/python scripts/launch_app.py
```

The optional loader adds an Immersiveness example without overwriting an existing pilot. Open http://127.0.0.1:8780, choose a project, then **AI research loop**. Subsequent starts can use **Open Construct Lab.command** on macOS. An older running version must be stopped/restarted before the new version can bind the same address. Back up existing data first using **Backup & recovery**.

## What actually runs

| Operation | Implementation | Role of the researcher |
|---|---|---|
| PDF evidence extraction | Provider request in `extraction.py`; source line validation | Check original PDF and proposed passages |
| Competing definitions and relationships | Live model stage in `research_loop.py` | Inspect interpretations, sources, assumptions and rival constructs |
| Boundary cases and challenges | Separate live model stage | Treat generated cases as synthetic; review classifications |
| Targeted evidence planning | Separate live model stage | Inspect proposed searches and decision rules |
| Evidence discovery | Crossref bibliographic API | Retrieve and inspect sources; metadata is not evidence |
| Revision | Live model stage requiring newly selected evidence | Review the predecessor-to-revision rationale |
| Provenance and review | SQLite records, input fingerprints, immutable originals, review history | Accept for development or reject, with rationale |
| Coding, novelty and stopping rules | Researcher-entered records and deterministic summaries | Specify and assess rules; these do not establish scientific saturation |

Live mode uses the configured OpenAI or compatible chat-completions provider. Enter your own key in **Configure an AI connection**; it stays in server memory, is not exported, and is cleared on restart. External model usage may cost money. A separately running compatible local model can be used instead. Support for an arbitrary provider/model is not guaranteed; it must implement the requested JSON output and token-limit options.

**Synthetic demonstration mode makes no AI request and does not analyze sources.** It exercises the same application review/lineage mechanics using explicitly labeled canned output. It must not be reported as an AI experiment.

## The four-stage workflow

1. Enter your name and research focus; select documented sources. Etymology source/history/finding records and current verified library passages are available, along with excerpts added in this workspace.
2. Select **Generate competing candidates**. Preview exact inputs; authorize transmission; run the stage.
3. Review the proposals, edit their text if needed, check references and limitations, enter a rationale, and **Accept for development** or **Reject**. The original model output remains preserved.
4. Select **Challenge candidates**, choose the accepted generation run, retain its sources, preview and run. Review it.
5. Select **Plan targeted evidence**, choose the accepted challenge run, preview and run. Review it.
6. Search metadata or investigate other documented linguistic/scholarly sources. Inspect the actual source, then add an excerpt, citation, URL, locator and limitations.
7. Select **Revise using added evidence**, choose the accepted plan, and select the new evidence alongside the previous evidence. Run and review. The revised candidate links to its predecessor.
8. Repeat challenges on an accepted revision, or export the full project from the workspace.

A stage cannot consume an unaccepted predecessor. Evidence changes block continuation of the old branch. Invalid source references and incomplete structured responses fail without accepting proposals. Completed identical requests are reused to avoid accidental repeat calls. Acceptance is final for that run; start a new branch for a different judgment. Edited text is reviewed alongside the original response; reference IDs cannot currently be edited in the UI.

The research-loop proposals are maintained in their own reviewable workspace. They do **not** automatically replace approved definitions, resolve existing etymology tasks, populate the old boundary matrix, or establish a saturation decision.

## Reproducibility and limits

Each run records selected evidence snapshots, prior accepted proposals, exact system instructions, schema and prompt version, provider/model, returned usage when available, original response, reviewed response and reviewer rationale. Source IDs validate linkage, not semantic entailment. Etymological analogy generates hypotheses; it cannot by itself validate modern meaning, antecedents, outcomes or causation.

The bundled immersiveness example contains fictional boundary cases and provisional judgments. Historical walkthrough material is a development artifact; submission drafts are distributed separately. These are **not a validated journal submission or a measured comparison against prompting alone**. The contribution requires empirical evaluation against capable prompting baselines with equal evidence, model access and researcher effort.

There is no automatic historical-dictionary crawler, autonomous full-text review, multi-user synchronization, empirical validation, or proven theoretical/nomological saturation. Each researcher has a separate local database. Original PDFs and private research data are not distributed.

## Tests

```sh
.venv/bin/python -m unittest discover -s tests -v
```

See [RELEASE-VALIDATION.md](RELEASE-VALIDATION.md) for exactly what was verified and the limitations of provider testing. Tests include a four-stage fixture path, review gates, new-evidence requirements, reference validation, project isolation and preservation of original versus edited proposals. Fixture tests are not live model tests.

## Data and recovery

Research data is stored under `data/`, excluded from Git. Use **Backup & recovery → Create backup now** before updates and preserve the database backup plus checksum. Project JSON export is an audit export, not a full database restore. Optional OCR requires the Node dependencies in `package.json` or a supported native Tesseract installation; review OCR against original pages.
