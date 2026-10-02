import sqlite3

from fastapi.testclient import TestClient

import backend.main as api_module
from caderno_inteligente.feedback import (
    feedback_summary,
    init_feedback_db,
    list_feedback,
    save_feedback,
)

def test_saves_feedback_separately(tmp_path):
 db=tmp_path/'feedback.db'; save_feedback(db,'CI-0001','aceita','ok','PCP'); rows=list_feedback(db)
 assert rows[0][0:4] == ('CI-0001','aceita','ok','PCP')
 assert rows[0][4:6] == ('nao_utilizado',None)

def test_migration_preserves_existing_feedback(tmp_path):
 db=tmp_path/'feedback.db'
 with sqlite3.connect(db) as conn:
  conn.execute('CREATE TABLE feedback (id INTEGER PRIMARY KEY, sku TEXT NOT NULL, action TEXT NOT NULL, note TEXT, user_name TEXT, created_at TEXT NOT NULL)')
  conn.execute("INSERT INTO feedback(sku,action,note,user_name,created_at) VALUES('CI-0002','alterada','registro antigo','PCP','2026-09-01T10:00:00+00:00')")
 init_feedback_db(db)
 with sqlite3.connect(db) as conn:
  columns={row[1] for row in conn.execute('PRAGMA table_info(feedback)')}
 assert {'partner_data_effect','analysis_minutes'}.issubset(columns)
 row=list_feedback(db)[0]
 assert row == ('CI-0002','alterada','registro antigo','PCP','nao_utilizado',None,'2026-09-01T10:00:00+00:00')

def test_persists_partner_data_effect_and_analysis_minutes(tmp_path):
 db=tmp_path/'feedback.db'
 save_feedback(db,'CI-0003','aceita','validado','Ana','aumentou_confianca',18)
 row=list_feedback(db)[0]
 assert row[4:6] == ('aumentou_confianca',18)
 assert feedback_summary(db) == {'decision_count':1,'partner_data_influenced_decision_count':1}

def test_feedback_api_persists_and_returns_new_fields(tmp_path,monkeypatch):
 db=tmp_path/'feedback.db'; monkeypatch.setattr(api_module,'FEEDBACK_DB',db)
 client=TestClient(api_module.app)
 response=client.post('/api/feedback',json={'sku':'CI-0004','action':'alterada','note':'canal confirmou','user_name':'Jo','partner_data_effect':'alterou_decisao','analysis_minutes':12})
 assert response.status_code==200
 payload=client.get('/api/feedback').json()
 assert payload[0]['partner_data_effect']=='alterou_decisao'
 assert payload[0]['analysis_minutes']==12
 summary=client.get('/api/overview').json()
 assert summary['decision_count']==1
 assert summary['partner_data_influenced_decision_count']==1
