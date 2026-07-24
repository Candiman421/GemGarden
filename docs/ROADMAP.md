# GemGarden Roadmap

## How the engine crosses over (important)
GemGarden is **not** a copy of the source working tree. The source engine and its owner-domain code currently share files, and this repo is public -- a bulk copy would either leak private data or ship broken partials. Instead the engine is distilled by **allow-list**: only provably-generic, `engine-seed` / `tenant-template` material crosses, and the DB is **rebuilt from generic migrations + a seed**, never copied. This is the safe path and it is deliberate.

## Locked order
1. **ship_class provenance keystone** -- the validated choke-point write primitive + read seam. **DONE.**
2. **Portable engine seed ("fertilizer")** -- a declarative, idempotent artifact of the tagged generic rows (facets, runtimes, executables, the UI shell, storage lanes, generic directives). Authored here, applied on the target machine -- IN PROGRESS.
3. **Build-on-empty** -- run the generic migrations against an empty DB, apply the seed, and assert the clone comes up green with zero content.
4. **Directive / persona split** -- generic engine rules travel; naming and authored voice stay private.
5. **Contract versioning** -- response shapes named and versioned as data, sealed once stable.
6. **Domain ontology tables** -- the Specimen / Part / Decomposer / Composition substrate (see ARCHITECTURE section 3), built on the target machine.
7. **QueryBoard** -- the self-describing UI, generalized from the DB.

## Current status
- Scaffold, safety rail (`.gitignore`), and plans: landed.
- Engine seed + build-on-empty: next.
- Everything content-specific is filled on the target machine, with scripts and rules taught there.
