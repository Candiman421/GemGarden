#!/usr/bin/env python3
"""
gemdesk_server.py -- minimal, dependency-free GemDesk read server (Python stdlib only).

Serves the engine DB (facets, ship-class, checks) and, if present, a domain DB (XF files,
functions, drift) over small JSON routes, plus a one-page dashboard. READ-ONLY: sqlite is
opened mode=ro, and only SELECT-backed routes exist. This is the walking-skeleton server so
the VM has something LIVE; the full route/SDUI layer is a later port.

  python gemdesk_server.py --engine-db _core/gemdesk.db --domain-db xf.db --port 7433
  then open http://localhost:7433/
"""
import argparse, json, os, sqlite3, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ENGINE_DB = None
DOMAIN_DB = None
BOOT = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def _ro(path):
    if not path or not os.path.exists(path):
        return None
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)

def _rows(db, sql, args=()):
    db.row_factory = sqlite3.Row
    return [dict(r) for r in db.execute(sql, args).fetchall()]

def _has_table(db, name):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,)).fetchone())

# ---- route handlers (return python objects) ----
def r_health():
    out = {"ok": True, "boot": BOOT, "engine_db": ENGINE_DB, "domain_db": DOMAIN_DB, "engine": {}, "domain": {}}
    ed = _ro(ENGINE_DB)
    if ed:
        out["engine"] = {"facets": _rows(ed, "SELECT count(*) c FROM facet_registry")[0]["c"],
                         "ship_class_engine_seed": _rows(ed, "SELECT count(*) c FROM v_pk_row_ship_class_live WHERE ship_class='engine-seed'")[0]["c"],
                         "tables": _rows(ed, "SELECT count(*) c FROM sqlite_master WHERE type='table'")[0]["c"]}
        ed.close()
    dd = _ro(DOMAIN_DB)
    if dd:
        out["domain"] = {"files": _rows(dd, "SELECT count(*) c FROM xf_file")[0]["c"] if _has_table(dd, "xf_file") else 0,
                         "functions": _rows(dd, "SELECT count(*) c FROM v_xf_function_live")[0]["c"] if _has_table(dd, "v_xf_function_live") else 0}
        dd.close()
    return out

def r_facets():
    ed = _ro(ENGINE_DB)
    if not ed: return {"error": "no engine db"}
    o = _rows(ed, "SELECT tag_type, value_set, default_value, applies_to FROM facet_registry ORDER BY tag_type"); ed.close(); return o

def r_ship_class():
    ed = _ro(ENGINE_DB)
    if not ed: return {"error": "no engine db"}
    o = _rows(ed, "SELECT table_name, row_id, ship_class FROM v_pk_row_ship_class_live ORDER BY ship_class, table_name"); ed.close(); return o

def r_functions():
    dd = _ro(DOMAIN_DB)
    if not dd or not _has_table(dd, "v_xf_function_live"): return []
    o = _rows(dd, "SELECT name, source_lib, kind, arity, raw_hash, norm_hash FROM v_xf_function_live ORDER BY name, source_lib"); dd.close(); return o

def r_drift():
    dd = _ro(DOMAIN_DB)
    if not dd or not _has_table(dd, "v_xf_function_live"): return {"content_drift": [], "renames": []}
    cd = [r["name"] for r in _rows(dd, "SELECT name FROM v_xf_function_live GROUP BY name HAVING count(DISTINCT norm_hash)>1")]
    rn = [r["names"] for r in _rows(dd, "SELECT group_concat(DISTINCT name) names FROM v_xf_function_live GROUP BY norm_hash HAVING count(DISTINCT name)>1")]
    dd.close(); return {"content_drift": cd, "renames": rn}

def r_files():
    dd = _ro(DOMAIN_DB)
    if not dd or not _has_table(dd, "xf_file"): return []
    o = _rows(dd, "SELECT file_id, program, task, role, bytes, sha256 FROM xf_file ORDER BY file_id"); dd.close(); return o

def r_regenerate(qs):
    fid = (qs.get("id") or [None])[0]
    dd = _ro(DOMAIN_DB)
    if not dd or not fid: return {"error": "id required / no domain db"}
    rows = _rows(dd, "SELECT raw_text FROM xf_segment WHERE file_id=? ORDER BY seq", (fid,))
    dd.close()
    return {"file_id": fid, "text": "".join(r["raw_text"] for r in rows)}

def r_tasks():
    dd = _ro(DOMAIN_DB)
    if not dd or not _has_table(dd, "xf_task"): return []
    o = _rows(dd, "SELECT program, task, sheet, password_policy, pattern_tag FROM xf_task ORDER BY program, task"); dd.close(); return o

