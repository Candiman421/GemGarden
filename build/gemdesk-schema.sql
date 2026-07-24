-- gemdesk-schema.sql  --  GemDesk engine schema (content-agnostic core)
-- Frozen from the PiQuix control-plane engine surface: 34 generic substrate tables + live views.
-- Domain tables (fin_*, address*, merchant*, purchase*, receipt*, ocr*, clearveil_*, category*) are NOT part of the engine.
-- Green-on-empty: this stands up an empty, integrity-clean engine DB. Seed adds governance rows (see gemdesk-seed.sql).
PRAGMA foreign_keys = OFF;
PRAGMA journal_mode = WAL;

-- ===== tables =====
CREATE TABLE annotations (
  id            TEXT PRIMARY KEY,
  target_kind   TEXT NOT NULL,
  target_id     TEXT NOT NULL,
  kind          TEXT NOT NULL CHECK(kind IN ('comment','correction','pattern-fit','pattern-break','link','context')),
  body          TEXT NOT NULL,
  ref_kind      TEXT,
  ref_id        TEXT,
  author        TEXT,
  created       TEXT NOT NULL,
  superseded_by TEXT,
  schema_v      INTEGER NOT NULL DEFAULT 1
) STRICT;

CREATE TABLE check_findings (
  id            TEXT PRIMARY KEY,
  run_id        TEXT NOT NULL,
  check_id      TEXT NOT NULL,
  verdict       TEXT NOT NULL,
  citation      TEXT,
  evidence      TEXT,
  audience      TEXT,
  created       TEXT NOT NULL,
  superseded_by TEXT
) STRICT;

CREATE TABLE check_pipeline_steps (
  id            TEXT PRIMARY KEY,
  pipeline_id   TEXT NOT NULL,
  step_order    INTEGER NOT NULL,
  check_id      TEXT NOT NULL,
  created       TEXT NOT NULL,
  superseded_by TEXT
) STRICT;

CREATE TABLE check_pipelines (
  id            TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  semantics     TEXT,
  audience      TEXT,
  active        INTEGER NOT NULL DEFAULT 1,
  created       TEXT NOT NULL,
  superseded_by TEXT
, intent TEXT) STRICT;

CREATE TABLE check_registry (
  id             TEXT PRIMARY KEY,
  asserts        TEXT NOT NULL,
  input_contract TEXT,
  uncovered_set  TEXT,
  audience       TEXT,
  active         INTEGER NOT NULL DEFAULT 1,
  created        TEXT NOT NULL,
  superseded_by  TEXT
, executable_id TEXT, invocation_json TEXT, result_mode TEXT) STRICT;

CREATE TABLE check_runs (
  id                TEXT PRIMARY KEY,
  pipeline_id       TEXT,
  check_id          TEXT,
  started           TEXT NOT NULL,
  finished          TEXT,
  determinacy_ratio REAL,
  created           TEXT NOT NULL
) STRICT;

CREATE TABLE check_runtimes (
    id                   TEXT PRIMARY KEY,
    launcher             TEXT NOT NULL,
    launcher_located_by  TEXT,
    base_args            TEXT,
    script_source        TEXT,
    availability_probe   TEXT,
    extensions           TEXT,
    note                 TEXT,
    enabled              INTEGER NOT NULL DEFAULT 1,
    created              TEXT,
    updated              TEXT,
    superseded_by        TEXT
);

CREATE TABLE decisions (
  id            TEXT PRIMARY KEY,
  folder        TEXT NOT NULL,
  seq           INTEGER NOT NULL,
  title         TEXT NOT NULL,
  status        TEXT NOT NULL,
  decision      TEXT NOT NULL DEFAULT '',
  path          TEXT NOT NULL,
  date          TEXT NOT NULL,
  supersedes    TEXT,
  superseded_by TEXT,
  created       TEXT NOT NULL,
  updated       TEXT NOT NULL,
  schema_v      INTEGER DEFAULT 1
, scope TEXT);

CREATE TABLE decision_links (
  from_id   TEXT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
  to_id     TEXT NOT NULL,
  link_kind TEXT NOT NULL,
  PRIMARY KEY (from_id, to_id, link_kind)
);

CREATE TABLE decision_options (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  dec_id    TEXT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
  label     TEXT NOT NULL,
  summary   TEXT,
  verdict   TEXT NOT NULL,
  reason    TEXT
, status TEXT NOT NULL DEFAULT 'live', superseded_by INTEGER);

