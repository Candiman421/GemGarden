# GemGarden Architecture

GemGarden is a distillation of a proven engine into its generic, content-agnostic core. It stands outside any single problem, naming, or algorithm and offers a compatible abstraction that any project can seed.

## 1. The DB is the brain
Every durable fact -- config, rules, UI, checks, decisions -- is a row, not a hardcode. Registries are data:
- **facets** -- governed enumerations (validate a value against a live value-set; extend by INSERT, never a code edit).
- **executables / runtimes** -- the tool allowlist and how each language is invoked, as data (adding a language is an INSERT).
- **decisions / annotations** -- the architectural record and its corrections, append-only.
- **documents** -- a registry over meaningful flat files (bytes on disk, metadata in the DB).

## 2. Provenance keystone: ship_class
Every row carries a provenance tag through one validated choke-point primitive: `engine-seed`, `tenant-template`, `tenant-data`, or `owner-private`. The default is `owner-private` -- **fail-closed**: an untagged row never ships, because a leak is silent and bad while a miss is loud and recoverable. A distillation ships `engine-seed` + `tenant-template` only. Re-classing supersedes append-only; nothing is deleted.

## 3. Generalized extraction/reconcile substrate
The multi-point-of-view reconciliation engine, lifted free of any one domain:

| Role | Meaning |
|---|---|
| **Specimen** | any corpus file, app-typed (excel / word / ppt / pdf / adobe / source) |
| **Template-family** | the repeated pattern a specimen follows (e.g. year x program) |
| **Decomposer profile** | teachable parsing knowledge, per family, naming a registered tool |
| **Part-extractions** | competing decompositions -- the many points of view |
| **Composition / validation gate** | deterministic assertions: naming, spacing, convention, best-practice |
| **Canonical parts + slots** | the promoted, named, validated micro-units and where they fit |
| **Source authority** | gold exemplar > variant > draft; proven-best > nuance > anti-pattern |
| **Part relations** | composes-with / variant-of / requires / supersedes / contradicts |
| **Needs-human queue** | what the engine refuses to guess -- the chicken-and-egg surface |
| **Teachings** | human input consumed *before* recompute, never a patch on a projection |
| **Pattern recompute** | which parts/conventions are canonical = a recomputed projection over authority x evidence, order-independent |
| **Drift guards** | deterministic checks that prove conventions and kill false positives/negatives |

New nouns on top: **Convention**, **Practice** (best / anti), **Composition**, **Requirement**, **Rubric / Score**.

## 4. Determinism lives in a pipeline, not in prose
Proofs are registered **checks** run as **pipelines**. Each check declares what it asserts and what it does NOT cover, names a registered tool, and is **purity-gated** (only read-only tools run). Every check emits `pass | fail | undetermined`; a determinacy ratio is computed, never self-reported. As coverage grows, the AI's non-deterministic role shrinks by construction: AI scaffolds, deterministic functions take over, checks certify.

## 5. QueryBoard: a self-describing UI
The DB describes the screens and the data within them (views -> components -> data bindings). Every surface renders from a live query -- the aim is that everything visible is queryable at run time, from smart widgets up.

## 6. Laws that hold everywhere
- **Supersede-only / no-delete** -- history is append-only; corrections are new rows that point back.
- **Plan-first** -- the reasoning and rejected alternatives are persisted before the change.
- **Fix-not-workaround** -- limitations get fixed at the source.
- **Self-describing names** -- a name a fresh reader can understand beats brevity, at every level.
- **One-way flow** -- engine patterns flow into a clone; tenant content never flows back.
