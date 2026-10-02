import streamlit as st

def inject_css():
 st.markdown('''<style>.block-container{padding-top:2rem;padding-bottom:3rem;max-width:1450px}.hero{padding:1.3rem 1.5rem;border-radius:16px;background:linear-gradient(115deg,#102a43,#2563eb);color:white;margin-bottom:1.2rem}.hero h1{margin:0;font-size:2rem}.hero p{margin:.4rem 0 0;opacity:.88}.kpi{border:1px solid #e2e8f0;border-radius:14px;padding:.8rem;background:#fff;box-shadow:0 1px 3px #0f172a0d}.stDataFrame{border:1px solid #e2e8f0;border-radius:12px;overflow:hidden}</style>''',unsafe_allow_html=True)
def badge(value):
 colors={'crítica':'#b91c1c','alta':'#c2410c','média':'#a16207','baixa':'#b91c1c','média':'#a16207'}
 return f"<span style='background:{colors.get(value,'#475569')};color:white;padding:3px 8px;border-radius:99px;font-size:.78rem'>{value}</span>"