CREATE TABLE decision_revisions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  decision_id   TEXT NOT NULL,
  revision      INTEGER NOT NULL,
  ts            TEXT NOT NULL,
  author        TEXT DEFAULT 'owner',
  change_note   TEXT,
  title         TEXT,
  status        TEXT,
  body          TEXT,
  date          TEXT,
  supersedes    TEXT,
  superseded_by TEXT,
  UNIQUE(decision_id, revision)
);

CREATE TABLE directives (
  id        TEXT PRIMARY KEY,
  category  TEXT NOT NULL,
  seq       INTEGER NOT NULL DEFAULT 0,
  key       TEXT,
  value     TEXT NOT NULL,
  active    INTEGER NOT NULL DEFAULT 1,
  created   TEXT NOT NULL,
  updated   TEXT NOT NULL
, project TEXT);

CREATE TABLE "documents" (
  id            TEXT PRIMARY KEY,
  kind          TEXT NOT NULL,
  project       TEXT,
  title         TEXT NOT NULL,
  path          TEXT NOT NULL,
  hash          TEXT,
  tax_year      INTEGER,
  lifecycle     TEXT NOT NULL DEFAULT 'active',
  note          TEXT,
  created       TEXT NOT NULL,
  updated       TEXT NOT NULL,
  superseded_by TEXT,
  schema_v      INTEGER NOT NULL DEFAULT 1
, parent_doc_id TEXT) STRICT;

CREATE TABLE doc_sections (
  id            TEXT PRIMARY KEY,
  doc_id        TEXT NOT NULL REFERENCES documents(id),
  seq           INTEGER NOT NULL DEFAULT 0,
  heading       TEXT,
  body          TEXT,
  created       TEXT NOT NULL,
  updated       TEXT NOT NULL,
  superseded_by TEXT,
  schema_v      INTEGER NOT NULL DEFAULT 1
) STRICT;

CREATE TABLE doc_links (
  id            TEXT PRIMARY KEY,
  from_doc_id   TEXT NOT NULL,
  to_doc_id     TEXT NOT NULL,
  link_kind     TEXT NOT NULL CHECK(link_kind IN ('duplicate','supersedes','page-of','evidences','corroborates','related')),
  status        TEXT NOT NULL DEFAULT 'proposed' CHECK(status IN ('proposed','confirmed','rejected')),
  note          TEXT,
  created       TEXT NOT NULL,
  superseded_by TEXT
) STRICT;

CREATE TABLE facet_registry (
  tag_type      TEXT PRIMARY KEY,
  value_set     TEXT NOT NULL,
  cardinality   TEXT NOT NULL DEFAULT 'single' CHECK(cardinality IN ('single','multi')),
  default_value TEXT,
  applies_to    TEXT NOT NULL DEFAULT 'item',
  resolver      TEXT NOT NULL DEFAULT 'precedence',
  note          TEXT,
  active        INTEGER NOT NULL DEFAULT 1,
  created       TEXT NOT NULL,
  updated       TEXT NOT NULL
, enforce_json TEXT) STRICT;

CREATE TABLE project_facets (
  project       TEXT NOT NULL,
  tag_type      TEXT NOT NULL REFERENCES facet_registry(tag_type),
  default_value TEXT NOT NULL,
  created       TEXT NOT NULL,
  updated       TEXT NOT NULL,
  PRIMARY KEY (project, tag_type)
) STRICT;

CREATE TABLE gotchas (
  id        TEXT PRIMARY KEY,
  symptom   TEXT NOT NULL,
  action    TEXT,
  fix       TEXT NOT NULL,
  project   TEXT,
  source    TEXT,
  created   TEXT NOT NULL,
  updated   TEXT NOT NULL
, superseded_by TEXT);

CREATE TABLE items (
  id          TEXT PRIMARY KEY,
  kind        TEXT NOT NULL,
  title       TEXT NOT NULL,
  body        TEXT,
  status      TEXT NOT NULL DEFAULT 'open',
  project     TEXT,
  priority    TEXT,
  due         TEXT,
  created     TEXT NOT NULL,
  updated     TEXT NOT NULL,
  expires     TEXT,
  supersedes  TEXT,
  source      TEXT DEFAULT 'api',
  schema_v    INTEGER DEFAULT 1
, superseded_by TEXT);

