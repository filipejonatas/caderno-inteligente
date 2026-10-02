import pytest
from fastapi.testclient import TestClient
from backend.main import _partner_level, app

def test_scenario_is_explicit_and_does_not_change_official_config():
 c=TestClient(app); r=c.post('/api/scenarios',json={'weights':{'EXCESS_COVERAGE':99}}).json()
 assert r['is_simulation'] and r['weights']['EXCESS_COVERAGE']==99
 assert c.get('/api/config').json()['weights']['EXCESS_COVERAGE']==3

def test_b2b_visibility_has_partner_coverage():
 c=TestClient(app); r=c.get('/api/b2b2c/visibility').json()
 assert len(r['partners'])==5 and all(x['coverage']==.2 for x in r['partners'])
 assert all(x['level']=='Essencial' and x['next_level']=='Conectado' for x in r['partners'])
 assert all(x['next_level_required_skus']==10 for x in r['partners'])
 assert 'Não representa acordo comercial firmado' in r['classification_disclaimer']

@pytest.mark.parametrize(('coverage','expected'),[(0,'Sem visibilidade'),(.2,'Essencial'),(.4,'Conectado'),(.8,'Estratégico')])
def test_b2b_level_boundaries(coverage,expected):
 assert _partner_level(coverage)==expected
