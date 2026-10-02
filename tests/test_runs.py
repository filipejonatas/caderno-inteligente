from caderno_inteligente.runs import create_run,list_runs,get_run

def test_persists_auditable_snapshot(tmp_path):
 source=tmp_path/'source.xlsm';source.write_bytes(b'base')
 db=tmp_path/'runs.db';rid=create_run(db,source,{'A':1},{'x':2},{'errors':[]},[{'sku':'CI-1'}])
 assert list_runs(db)[0]['id']==rid
 assert get_run(db,rid)['ranking'][0]['sku']=='CI-1'