CREATE TABLE item_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  ts          TEXT NOT NULL,
  event_kind  TEXT NOT NULL,
  from_val    TEXT,
  to_val      TEXT,
  note        TEXT,
  author      TEXT DEFAULT 'owner'
);

CREATE TABLE item_tags (
  item_id   TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  tag_type  TEXT NOT NULL,
  tag       TEXT NOT NULL,
  PRIMARY KEY (item_id, tag_type, tag)
);

CREATE TABLE peeps (
  id            TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  aka           TEXT,
  relation      TEXT,
  status        TEXT,
  note          TEXT,
  created       TEXT NOT NULL,
  updated       TEXT NOT NULL,
  superseded_by TEXT,
  schema_v      INTEGER NOT NULL DEFAULT 1
) STRICT;

CREATE TABLE pk_row_ship_class (
  row_ship_class_id TEXT PRIMARY KEY,
  table_name        TEXT NOT NULL,
  row_id            TEXT NOT NULL,
  ship_class        TEXT NOT NULL,
  note              TEXT,
  created           TEXT NOT NULL,
  updated           TEXT NOT NULL,
  superseded_by     TEXT
) STRICT;

CREATE TABLE projects (
  name           TEXT PRIMARY KEY,
  folder         TEXT,
  claude_project TEXT,
  tier           INTEGER,
  synthesis      TEXT,
  repo           TEXT,
  definition     TEXT,
  description    TEXT,
  scope_limit    TEXT,
  parent         TEXT,
  meta_json      TEXT,
  created        TEXT NOT NULL,
  updated        TEXT NOT NULL
, status TEXT, current_focus TEXT, synthesis_version INTEGER, synthesis_updated TEXT);

CREATE TABLE project_edges (
  id          INTEGER PRIMARY KEY,
  from_folder TEXT NOT NULL,
  to_folder   TEXT NOT NULL,
  edge_kind   TEXT NOT NULL CHECK(edge_kind IN ('hard-blocker','soft-judgement','relates','feeds')),
  note        TEXT,
  created     TEXT NOT NULL
) STRICT;

CREATE TABLE providers (
  id       TEXT PRIMARY KEY,
  name     TEXT NOT NULL,
  key_env  TEXT,
  enabled  INTEGER NOT NULL DEFAULT 1,
  note     TEXT,
  created  TEXT NOT NULL,
  updated  TEXT NOT NULL
);

CREATE TABLE "registered_executables" (
  executable_id TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  kind          TEXT NOT NULL,
  path          TEXT,
  venv          TEXT,
  digest_sha256 TEXT,
  digest_verify TEXT NOT NULL DEFAULT 'off' CHECK(digest_verify IN ('off','warn','enforce')),
  enabled       INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
  note          TEXT,
  meta_json     TEXT,
  created       TEXT NOT NULL,
  updated       TEXT NOT NULL,
  superseded_by TEXT,
  purity        TEXT,
  runtime_id    TEXT,
  base_args     TEXT
) STRICT;

CREATE TABLE "storage_locations" (
  key       TEXT PRIMARY KEY,
  base      TEXT NOT NULL CHECK(base IN ('root','parent','absolute')),
  rel_path  TEXT NOT NULL,
  kind      TEXT NOT NULL CHECK(kind IN ('db','dir','fs-root')),
  backup    TEXT NOT NULL DEFAULT 'never' CHECK(backup IN ('session','ondemand','never')),
  note      TEXT,
  created   TEXT NOT NULL,
  updated   TEXT NOT NULL,
  connection_string TEXT,
  driver    TEXT NOT NULL DEFAULT 'sqlite'
);

CREATE TABLE ui_views (
  name        TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  lifecycle   TEXT NOT NULL DEFAULT 'active' CHECK(lifecycle IN ('idea','proposed','active','deprecated','archived')),
  note        TEXT,
  created     TEXT NOT NULL,
  updated     TEXT NOT NULL
, nav_group TEXT) STRICT;

CREATE TABLE ui_components (
  name        TEXT PRIMARY KEY,
  renderer    TEXT NOT NULL,
  prop_schema_json TEXT,
  note        TEXT,
  active      INTEGER NOT NULL DEFAULT 1,
  created     TEXT NOT NULL
) STRICT;

CREATE TABLE ui_bindings (
  name        TEXT PRIMARY KEY,
  kind        TEXT NOT NULL DEFAULT 'route' CHECK(kind IN ('route','static')),
  ref         TEXT NOT NULL,
  result_path TEXT,
  params_json TEXT,
  note        TEXT,
  created     TEXT NOT NULL
) STRICT;

