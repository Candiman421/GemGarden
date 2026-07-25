# GemDesk handoff — read this, then guide the user

**You (Copilot/Cursor) are being handed a working system.** Read this file top to bottom, then walk the
user (CandisMan) through setup and use, one step at a time, waiting for confirmation between steps.
The user prefers short, direct answers. Do not invent paths or commands beyond what's here.

## What GemDesk is
A content-agnostic engine (**GemGarden**, public repo) + a private domain pack (**DevAssist**) that
ingests the user's Excel-Finance **scoring corpus** into a SQLite DB and serves it. Core law: **the DB
is the single source of truth; every source file is a byte-identical projection of `xf_segment` rows.**
Parsed fields are a derived overlay, never the regeneration source.

## Repos on the VM (peers under a plain folder; never nest git repos)
```
C:\Repos\MosBurger\
   GemGarden\           (public engine)   build\{gemdesk-schema.sql, gemdesk-seed.sql, Build-GemGardenDb.ps1}, gemdesk_server.py, docs\
   DevAssist\           (private pack)     gemdesk\{db\xf-domain-schema.sql, parsers\*.py, taxonomy\, docs\}
```

## The pieces (all in DevAssist\gemdesk\parsers\ unless noted)
- `xf_discover.py` — find ingestable `Scoring\` roots under a tree; **prunes Archive** (`--exclude`). Each hit = a *collection*.
- `xf_parse.py` — scan one Scoring tree, stitch content+var+init+scoring+lib by task → a JSON tree.
- `xf_ingest.py` — load files **byte-faithfully** into `xf_file`/`xf_segment`; `regenerate()` reproduces exact bytes (rejects any ingest it can't reproduce); `--lib` loads the function registry.
- `xf_stitch.py` — load the taxonomy: `--tree <parse.json>` (all programs) or `--recon <one.json>`. Resolves each task's sheet+password via the alias header; parses pattern tags `[{family}-{target}-{dynTests}]-{assertion chain}` (families ST=Static Table, SR=Static Range, DT=Dynamic Table, DR=Dynamic Range, + PROTECT/STYLE/CHART/TABLE).
- `xf_funcdrift.py` — function registry + drift (content/format/rename/presence) across `libXF`/`libXA`.
- `xf_checks.py` — deterministic health suite (roundtrip, orphans, hashes, drift warnings); exit code = # fails.
- `gen_copilot_context.py` — regenerate `.github\copilot-instructions.md` (+ `.cursorrules`, `CLAUDE.md`) FROM the DB.
- `GemGarden\gemdesk_server.py` — dependency-free read server + dashboard. Routes: `/api/health|facets|ship-class|functions|drift|files|tasks|patterns|regenerate?id=`.

## Setup (guide the user through these, in order)
0. Requirement: `winget install Python.Python.3.12` (and `winget install Git.Git` if needed).
1. Build the engine DB (green-on-empty):
   `cd C:\Repos\MosBurger\GemGarden ; pwsh -File build\Build-GemGardenDb.ps1`  → expect `GREEN ON EMPTY: OK`.
2. Discover the real scoring roots:
   `cd C:\Repos\MosBurger\DevAssist\gemdesk ; python parsers\xf_discover.py "C:\Repos\MosBurger\Content-Microsoft\Dev\365\Excel"`
   (adjust the path to where the Excel corpus lives; Archive is skipped automatically.)
3. Parse + stitch one collection to start (e.g. FinanceRoot/Finance_v10):
   `python parsers\xf_parse.py "<that Scoring path>" --out taxonomy\release.json`
   `python parsers\xf_ingest.py xf.db --schema db\xf-domain-schema.sql`
   `python parsers\xf_stitch.py xf.db --tree taxonomy\release.json`
4. Ingest a few real files byte-faithfully + the libs (to see drift):
   `python parsers\xf_ingest.py xf.db --file "<a scoring .txt>" --role scoring`
   `python parsers\xf_ingest.py xf.db --lib "<libXF.txt>" --lib "<libXA.txt>" --verify`
5. Health + AI context:
   `python parsers\xf_checks.py xf.db`
   `python parsers\gen_copilot_context.py --engine-db ..\..\GemGarden\_core\gemdesk.db --domain-db xf.db --out .github\copilot-instructions.md --also-cursor --also-claude`
6. Serve + view:
   `python ..\..\GemGarden\gemdesk_server.py --engine-db ..\..\GemGarden\_core\gemdesk.db --domain-db xf.db`
   → open http://localhost:8770/  (Tasks + Scoring patterns cards populate).

## How the user talks to you (Copilot) to work the system
The user drives you in plain language, like: "ingest the FinanceRoot collection", "show me which functions
drifted and where", "regenerate the copilot context", "rebuild the AmortizationSchedule scoring file from the
DB". Translate each to the commands above. Always: **read `.github\copilot-instructions.md` first** — it is
regenerated from the DB and holds the live taxonomy, pattern grammar, function list, and drift warnings.

## Not yet built (roadmap — say so if the user asks for these)
- Collection model + per-collection **purge** (hard delete a Scoring root's rows, then re-ingest cleanly — deletion is OK for this rebuildable corpus).
- Drift **where + how** (per-drift: collection/lib/file + a unified diff).
- Fuller engine seed (UI scaffold rows) + enforcement triggers.
- Full route/SDUI engine (the current server is a walking skeleton).
- Copilot corpus **B** (MCP server so you can query the DB live) + **C** (text index).

## Golden rules when editing scoring files
- Regenerate a file only from `xf_segment` (byte-faithful) — never from parsed fields.
- Preserve whitespace, `=` alignment, blank lines exactly.
- A scoring script = alias header + `[PATTERN]` tag + shared pattern body; reuse the body, don't rewrite it.
- Report library drift; never silently pick a version. `Target=` is the candidate answer region; `Ref=` is the hidden correct answers.
