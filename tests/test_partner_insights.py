import copy

import pandas as pd
import pytest

from caderno_inteligente.partner_insights import build_partner_insights, load_commercial_thresholds


def source(sales=60, stock=30, sent=65):
    months = pd.date_range('2026-06-01', periods=3, freq='MS')
    return {
        'Produtos': pd.DataFrame([{'SKU': 'S1', 'Produto': 'Teste'}, {'SKU': 'S2', 'Produto': 'Outro'}]),
        'Parceiros_Canais': pd.DataFrame([{'Código': p, 'Nome fictício': p, 'Tipo': 'Varejo', 'Região': 'Sul', 'Canal principal': 'Loja'} for p in ['P1', 'P2']]),
        'Sell_In': pd.DataFrame([{'Cliente': 'P1', 'SKU': 'S1', 'Mês': m, 'Quantidade enviada': sent} for m in months]),
        'Sell_Out': pd.DataFrame([{'Cliente': 'P1', 'SKU': 'S1', 'Mês': m, 'Quantidade vendida': sales, 'Estoque estimado cliente': stock, 'Natureza do dado': 'Observado pelo parceiro'} for m in months]),
        'Carteira_Pedidos': pd.DataFrame([{'Pedido': 'PED1', 'SKU': 'S2', 'Cliente/Canal': 'P2', 'Quantidade': 40, 'Data prometida': pd.Timestamp('2026-09-10'), 'Status': 'Confirmado'}]),
        'Estoque_Atual': pd.DataFrame([{'SKU': 'S1', 'Estoque atual': 99999}]),
    }


def first(data, thresholds=None):
    return next(row for row in build_partner_insights(data, thresholds)['items'] if row['partner'] == 'P1')


def test_real_keys_only_no_cartesian_or_global_stock_and_source_immutable():
    data = source()
    before = copy.deepcopy(data)
    result = build_partner_insights(data)
    assert {(r['partner'], r['sku']) for r in result['items']} == {('P1', 'S1'), ('P2', 'S2')}
    assert sum(len(r['periods']) for r in result['items']) == 3
    assert first(data)['estimated_stock'] == 30
    assert first(data)['coverage_days'] == 15
    for key in data:
        pd.testing.assert_frame_equal(data[key], before[key])


def test_safe_reposition_requires_recent_observed_sales_and_estimated_stock():
    assert first(source())['action'] == 'avaliar_reposicao'
    no_stock = source()
    no_stock['Sell_Out']['Estoque estimado cliente'] = None
    assert first(no_stock)['action'] == 'dados_insuficientes'
    assert first(source(sales=0))['action'] != 'avaliar_reposicao'
    assert first(source(sales=0))['coverage_days'] is None


def test_missing_is_null_but_observed_zero_is_zero():
    result = build_partner_insights(source(sales=0))
    assert result['items'][0]['sell_out_recent'] == 0
    order_only = result['items'][1]
    assert order_only['sell_out_recent'] is None
    assert order_only['sell_in_recent'] is None
    assert order_only['estimated_stock'] is None
    assert order_only['periods'] == []
    assert order_only['backlog_quantity'] == 40
    assert order_only['action'] == 'dados_insuficientes'


def test_comparison_uses_intersection_not_unmatched_months():
    data = source()
    data['Sell_In'] = data['Sell_In'].iloc[1:].copy()
    row = first(data)
    assert row['comparable_months'] == ['2026-07', '2026-08']
    assert row['comparable_sell_in'] == 130
    assert row['comparable_sell_out'] == 120
    assert row['comparable_difference'] == 10
    assert row['sell_out_recent'] == 180
    assert not any(s['code'] == 'SELLIN_SELLOUT_DIVERGENCE' for s in row['signals'])


def test_gap_and_stale_data_suppress_reposition():
    data = source()
    data['Sell_Out'] = data['Sell_Out'].drop(index=1)
    row = first(data)
    assert row['missing_months'] == ['2026-07']
    assert row['action'] == 'solicitar_atualizacao'
    assert row['data_quality'] == 'stale'
    assert not any(s['code'] == 'REPOSITION_OPPORTUNITY' for s in row['signals'])
    data['Sell_Out']['Mês'] = data['Sell_Out']['Mês'] - pd.DateOffset(months=4)
    assert first(data)['age_months'] == 4


def test_excess_signal_for_low_or_zero_turnover():
    for sales in [0, 20]:
        row = first(source(sales=sales, stock=300, sent=sales))
        assert any(s['code'] == 'PARTNER_EXCESS_RISK' for s in row['signals'])
        assert row['action'] == 'monitorar_estoque'


def test_divergence_has_precedence_and_thresholds_are_configurable():
    row = first(source(sent=200))
    assert row['action'] == 'investigar_divergencia'
    assert first(source(), {'reposition_coverage_days': 10})['action'] == 'monitorar_estoque'


@pytest.mark.parametrize('kind', ['duplicate', 'orphan', 'negative', 'infinite', 'duplicate_order'])
def test_invalid_source_stops_commercial_analysis(kind):
    data = source()
    if kind == 'duplicate': data['Sell_Out'] = pd.concat([data['Sell_Out'], data['Sell_Out'].iloc[:1]])
    if kind == 'orphan': data['Carteira_Pedidos'].loc[0, 'Cliente/Canal'] = 'unknown'
    if kind == 'negative': data['Sell_Out'].loc[0, 'Estoque estimado cliente'] = -1
    if kind == 'infinite': data['Sell_In'] = data['Sell_In'].astype({'Quantidade enviada': float}); data['Sell_In'].loc[0, 'Quantidade enviada'] = float('inf')
    if kind == 'duplicate_order': data['Carteira_Pedidos'] = pd.concat([data['Carteira_Pedidos']] * 2)
    with pytest.raises(ValueError): build_partner_insights(data)


@pytest.mark.parametrize('thresholds', [{'recent_months': 0}, {'divergence_ratio': -1}, {'unexpected': 2}, {'minimum_sell_out_months': 1.5}])
def test_invalid_configuration_rejected(thresholds):
    with pytest.raises(ValueError): first(source(), thresholds)


def test_threshold_file_matches_defaults():
    assert load_commercial_thresholds('config/commercial_thresholds.json') == load_commercial_thresholds()


def test_registry_with_no_sell_out_is_not_declared_complete():
    result = build_partner_insights(source())
    assert next(p for p in result['partners'] if p['code'] == 'P2')['coverage'] == 0
