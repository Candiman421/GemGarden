# GemDesk -- Engine Specification (the seed garden)

GemDesk is the generic, content-agnostic engine at the heart of GemGarden. An **empty GemDesk is a prepared garden**: every bed (registry) exists, empty, with one validated way to fill it. Any project -- a document-scoring domain, a game, an Adobe toolchain -- is *grown* by filling beds, never by editing the engine.

## Naming law (true names)
1. **Self-describing over brief** -- a fresh reader must understand a name with zero history.
2. **Unbranded** -- the engine carries no origin-instance brand; tables and functions read as plain English.
3. **One canonical noun per concept** (the ontology); no synonyms.
4. **Supersede-only** -- names evolve by adding a better definition that points back, never by deletion or silent rewrite.

The names below are GemDesk's TARGET form. The originating instance converges to them incrementally (supersede-only, opportunistic -- never a destabilizing mass-rename of a live engine); the build translates instance names to these on the way into GemGarden.

## The beds (registries), by tier

### Tier 0 -- Governance
- `facets` -- governed enumerations. A value is validated against a live value-set; a vocabulary grows by INSERT, never a code edit. Seam: `Test-FacetValue`, `POST /api/facets`.
- `ship_class` -- the provenance tag on every row: engine-seed | tenant-template | tenant-data | owner-private. Default owner-private (fail-closed). The distillation gate. Seam: `Set-RowShipClass`, `/api/ship-class`.

### Tier 1 -- Record (append-only knowledge)
- `decisions` (+ `options`, `links`, `revisions`) -- architecture decisions as data.
- `annotations` -- universal, recursive commentary and corrections on any row.
- `gotchas` -- captured landmines.
- `documents` (+ `sections`) -- a registry over meaningful flat files; bytes on disk, metadata in the DB.

### Tier 2 -- Proof (the determinism substrate)
- `runtimes` -- how each language is invoked; adding a language is an INSERT.
- `executables` -- the tool allowlist; digest-signed, purity-tagged (only read-only tools run in checks).
- `checks` -- declared proofs: what each asserts AND what it does NOT cover (the boundary published as data).
- `check_pipelines` (+ `steps`) -- ordered proof runs with stop-on-fail / collect-all semantics.
- `check_runs` (+ `findings`) -- executions and verdicts: **pass | fail | undetermined**, with a computed determinacy ratio. Drift fails loud here.

### Tier 3 -- Structure (the umbrella)
- `projects` (+ `project_edges`) -- many projects under one roof; typed dependency edges surface the unblocked frontier.
- `items` -- work units on the frontier.

### Tier 4 -- Presentation (QueryBoard / self-describing UI)
- `views`, `components`, `bindings` -- the DB describes the screens and the data in them; every surface renders from a live query.
- `settings` -- the display-override layer (state words, never a stylesheet's hex opinion).

### Tier 5 -- Integrity
- `voids` -- mark rows that should never have existed; audited, hidden from default views, never deleted.
- `storage_locations` -- the lane / fs-root registry; the write-surface allowlist, as data.

## Universal laws (hold in every bed)
- One validated **write seam** per registry; the **read side ships with the writer** (a write-only seam is unverifiable).
- **Supersede-only / no-delete** -- corrections are new rows pointing back.
- **Fail-closed and fail-loud** -- an unknown or unvalidated value is refused with the allowed set, never silently accepted.
- **Plan-first** -- the reasoning and the rejected alternatives are persisted before the change.

## The domain substrate (what a garden grows)
Every tenant project decomposes a corpus and recomposes it to answer scored requirements. GemDesk ships these forms as **tenant-template** (present, empty):

`specimens` - `template_families` - `decomposer_profiles` - `part_extractions` - `canonical_parts` - `slots` - `part_relations` - `conventions` - `practices` - `compositions` - `requirements` - `rubrics` - `teachings` - `drift_guards`

(See ARCHITECTURE.md section 3 for the roles.) The engine is **app-agnostic**: adding Excel / Word / PPT / Adobe is a new decomposer + template-family -- an INSERT, never an engine edit.

## Placement (true positioning) -- repo layout
- `engine/` -- the server, the DB-migration runner, the route registry, and the inspection/compliance (check) scripts.
- `db/` -- schema and migrations. `gemdesk.db` is BUILT, never committed.
- `ui/` -- the self-describing renderers and static assets.
- `docs/` -- architecture, roadmap, this spec.
- `gemdesk.db` (control plane) + declared `storage_locations` lanes; the tier structure is data, not hardcode.

## Seed & fill (green-on-empty)
1. Run the generic migrations -> an empty `gemdesk.db` with **every bed present**.
2. Apply the **seed**: the engine-seed + tenant-template rows (facets, runtimes, executables, the UI shell, generic directives, the empty domain forms).
3. Assert **GREEN-ON-EMPTY**: the check pipelines pass against zero content -- an empty garden that is provably well-formed.
4. On the target machine: create projects, register decomposer tools, teach conventions, fill tenant-data. The engine never changes; the garden fills.

## Name evolution (instance -> GemDesk), supersede-only
`pk_row_ship_class -> ship_class` - `Set-PkRowShipClass -> Set-RowShipClass` - `Set-PkRowSuperseded -> Set-RowSuperseded` - `Test-PkFacetValue -> Test-FacetValue` - `Invoke-Pk* -> Invoke-*` - `facet_registry -> facets` - `registered_executables -> executables` - `check_runtimes -> runtimes` - `ui_views/ui_components/ui_bindings -> views/components/bindings`. Instance-specific project and domain names never cross.