def r_patterns():
    dd = _ro(DOMAIN_DB)
    if not dd or not _has_table(dd, "xf_pattern"): return []
    o = _rows(dd, "SELECT tag, family, shape, assertion_fn FROM xf_pattern ORDER BY family, tag"); dd.close(); return o

ROUTES = {"/api/health": lambda qs: r_health(), "/api/facets": lambda qs: r_facets(),
          "/api/ship-class": lambda qs: r_ship_class(), "/api/functions": lambda qs: r_functions(),
          "/api/drift": lambda qs: r_drift(), "/api/files": lambda qs: r_files(),
          "/api/tasks": lambda qs: r_tasks(), "/api/patterns": lambda qs: r_patterns(),
          "/api/regenerate": r_regenerate}

DASH = """<!doctype html><html><head><meta charset=utf-8><title>GemDesk</title>
<style>body{background:#0e0f13;color:#d7dae0;font:14px/1.5 system-ui;margin:0;padding:24px}
h1{color:#8ab4f8;margin:0 0 4px}.sub{color:#7b8394;margin-bottom:20px}
.card{background:#171922;border:1px solid #242836;border-radius:10px;padding:14px 16px;margin:0 0 14px}
.k{color:#7b8394}.v{color:#e8eaed;font-weight:600}pre{white-space:pre-wrap;color:#a8b0c0;max-height:240px;overflow:auto}
.warn{color:#f0b429}.ok{color:#57d68d}</style></head><body>
<h1>GemDesk</h1><div class=sub>a desk... really a db... with facets and seams.</div>
<div class=card id=health>loading health...</div>
<div class=card><b>Facets</b> <pre id=facets></pre></div>
<div class=card><b>Functions + drift</b> <span id=drift></span><pre id=functions></pre></div>
<div class=card><b>Tasks</b> <pre id=tasks></pre></div>
<div class=card><b>Scoring patterns</b> <pre id=patterns></pre></div>
<div class=card><b>Files (byte-faithful)</b> <pre id=files></pre></div>
<script>
const g=(u)=>fetch(u).then(r=>r.json());
g('/api/health').then(h=>{document.getElementById('health').innerHTML=
 `<b class=ok>HEALTHY</b> &nbsp; boot ${h.boot} &nbsp; engine facets=${h.engine.facets||0} engine-seed=${h.engine.ship_class_engine_seed||0} &nbsp; domain files=${h.domain.files||0} functions=${h.domain.functions||0}`;});
g('/api/facets').then(f=>document.getElementById('facets').textContent=f.map(x=>`${x.tag_type}: ${x.value_set}`).join('\\n'));
g('/api/functions').then(f=>document.getElementById('functions').textContent=f.map(x=>`${x.name} [${x.source_lib}] ${x.raw_hash}`).join('\\n')||'(none)');
g('/api/drift').then(d=>document.getElementById('drift').innerHTML=(d.content_drift.length?`<span class=warn>content drift: ${d.content_drift.join(', ')}</span>`:'<span class=ok>no drift</span>'));
g('/api/files').then(f=>document.getElementById('files').textContent=f.map(x=>`${x.file_id}  ${x.bytes}B  ${x.sha256.slice(0,12)}`).join('\\n')||'(none)');
g('/api/tasks').then(t=>document.getElementById('tasks').textContent=t.map(x=>`${x.program} ${x.task}  ->  ${x.sheet||''}  [${x.pattern_tag||''}]`).join('\\n')||'(none)');
g('/api/patterns').then(p=>document.getElementById('patterns').textContent=p.map(x=>`${x.family||''}/${x.shape||''}  ${x.tag}  -> ${x.assertion_fn||''}`).join('\\n')||'(none)');
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        u = urlparse(self.path); qs = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            body = DASH.encode(); ctype = "text/html; charset=utf-8"
        elif u.path in ROUTES:
            try: body = json.dumps(ROUTES[u.path](qs), ensure_ascii=False).encode()
            except Exception as e: body = json.dumps({"error": repr(e)}).encode()
            ctype = "application/json; charset=utf-8"
        else:
            self.send_response(404); self.end_headers(); self.wfile.write(b'{"error":"not found"}'); return
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

def main():
    global ENGINE_DB, DOMAIN_DB
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine-db", default="_core/gemdesk.db")
    ap.add_argument("--domain-db", default="xf.db")
    ap.add_argument("--port", type=int, default=7433)
    a = ap.parse_args()
    ENGINE_DB = a.engine_db if os.path.exists(a.engine_db) else None
    DOMAIN_DB = a.domain_db if os.path.exists(a.domain_db) else None
    print(f"GemDesk server on http://localhost:{a.port}/  engine={ENGINE_DB} domain={DOMAIN_DB}")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()

if __name__ == "__main__":
    main()
