# GemGarden

A generic, DB-centric engine for building **SOLID, DRY, deterministic, well-architected** programs of any nature -- the *GemDesk* body, cloned clean so it can grow any seed.

## What this is
GemGarden is an umbrella engine, not an app. It gives a project:

- **A DB as the single source of truth** -- registries as data, not hardcoded values.
- **A local server + self-describing API** the AI calls; **deterministic functions** scaffold and prove each single-purpose duty, emitting `yes | no | undefined` so drift **fails loud**.
- **A generalized extraction/reconcile substrate** -- decompose any corpus into named parts from many points of view, reconcile deterministically, and refuse to guess where evidence is missing.
- **A self-describing UI (QueryBoard)** where every surface renders from live DB data.
- **Append-only, supersede-only history** -- nothing is deleted; corrections are new rows.

## Principles
- Fix at the source; never work around a limitation.
- Plan first -- persist the reasoning before the change.
- Verify before *done* -- dry-run, integrity check, endpoint probe. Never trust a success banner alone.
- The DB is the brain; flat files are bytes on disk.
- One-way flow: engine patterns flow *in*; tenant content never flows back out.

## Status
Early. The engine is being distilled -- deliberately, by allow-list -- from a proven private instance. See `docs/ROADMAP.md`.

GemGarden ships **engine machinery only**. No owner or tenant content ever enters this repo -- see `.gitignore`.

## Layout (planned)
- `docs/` -- architecture and roadmap
- `scripts/` -- the generic engine (server, DB migrations, deterministic checks)
- `db/` -- schema and migrations (the DB itself is generated, never committed)
