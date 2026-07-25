#!/usr/bin/env python3
"""
gemdesk_server.py -- minimal, dependency-free GemDesk read server (Python stdlib only).

Serves the engine DB (facets, ship-class, checks) and, if present, a domain DB (XF files,
functions, drift) over small JSON routes, plus a one-page dashboard. READ-ONLY: sqlite is
opened mode=ro, and only SELECT-backed routes exist. This is the walking-skeleton server so
the VM has something LIVE; the full route/SDUI layer is a later port.

  python gemdesk_server.py --engine-db _core/gemdesk.db --domain-db xf.db --port 8770
  then open http://localhost:8770/
"""
import argparse, json, os, sqlite3, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import base64, importlib.util, json as _json, re, threading, xml.etree.ElementTree as ET, zipfile, io

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

def r_collections():
    dd = _ro(DOMAIN_DB)
    if not dd or not _has_table(dd, "xf_collection"): return []
    o = _rows(dd, "SELECT collection_id, era, app, category, version, scoring_path, status, updated FROM xf_collection ORDER BY collection_id"); dd.close(); return o

def r_runs():
    dd = _ro(DOMAIN_DB)
    if not dd or not _has_table(dd, "xf_collection_run"): return []
    o = _rows(dd, "SELECT collection_id, ran_at, files, tasks, functions, drift_count FROM xf_collection_run ORDER BY run_id DESC LIMIT 100"); dd.close(); return o

# ===================== ABSTRACTION RECOGNITION =====================
# "I am looking at this snippet -- does it fit a NAMED abstraction?"
# The engine answers with EVIDENCE, not opinion: normalise the snippet to its structural
# shape, then count how often that exact shape occurs across the whole corpus. Unique
# means bespoke; frequent means it IS an idiom and deserves a name.
#
# Everything here is LANGUAGE knowledge (VB/VBScript), never TENANT knowledge, so it is
# legitimately public. Domain patterns live in the PRIVATE pack and are injected via
# --patterns (ADR boundary: the public engine stays content-agnostic).
DOMAIN_PATTERNS = None          # set by main() from --patterns
_SHAPE_INDEX = None             # lazily built {shape: count}
_SHAPE_LOCK = threading.Lock()

_STR = re.compile(r'"[^"]*"')
_NUM = re.compile(r'\b\d+(\.\d+)?\b')
_IDN = re.compile(r'\b[A-Za-z_]\w*\b')
_KW = {'if','then','else','elseif','end','for','each','next','do','loop','while','wend','select',
       'case','sub','function','dim','set','let','and','or','not','is','nothing','true','false',
       'to','step','exit','call','with','on','error','resume','goto','as','byval','byref',
       'optional','const','public','private','redim','preserve','in','mod'}

def shape_of(line):
    t = _STR.sub('S', line)
    t = _NUM.sub('N', t)
    t = _IDN.sub(lambda m: m.group(0) if m.group(0).lower() in _KW else 'I', t)
    return re.sub(r'\s+', ' ', t).strip()

def _segments(name):
    out = []
    for p in re.split(r'[_\W]+', name):
        out += [t for t in re.findall(r'[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+', p) if t]
    return [t.lower() for t in out]

def shape_index():
    """Build once per process: every code line in the corpus -> its shape -> count.
    Rebuild = restart the server, which every ingest already does."""
    global _SHAPE_INDEX
    with _SHAPE_LOCK:
        if _SHAPE_INDEX is not None:
            return _SHAPE_INDEX
        idx = {}
        db = _ro(DOMAIN_DB)
        if db:
            for (txt,) in db.execute("SELECT raw_text FROM xf_segment"):
                c = (txt or '').strip()
                if c and not c.startswith("'"):
                    sh = shape_of(c)
                    idx[sh] = idx.get(sh, 0) + 1
        _SHAPE_INDEX = idx
        return idx

