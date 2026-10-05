from __future__ import annotations
import hashlib,json,sqlite3
from datetime import datetime,timezone
from pathlib import Path

def init_runs_db(path):
 with sqlite3.connect(path) as c:
  c.execute('CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, source_hash TEXT NOT NULL, weights TEXT NOT NULL, thresholds TEXT NOT NULL, quality TEXT NOT NULL, ranking TEXT NOT NULL)')
  # Additive migration: legacy snapshots keep comparison = NULL.
  if 'comparison' not in {r[1] for r in c.execute('PRAGMA table_info(runs)')}:
   c.execute('ALTER TABLE runs ADD COLUMN comparison TEXT')
def create_run(path,source,weights,thresholds,quality,ranking,comparison=None):
 init_runs_db(path); h=hashlib.sha256(Path(source).read_bytes()).hexdigest(); now=datetime.now(timezone.utc).isoformat()
 with sqlite3.connect(path) as c:
  c.execute('INSERT INTO runs(created_at,source_hash,weights,thresholds,quality,ranking,comparison) VALUES(?,?,?,?,?,?,?)',(now,h,json.dumps(weights),json.dumps(thresholds),json.dumps(quality,default=str),json.dumps(ranking,default=str),None if comparison is None else json.dumps(comparison,default=str)))
  return c.execute('SELECT last_insert_rowid()').fetchone()[0]
def list_runs(path):
 init_runs_db(path)
 with sqlite3.connect(path) as c:return [{'id':r[0],'created_at':r[1],'source_hash':r[2],'prioritized_skus':len(json.loads(r[3])),'comparison_schema_version':None if r[4] is None else json.loads(r[4]).get('schema_version')} for r in c.execute('SELECT id,created_at,source_hash,ranking,comparison FROM runs ORDER BY id DESC')]
def get_run(path,run_id):
 init_runs_db(path)
 with sqlite3.connect(path) as c:
  r=c.execute('SELECT id,created_at,source_hash,weights,thresholds,quality,ranking,comparison FROM runs WHERE id=?',(run_id,)).fetchone()
 if not r:return None
 return {'id':r[0],'created_at':r[1],'source_hash':r[2],'weights':json.loads(r[3]),'thresholds':json.loads(r[4]),'quality':json.loads(r[5]),'ranking':json.loads(r[6]),'comparison':None if r[7] is None else json.loads(r[7])}
