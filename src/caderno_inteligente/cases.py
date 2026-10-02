from __future__ import annotations
import sqlite3
from datetime import datetime,timezone
STATUSES=('novo','em_investigacao','aguardando_comercial','aguardando_producao','concluido')
def now():return datetime.now(timezone.utc).isoformat()
def init_cases_db(path):
 with sqlite3.connect(path) as c:
  c.execute('CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, sku TEXT NOT NULL, run_id INTEGER, status TEXT NOT NULL, owner TEXT, due_date TEXT, action TEXT, note TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS case_history (id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL, status TEXT NOT NULL, owner TEXT, due_date TEXT, action TEXT, note TEXT, changed_at TEXT NOT NULL)')
def create_case(path,sku,run_id=None,status='novo',owner='',due_date='',action='',note=''):
 if status not in STATUSES:raise ValueError('Status inválido')
 init_cases_db(path);t=now()
 with sqlite3.connect(path) as c:
  c.execute('INSERT INTO cases(sku,run_id,status,owner,due_date,action,note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(sku,run_id,status,owner,due_date,action,note,t,t));i=c.execute('SELECT last_insert_rowid()').fetchone()[0];c.execute('INSERT INTO case_history(case_id,status,owner,due_date,action,note,changed_at) VALUES(?,?,?,?,?,?,?)',(i,status,owner,due_date,action,note,t));return i
def list_cases(path):
 init_cases_db(path)
 with sqlite3.connect(path) as c:return [dict(zip(['id','sku','run_id','status','owner','due_date','action','note','created_at','updated_at'],r)) for r in c.execute('SELECT id,sku,run_id,status,owner,due_date,action,note,created_at,updated_at FROM cases ORDER BY updated_at DESC')]
def update_case(path,case_id,**v):
 if v.get('status') not in STATUSES:raise ValueError('Status inválido')
 init_cases_db(path);t=now()
 with sqlite3.connect(path) as c:
  c.execute('UPDATE cases SET status=?,owner=?,due_date=?,action=?,note=?,updated_at=? WHERE id=?',(v['status'],v.get('owner',''),v.get('due_date',''),v.get('action',''),v.get('note',''),t,case_id));c.execute('INSERT INTO case_history(case_id,status,owner,due_date,action,note,changed_at) VALUES(?,?,?,?,?,?,?)',(case_id,v['status'],v.get('owner',''),v.get('due_date',''),v.get('action',''),v.get('note',''),t))
def history(path,case_id):
 init_cases_db(path)
 with sqlite3.connect(path) as c:return [dict(zip(['status','owner','due_date','action','note','changed_at'],r)) for r in c.execute('SELECT status,owner,due_date,action,note,changed_at FROM case_history WHERE case_id=? ORDER BY id DESC',(case_id,))]