def r_analyze(payload):
    """POST {text, role} -> per-line shape + corpus frequency + verdict + domain hits."""
    text = payload.get('text') or ''
    role = payload.get('role') or 'scoring'
    idx = shape_index()
    corpus_lines = sum(idx.values()) or 1
    seen, lines = {}, []
    for i, raw in enumerate(text.splitlines(), 1):
        code = raw.strip()
        if not code or code.startswith("'"):
            continue
        sh = shape_of(code)
        n = idx.get(sh, 0)
        seen[sh] = seen.get(sh, 0) + 1
        lines.append({'line': i, 'shape': sh, 'corpus_count': n,
                      'verdict': 'idiom' if n >= 25 else 'common' if n >= 5
                                 else 'rare' if n > 0 else 'unique'})
    idents = {}
    for nm in set(_IDN.findall(text)):
        if nm.lower() in _KW or len(nm) < 3:
            continue
        for seg in _segments(nm):
            idents[seg] = idents.get(seg, 0) + 1
    hits = []
    if DOMAIN_PATTERNS is not None:
        try:
            hits = DOMAIN_PATTERNS.scan_text(text, role)
        except Exception as e:
            hits = [{'pattern': '(engine)', 'line': 0, 'note': f'domain pattern error: {e!r}'}]
    covered = {h.get('line') for h in hits}
    return {
        'role': role,
        'corpus_lines_indexed': corpus_lines,
        'domain_patterns_loaded': DOMAIN_PATTERNS is not None,
        'lines': lines,
        'distinct_shapes': len(seen),
        'unnamed_idioms': sorted(
            [{'shape': sh, 'in_snippet': c, 'in_corpus': idx.get(sh, 0)}
             for sh, c in seen.items() if idx.get(sh, 0) >= 25 and not covered],
            key=lambda d: -d['in_corpus'])[:25],
        'identifier_segments': sorted(
            [{'seg': k, 'n': v} for k, v in idents.items()], key=lambda d: -d['n'])[:30],
        'pattern_hits': hits,
    }

# ===================== EXEMPLARS =====================
# A narrative case that justifies a pattern: starter -> steps -> completed + WHY.
# Written to a SEPARATE db (--exemplar-db). The corpus DBs stay strictly read-only:
# read-only over INGESTED truth, writable only over AUTHORED content. That distinction
# is the invariant, not "the server never writes".
EXEMPLAR_DB = None

def _ex_db():
    if not EXEMPLAR_DB:
        return None
    db = sqlite3.connect(EXEMPLAR_DB)
    db.row_factory = sqlite3.Row
    return db

OOXML_TEXT = {  # zip member globs -> the XML tag whose text we want, per format
    'word/document.xml':  '}t',
    'ppt/slides/':        '}t',
    'xl/sharedStrings.xml': '}t',
}

def extract_ooxml_text(data: bytes, filename: str = ''):
    """docx / xlsx / pptx are zip+XML. Pull readable text with STDLIB ONLY -- no
    python-docx, no openpyxl, nothing to install. Keeps the dependency-free constraint."""
    out = []
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except Exception as e:
        return f'(not an OOXML package: {e})'
    for nm in z.namelist():
        if not (nm.endswith('.xml') and (
                nm == 'word/document.xml' or nm.startswith('ppt/slides/slide')
                or nm == 'xl/sharedStrings.xml' or nm.startswith('xl/worksheets/sheet'))):
            continue
        try:
            root = ET.fromstring(z.read(nm))
        except Exception:
            continue
        chunk = [(el.text or '') for el in root.iter() if el.tag.endswith('}t') and el.text]
        if chunk:
            out.append(f'--- {nm} ---\n' + '\n'.join(chunk))
    return '\n\n'.join(out) or '(no extractable text)'

def r_exemplars():
    db = _ex_db()
    if not db: return []
    return [dict(r) for r in db.execute("SELECT * FROM v_xf_exemplar_summary ORDER BY updated DESC")]

def r_exemplar(qs):
    db = _ex_db()
    if not db: return {'error': 'no exemplar db'}
    eid = (qs.get('id') or [''])[0]
    e = db.execute("SELECT * FROM xf_exemplar WHERE exemplar_id=?", (eid,)).fetchone()
    if not e: return {'error': 'not found'}
    parts = db.execute("SELECT part_id,seq,kind,caption,mime,filename,text,sha256,bytes,created "
                       "FROM xf_exemplar_part WHERE exemplar_id=? ORDER BY seq", (eid,)).fetchall()
    return {'exemplar': dict(e), 'parts': [dict(p) for p in parts]}

