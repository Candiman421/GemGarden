# GemDesk -- Ingest, Dissect, Regenerate (the recipe engine)

The governing law: **the DB is the only source of truth; every flat file is either ingested INTO it or generated FROM it. No flat file is authoritative.** A file on disk is raw input being absorbed, or a projection of DB rows produced by a recipe. Nothing load-bearing lives only on disk.

## Three lanes

### 1. Ingest (absorb + dissect)
Any corpus file crosses one door:
- registered as a **specimen** (bytes on disk via the `documents` registry; app-typed).
- decomposed by a **decomposer** into **part_extractions** -- competing readings, the many points of view.
- reconciled deterministically into **canonical_parts** + **slots**, with **every derived aspect stored as queryable rows**: facet tags, conventions matched, practices (best / anti), part_relations, and `derivations` that record WHICH deterministic function produced WHICH value from WHICH source. The problem is dissected INTO the database.
- what the engine refuses to resolve lands in the **needs-human** queue; a **teaching** resolves it and is consumed on the next recompute (never a patch on a projection).

### 2. Query (data-driven, absorbed)
Every ingested and derived aspect is queryable through DB endpoints and the QueryBoard. AI agents and tooling read the DB endpoints -- they never scrape flat files, because the flat files are downstream of the DB, not upstream.

### 3. Regenerate (project via recipes)
A **recipe** is a named, versioned generator stored as data: `recipe(name, output_path, source_binding, template, output_kind, triggers)`. It reads DB rows and emits a flat file -- a doc, a config, an instruction file, a spec, a report. Recipes are **deterministic**: the same DB state yields the same file, byte for byte. Files are **projections, regenerated freshly as needed** -- on write (a changed row triggers regeneration of dependents), on request (an endpoint serves a fresh projection), or on build.

## Determinism executes itself
The crux of the rule -- *deterministic functions run because the system triggers them, not because an agent remembers to.* Recipes and checks wire into the same trigger / pipeline substrate as facet enforcement: a row change fires the dependent regenerations and the drift guards; an endpoint request returns a freshly-projected file; a build asserts green-on-empty. Forgetting is impossible because nothing relies on memory -- the seam runs the function.

## The reflexive win: the engine's own files are recipes
`.github/copilot-instructions.md`, `.cursorrules`, `CLAUDE.md`, READMEs, config -- all become recipes projecting from DB rows (directives, conventions, project context). The AI's own instructions are DB-governed and always current. Change a directive row; the instruction file regenerates; every agent picks up the change with zero hand-editing.

## Corpus in the VS Code + Copilot environment
You won't have the Claude chat corpus on the VM, and capturing Copilot chat is the weakest lane -- so we don't lean on it. The strong pattern (all current in VS Code):
- **A. Instructions-as-projection.** Generate `.github/copilot-instructions.md` from the DB via a recipe. VS Code auto-detects that file and applies it to every chat request in the workspace -- Copilot is steered by the DB, refreshed on demand.
- **B. GemDesk as an MCP server.** Expose the DB endpoints (query specimens, parts, conventions, recipes) as an MCP server. Copilot in VS Code has MCP support built in and calls those tools live -- your db endpoints, straight to the AI agents and tooling. The instruction file (A) tells Copilot to prefer the read-only MCP tool over inventing raw SQL.
- **C. Workspace indexing, free.** Because the docs are generated from the DB, Copilot's workspace index stays current automatically -- the projection IS the index surface.
- **D. Copilot chat capture (optional, later).** If you ever want the chat history as a corpus, it becomes a secondary ingest lane (workspace chat logs -> specimens). Fragile and non-authoritative -- raw input, never truth.

Recommendation: **A + B + C** as the spine -- the DB steers Copilot, serves Copilot, and indexes for Copilot. Chat capture stays optional. The result is exactly the ask: files generated fresh from the DB, or served straight from DB endpoints to the agents.

## Scope note
Scoped to GemDesk (generic). On the work VM it is populated with your scrapes and template-families iteratively; the engine never changes -- the garden fills.
