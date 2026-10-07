from fastapi.testclient import TestClient
from backend.main import app

def test_detail_exposes_score_contributions_and_limitations():
 c=TestClient(app); data=c.get('/api/priorities/CI-0002').json()
 assert data['score_contributions'] and 'limitation' in data
 required={'current_stock','backlog_order_quantity','production_order_quantity','projected_stock_quantity','operational_gap_quantity','first_promised_date','first_production_completion','sell_in_quantity','sell_out_quantity','sell_in_minus_sell_out_quantity','sell_out_partner_count','forecast_quantity','missing_data'}
 assert required.issubset(data['indicator'])
 assert 'capacidade' in data['limitation'].lower() and 'individual' in data['limitation'].lower()
 assert {'forecast','operational_recommendation'}.issubset(data)
 forecast=data['forecast']; recommendation=data['operational_recommendation']
 assert forecast['status']=='ok' and len(forecast['forecast_values'])==forecast['horizon_months']==6
 assert forecast['forecast_total_3m']==round(sum(forecast['forecast_values'][:3]),1)
 assert {'model','backtest_wape','forecast_confidence','limitation'}.issubset(forecast)
 assert {'suggested_quantity','calculation','limitations','requires_human_review'}.issubset(recommendation)
 assert recommendation['requires_human_review'] is True

def test_priority_api_exposes_operational_context_with_json_nulls():
 c=TestClient(app); priorities=c.get('/api/priorities').json()
 required={'critical_date','critical_date_reason','operational_gap_quantity','projected_stock_quantity','first_promised_date','first_production_completion','sell_in_quantity','sell_out_quantity','sell_in_minus_sell_out_quantity','forecast_quantity','analysis_scope','missing_data'}
 assert priorities and required.issubset(priorities[0])
 assert all(item['analysis_scope']=='SKU global' for item in priorities)
 assert all(item['operational_gap_quantity']>=0 for item in priorities)
 missing=next(item for item in priorities if 'sell_out_quantity' in item['missing_data'])
 assert missing['sell_out_quantity'] is None

def test_capacity_timeline_is_available_by_family():
 c=TestClient(app); data=c.get('/api/capacity/Escolar').json()
 assert data['weeks'] and 'Ocupação' in data['weeks'][0]