def r_exemplar_save(payload):
    db = _ex_db()
    if not db: return {'error': 'no exemplar db -- start the server with --exemplar-db'}
    eid = (payload.get('exemplar_id') or re.sub(r'[^a-z0-9]+', '-',
           (payload.get('name') or '').lower()).strip('-'))
    if not eid: return {'error': 'name required'}
    now = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    db.execute("INSERT INTO xf_exemplar(exemplar_id,name,pattern_name,program,task,app,era,"
               "question,why,status,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) "
               "ON CONFLICT(exemplar_id) DO UPDATE SET name=excluded.name,"
               "pattern_name=excluded.pattern_name,program=excluded.program,task=excluded.task,"
               "app=excluded.app,era=excluded.era,question=excluded.question,why=excluded.why,"
               "status=excluded.status,updated=excluded.updated",
               (eid, payload.get('name') or eid, payload.get('pattern_name'), payload.get('program'),
                payload.get('task'), payload.get('app'), payload.get('era'), payload.get('question'),
                payload.get('why'), payload.get('status') or 'draft', now, now))
    db.commit()
    return {'ok': True, 'exemplar_id': eid}

def r_exemplar_part(payload):
    db = _ex_db()
    if not db: return {'error': 'no exemplar db'}
    eid = payload.get('exemplar_id')
    if not eid: return {'error': 'exemplar_id required'}
    blob = None; text = payload.get('text') or ''
    b64 = payload.get('data_b64')
    if b64:
        if ',' in b64[:64] and b64[:5] == 'data:':
            b64 = b64.split(',', 1)[1]
        blob = base64.b64decode(b64)
        fn = (payload.get('filename') or '')
        if fn.lower().endswith(('.docx', '.xlsx', '.pptx', '.dotx', '.potx', '.xltx')):
            text = extract_ooxml_text(blob, fn)
    seq = payload.get('seq')
    if seq is None:
        seq = (db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM xf_exemplar_part WHERE exemplar_id=?",
                          (eid,)).fetchone()[0])
    payload_bytes = blob if blob is not None else text.encode('utf-8')
    db.execute("INSERT INTO xf_exemplar_part(exemplar_id,seq,kind,caption,mime,filename,text,blob,"
               "sha256,bytes,created) VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'))",
               (eid, seq, payload.get('kind') or 'note', payload.get('caption'),
                payload.get('mime'), payload.get('filename'), text, blob,
                hashlib_sha(payload_bytes), len(payload_bytes)))
    db.execute("UPDATE xf_exemplar SET updated=datetime('now') WHERE exemplar_id=?", (eid,))
    db.commit()
    return {'ok': True, 'seq': seq, 'extracted_chars': len(text)}

def r_exemplar_purge(payload):
    db = _ex_db()
    if not db: return {'error': 'no exemplar db'}
    eid = payload.get('exemplar_id')
    pid = payload.get('part_id')
    if pid:
        db.execute("DELETE FROM xf_exemplar_part WHERE part_id=?", (pid,)); db.commit()
        return {'ok': True, 'deleted_part': pid}
    if not eid: return {'error': 'exemplar_id or part_id required'}
    db.execute("DELETE FROM xf_exemplar_part WHERE exemplar_id=?", (eid,))
    db.execute("DELETE FROM xf_exemplar WHERE exemplar_id=?", (eid,))
    db.commit()
    return {'ok': True, 'purged': eid}

