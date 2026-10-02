from pathlib import Path
import streamlit as st
from caderno_inteligente.ingestion import load_workbook
from caderno_inteligente.validation import validate_dataset
from caderno_inteligente.transformations import normalise_dataset
from caderno_inteligente.indicators import build_sku_indicators
from caderno_inteligente.rules import evaluate_rules,load_rule_thresholds
from caderno_inteligente.prioritization import prioritize,load_weights
from caderno_inteligente.feedback import ACTIONS,save_feedback,list_feedback
from caderno_inteligente.ui import inject_css
SOURCE=Path('data/source/Base de Dados - Caderno Inteligente.xlsm'); DB=Path('runtime/feedback.db')
st.set_page_config('Caderno Inteligente','📒',layout='wide'); inject_css()
@st.cache_data
def pipeline():
 d=normalise_dataset(load_workbook(SOURCE)); q=validate_dataset(d); i=build_sku_indicators(d); x=evaluate_rules(i,load_rule_thresholds()); return q,i,x,prioritize(x,load_weights(),i)
q,ind,issues,ranking=pipeline()
st.markdown("<div class='hero'><h1>Caderno Inteligente</h1><p>Painel de atenção operacional para PCP — evidências, confiança e decisões humanas.</p></div>")
st.sidebar.header('Navegação'); page=st.sidebar.radio('Seção',['Visão geral','Prioridades','Detalhe do SKU','Qualidade','Feedback'])
st.sidebar.caption('A ordenação indica atenção; não libera produção automaticamente.')
if page=='Visão geral':
 labels=[('SKUs priorizados',len(ranking)),('Risco de ruptura',issues.code.str.startswith('RUP').sum()),('Pedidos sem OP',(issues.code=='ORDER_WITHOUT_PRODUCTION').sum()),('Excesso',(issues.code=='EXCESS_COVERAGE').sum()),('Baixa confiança',(ranking.confidence=='baixa').sum())]
 cols=st.columns(5)
 for c,(l,v) in zip(cols,labels): c.metric(l,v)
 st.subheader('Prioridades que exigem atenção'); st.dataframe(ranking[['priority','sku','product','family','attention_score','confidence']].head(10),hide_index=True,use_container_width=True)
 a,b=st.columns(2); a.bar_chart(issues.code.value_counts()); b.bar_chart(ranking.confidence.value_counts())
elif page=='Prioridades':
 st.subheader('Lista de prioridades'); search=st.text_input('Buscar SKU ou produto'); fam=st.multiselect('Família',sorted(ranking.family.unique())); conf=st.multiselect('Confiança',['baixa','média']); view=ranking.copy()
 if search:view=view[view.sku.str.contains(search,case=False)|view.product.str.contains(search,case=False)]
 if fam:view=view[view.family.isin(fam)]
 if conf:view=view[view.confidence.isin(conf)]
 st.caption(f'{len(view)} SKUs encontrados. Abra o detalhe para evidências e origem dos dados.')
 st.dataframe(view[['priority','sku','product','family','attention_score','confidence','confidence_reason','reasons']],hide_index=True,use_container_width=True)
elif page=='Detalhe do SKU':
 sku=st.selectbox('Selecione o SKU',ind.SKU); r=ind[ind.SKU==sku].iloc[0]; st.subheader(f'{sku} · {r.Produto}')
 c=st.columns(6)
 for col,label,key in zip(c,['Cobertura','Lead time','Segurança','Carteira','OP','Estoque projetado'],['coverage_days_calculated','lead_time_days','safety_stock_days','backlog_order_quantity','production_order_quantity','projected_stock_quantity']):col.metric(label,f'{r[key]:.0f}')
 t1,t2,t3=st.tabs(['Riscos e evidências','Canal e confiança','Dados operacionais'])
 with t1:
  for _,x in issues[issues.sku==sku].iterrows():
   with st.expander(f"{x.code} · {x.severity}"): st.write(x.description); st.json({'valores':x.values_used,'origem':x.data_origin})
 with t2: st.info('Sell-out não disponível significa ausência de observação, nunca venda zero.' if not r.has_sell_out else 'Há sell-out observado; a cobertura B2B ainda é parcial.'); st.metric('Parceiros com sell-out',int(r.sell_out_partner_count))
 with t3: st.dataframe(ind[ind.SKU==sku],hide_index=True,use_container_width=True)
elif page=='Qualidade':
 st.subheader('Qualidade e cobertura dos dados'); c=st.columns(3); c[0].metric('Erros',len(q['errors']));c[1].metric('Avisos',len(q['warnings']));c[2].metric('Cobertura sell-out',f"{q['sell_out_coverage']['coverage']:.0%}")
 st.dataframe(__import__('pandas').DataFrame(q['sheets']).T[['records','duplicate_keys']],use_container_width=True); st.json({'integridade_referencial':q['foreign_keys']})
else:
 st.subheader('Registrar decisão do PCP'); sku=st.selectbox('SKU',ranking.sku); action=st.selectbox('Ação',ACTIONS); user=st.text_input('Usuário'); note=st.text_area('Observação')
 if st.button('Salvar feedback',type='primary'): save_feedback(DB,sku,action,note,user);st.success('Feedback salvo em SQLite separado da base XLSM.');st.rerun()
 st.subheader('Histórico'); st.dataframe(list_feedback(DB),hide_index=True,use_container_width=True)
