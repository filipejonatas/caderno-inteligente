from caderno_inteligente.runs import create_run,list_runs,get_run

def test_persists_auditable_snapshot(tmp_path):
 source=tmp_path/'source.xlsm';source.write_bytes(b'base')
 db=tmp_path/'runs.db';rid=create_run(db,source,{'A':1},{'x':2},{'errors':[]},[{'sku':'CI-1'}])
 assert list_runs(db)[0]['id']==rid
 assert get_run(db,rid)['ranking'][0]['sku']=='CI-1'

def test_active_source_hash_is_stored_when_given(tmp_path):
 source=tmp_path/'source.xlsm';source.write_bytes(b'base')
 db=tmp_path/'runs.db';rid=create_run(db,source,{},{},{},[],source_hash='abc')
 assert get_run(db,rid)['source_hash']=='abc' and list_runs(db)[0]['source_hash']=='abc'