def hashlib_sha(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()

def r_candidates_list():
    path = _cand_path()
    if not path or not os.path.exists(path):
        return []
    out = []
    with open(path, encoding='utf-8') as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                try: out.append(_json.loads(ln))
                except Exception: pass
    return out[::-1]

def _cand_path():
    """Append-only sidecar beside the domain DB. The server stays READ-ONLY against
    SQLite by design (ANN20260724-022); naming a candidate must not break that."""
    return (os.path.splitext(DOMAIN_DB)[0] + '-pattern-candidates.jsonl') if DOMAIN_DB else None

def r_candidate_save(payload):
    path = _cand_path()
    if not path:
        return {'error': 'no domain db'}
    rec = {'name': (payload.get('name') or '').strip(),
           'role': payload.get('role') or 'scoring',
           'shape': payload.get('shape') or '',
           'note': payload.get('note') or '',
           'sample': (payload.get('sample') or '')[:4000],
           'saved': __import__('datetime').datetime.now().isoformat(timespec='seconds')}
    if not rec['name']:
        return {'error': 'name required'}
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(_json.dumps(rec, ensure_ascii=False) + '\n')
    return {'ok': True, 'saved': rec['name'], 'file': path}

ROUTES = {"/api/health": lambda qs: r_health(),
          "/api/pattern-candidates": lambda qs: r_candidates_list(),
          "/api/exemplars": lambda qs: r_exemplars(),
          "/api/exemplar": lambda qs: r_exemplar(qs), "/api/facets": lambda qs: r_facets(),
          "/api/ship-class": lambda qs: r_ship_class(), "/api/functions": lambda qs: r_functions(),
          "/api/drift": lambda qs: r_drift(), "/api/files": lambda qs: r_files(),
          "/api/tasks": lambda qs: r_tasks(), "/api/patterns": lambda qs: r_patterns(),
          "/api/collections": lambda qs: r_collections(), "/api/runs": lambda qs: r_runs(),
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
    def _send(self, body, ctype="application/json; charset=utf-8", code=200):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get('Content-Length') or 0)
            payload = json.loads(self.rfile.read(n) or b'{}')
        except Exception as e:
            self._send(json.dumps({'error': f'bad json: {e}'}).encode(), code=400); return
        try:
            if u.path == '/api/analyze':
                body = json.dumps(r_analyze(payload), ensure_ascii=False).encode()
            elif u.path == '/api/pattern-candidates':
                body = json.dumps(r_candidate_save(payload), ensure_ascii=False).encode()
            elif u.path == '/api/exemplar':
                body = json.dumps(r_exemplar_save(payload), ensure_ascii=False).encode()
            elif u.path == '/api/exemplar/part':
                body = json.dumps(r_exemplar_part(payload), ensure_ascii=False).encode()
            elif u.path == '/api/exemplar/purge':
                body = json.dumps(r_exemplar_purge(payload), ensure_ascii=False).encode()
            else:
                self._send(b'{"error":"not found"}', code=404); return
        except Exception as e:
            body = json.dumps({'error': repr(e)}).encode()
        self._send(body)

    def do_GET(self):
        u = urlparse(self.path); qs = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            uihtml = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemdesk-ui.html")
            body = open(uihtml, "rb").read() if os.path.exists(uihtml) else DASH.encode()
            ctype = "text/html; charset=utf-8"
        elif u.path == '/api/exemplar/blob':
            db = _ex_db(); pid = (qs.get('part_id') or ['0'])[0]
            row = db.execute("SELECT blob,mime FROM xf_exemplar_part WHERE part_id=?", (pid,)).fetchone() if db else None
            if not row or row['blob'] is None:
                self.send_response(404); self.end_headers(); self.wfile.write(b'no blob'); return
            self._send(row['blob'], row['mime'] or 'application/octet-stream'); return
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
    ap.add_argument("--port", type=int, default=8770)  # 7433 is RESERVED (async port)
    ap.add_argument("--exemplar-db", help="WRITABLE store for authored exemplars. VM-only, "
                                          "gitignored. Corpus DBs stay read-only.")
    ap.add_argument("--exemplar-schema", help="schema applied if the exemplar db is new")
    ap.add_argument("--patterns", help="path to the PRIVATE domain pattern module "
                                       "(e.g. parsers/xf_patterns.py). Engine works without it.")
    a = ap.parse_args()
    global DOMAIN_PATTERNS, EXEMPLAR_DB
    if a.exemplar_db:
        EXEMPLAR_DB = a.exemplar_db
        _d = sqlite3.connect(EXEMPLAR_DB)
        if not _d.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='xf_exemplar'").fetchone():
            if a.exemplar_schema and os.path.exists(a.exemplar_schema):
                _d.executescript(open(a.exemplar_schema, encoding="utf-8").read()); _d.commit()
        _d.close()
    if a.patterns and os.path.exists(a.patterns):
        spec = importlib.util.spec_from_file_location("xf_patterns_domain", a.patterns)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        DOMAIN_PATTERNS = mod
    ENGINE_DB = a.engine_db if os.path.exists(a.engine_db) else None
    DOMAIN_DB = a.domain_db if os.path.exists(a.domain_db) else None
    print(f"GemDesk server on http://localhost:{a.port}/  engine={ENGINE_DB} domain={DOMAIN_DB} "
          f"patterns={'loaded' if DOMAIN_PATTERNS else 'none'} exemplars={EXEMPLAR_DB or 'off'}")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()

if __name__ == "__main__":
    main()
