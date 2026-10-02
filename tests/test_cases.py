from caderno_inteligente.cases import create_case,list_cases,update_case,history

def test_case_workflow_keeps_history(tmp_path):
 db=tmp_path/'cases.db'; i=create_case(db,'CI-0001',owner='Mauro')
 update_case(db,i,status='em_investigacao',owner='PCP',due_date='2026-10-01',action='validar OP',note='prioridade revisada')
 assert list_cases(db)[0]['status']=='em_investigacao'
 assert len(history(db,i))==2