CREATE TABLE ui_view_slots (
  id          INTEGER PRIMARY KEY,
  view        TEXT NOT NULL REFERENCES ui_views(name),
  slot        TEXT NOT NULL DEFAULT 'main',
  seq         INTEGER NOT NULL DEFAULT 0,
  component   TEXT NOT NULL REFERENCES ui_components(name),
  binding     TEXT REFERENCES ui_bindings(name),
  props_json  TEXT,
  active      INTEGER NOT NULL DEFAULT 1,
  created     TEXT NOT NULL
) STRICT;

CREATE TABLE ui_settings (
  scope       TEXT NOT NULL,
  setting_key TEXT NOT NULL,
  value_json  TEXT NOT NULL,
  author      TEXT,
  updated     TEXT NOT NULL,
  PRIMARY KEY (scope, setting_key)
) STRICT;

CREATE TABLE void_records (
  id            TEXT PRIMARY KEY,
  target_kind   TEXT NOT NULL,
  target_id     TEXT NOT NULL,
  reason        TEXT NOT NULL,
  void_class    TEXT,
  voided_by     TEXT,
  created       TEXT NOT NULL,
  superseded_by TEXT
) STRICT;

-- ===== live views (superseded_by IS NULL projections) =====
CREATE VIEW v_annotations_live AS SELECT * FROM annotations WHERE superseded_by IS NULL;
CREATE VIEW v_check_findings_live AS SELECT * FROM check_findings WHERE superseded_by IS NULL;
CREATE VIEW v_check_pipeline_steps_live AS SELECT * FROM check_pipeline_steps WHERE superseded_by IS NULL;
CREATE VIEW v_check_pipelines_live AS SELECT * FROM check_pipelines WHERE superseded_by IS NULL;
CREATE VIEW v_check_registry_live AS SELECT * FROM check_registry WHERE superseded_by IS NULL;
CREATE VIEW v_check_runtimes_live AS SELECT * FROM check_runtimes WHERE superseded_by IS NULL;
CREATE VIEW v_decision_options_live AS SELECT * FROM decision_options WHERE superseded_by IS NULL;
CREATE VIEW v_decision_revisions_live AS SELECT * FROM decision_revisions WHERE superseded_by IS NULL;
CREATE VIEW v_decisions_live AS SELECT * FROM decisions WHERE superseded_by IS NULL;
CREATE VIEW v_doc_links_live AS SELECT * FROM doc_links WHERE superseded_by IS NULL;
CREATE VIEW v_doc_sections_live AS SELECT * FROM doc_sections WHERE superseded_by IS NULL;
CREATE VIEW v_documents_live AS SELECT * FROM documents WHERE superseded_by IS NULL;
CREATE VIEW v_gotchas_live AS SELECT * FROM gotchas WHERE superseded_by IS NULL;
CREATE VIEW v_items_live AS SELECT * FROM items WHERE superseded_by IS NULL;
CREATE VIEW v_peeps_live AS SELECT * FROM peeps WHERE superseded_by IS NULL;
CREATE VIEW v_pk_row_ship_class_live AS SELECT * FROM pk_row_ship_class WHERE superseded_by IS NULL;
CREATE VIEW v_registered_executables_live AS SELECT * FROM registered_executables WHERE superseded_by IS NULL;
CREATE VIEW v_void_records_live AS SELECT * FROM void_records WHERE superseded_by IS NULL;

-- engine-only timeline (domain sources removed from the PiQuix original)
CREATE VIEW v_timeline AS
SELECT ts AS ts, 'item_event' AS source, event_kind AS event_kind, 'item' AS target_kind, item_id AS target_id, COALESCE(note, event_kind) AS title, CAST(id AS TEXT) AS source_id FROM item_events
UNION ALL
SELECT ts, 'decision_revision', 'revision', 'decision', decision_id, COALESCE(change_note, title, 'revision ' || revision), CAST(id AS TEXT) FROM decision_revisions
UNION ALL
SELECT created, 'annotation', kind, target_kind, target_id, substr(body, 1, 120), id FROM annotations WHERE superseded_by IS NULL
UNION ALL
SELECT created, 'gotcha', 'gotcha', 'project', COALESCE(project, 'GemDesk'), substr(symptom, 1, 120), id FROM gotchas WHERE superseded_by IS NULL;
