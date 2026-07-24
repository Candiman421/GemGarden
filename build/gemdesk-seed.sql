-- gemdesk-seed.sql  --  GemDesk engine governance seed (minimal, green-on-empty)
-- Seeds only the engine governance vocabulary + runtimes + a keyless provider, all engine-seed class.
-- Fuller scaffold (UI views/components/bindings, executables allowlist, storage templates) = a later seed pass.
-- Notes here are trimmed; the authoritative long-form notes live in the source engine + docs.

-- ===== facet_registry: the 10 engine governance vocabularies =====
INSERT INTO facet_registry (tag_type,value_set,cardinality,default_value,applies_to,resolver,note,active,created,updated,enforce_json) VALUES
 ('audience','human,desk','single','desk','item','precedence','Routing: desk=operational/AI; human=life-admin/dashboard.',0,'2026.07.24-000000','2026.07.24-000000',NULL),
 ('check_result_mode','exit_code,json','single','exit_code','check','none','How a check reports: exit_code | json finding contract.',1,'2026.07.24-000000','2026.07.24-000000','{"table":"check_registry","column":"result_mode"}'),
 ('check_verdict','pass,fail,undetermined','single',NULL,'check_finding','none','Verdict of one finding; undetermined is first-class.',1,'2026.07.24-000000','2026.07.24-000000','{"table":"check_findings","column":"verdict"}'),
 ('decision_status','proposed,accepted,rejected,superseded,deprecated','single','proposed','decision','none','Allowed decision (ADR) status values.',1,'2026.07.24-000000','2026.07.24-000000','{"column":"status","table":"decisions"}'),
 ('executable_purity','read-only,mutating,unknown','single',NULL,'registered_executable','none','Purity gate: the check executor runs read-only only.',1,'2026.07.24-000000','2026.07.24-000000','{"table":"registered_executables","column":"purity"}'),
 ('layer','desk,content','single','desk','item','precedence','desk=operational/build surface; content=produced substance.',1,'2026.07.24-000000','2026.07.24-000000',NULL),
 ('pipeline_semantics','stop-on-first-fail,collect-all','single','collect-all','check_pipeline','none','Pipeline composition: gate vs audit.',1,'2026.07.24-000000','2026.07.24-000000','{"table":"check_pipelines","column":"semantics"}'),
 ('project_classification','project,layer,pattern,proposed-dll','single','project','project','none','Self-describes each projects-registry entry.',1,'2026.07.24-000000','2026.07.24-000000',NULL),
 ('ship_class','engine-seed,tenant-template,tenant-data,owner-private','single','owner-private','row','none','Provenance/shipping class of any registry row; default owner-private (fail-closed).',1,'2026.07.24-000000','2026.07.24-000000',NULL),
 ('void_class','test-fixture,never-real,erroneous-write,duplicate','single',NULL,'void_record','none','Why a row should never have existed.',1,'2026.07.24-000000','2026.07.24-000000','{"table":"void_records","column":"void_class"}');

-- ===== check_runtimes: node / powershell / python =====
INSERT INTO check_runtimes (id,launcher,launcher_located_by,base_args,script_source,availability_probe,extensions,note,enabled,created,updated) VALUES
 ('node','node','path','[]','none','["--version"]','[".js",".mjs",".cjs"]','Node.js as a syntax instrument (node --check).',1,'2026.07.24-000000','2026.07.24-000000'),
 ('powershell','pwsh','path','["-NoProfile","-NonInteractive","-File"]','search-name','["--version"]','[".ps1"]','PowerShell 7; .ps1 resolved by name; -File must precede the script path.',1,'2026.07.24-000000','2026.07.24-000000'),
 ('python','python','venv','[]','path-column','["--version"]','[".py"]','Python via executable venv, falling back to PATH.',1,'2026.07.24-000000','2026.07.24-000000');

-- ===== providers: keyless local provider ships verbatim =====
INSERT INTO providers (id,name,key_env,enabled,note,created,updated) VALUES
 ('ollama','Ollama (local)',NULL,1,'Local inference. No API key.','2026.07.24-000000','2026.07.24-000000');

-- ===== ship_class manifest for the seeded rows =====
INSERT INTO pk_row_ship_class (row_ship_class_id,table_name,row_id,ship_class,note,created,updated) VALUES
 ('SHC-seed-f01','facet_registry','audience','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-f02','facet_registry','check_result_mode','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-f03','facet_registry','check_verdict','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-f04','facet_registry','decision_status','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-f05','facet_registry','executable_purity','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-f06','facet_registry','layer','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-f07','facet_registry','pipeline_semantics','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-f08','facet_registry','project_classification','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-f09','facet_registry','ship_class','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-f10','facet_registry','void_class','engine-seed','engine governance facet','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-r01','check_runtimes','node','engine-seed','generic runtime','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-r02','check_runtimes','powershell','engine-seed','generic runtime','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-r03','check_runtimes','python','engine-seed','generic runtime','2026.07.24-000000','2026.07.24-000000'),
 ('SHC-seed-p01','providers','ollama','engine-seed','keyless local provider','2026.07.24-000000','2026.07.24-000000');
