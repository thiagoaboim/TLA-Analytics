import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ==========================================
# CONFIGURAÇÃO E INTERFACE
# ==========================================
st.set_page_config(page_title="TLA - Tech Layout Analytics", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #00ff88; }
    h1, h2, h3 { color: #00ff88 !important; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ TLA: Tech Layout Analytics")

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.header("📊 Upload de Dados")
    file_seinfra = st.file_uploader("1. Tabela Seinfra (xlsx/csv)", type=["xlsx", "csv"])
    file_user = st.file_uploader("2. Seu Orçamento (xlsx/csv)", type=["xlsx", "csv"])
    bdi = st.number_input("BDI (%)", value=25.0)

# ==========================================
# FUNÇÕES DE TRATAMENTO ROBUSTO
# ==========================================
def smart_load(file):
    """Lê o ficheiro e tenta identificar o separador automaticamente."""
    if file.name.endswith('.csv'):
        # Tenta ler com vírgula, se falhar tenta ponto e vírgula
        try:
            df = pd.read_csv(file, sep=',', encoding='utf-8')
            if len(df.columns) <= 1: 
                file.seek(0)
                df = pd.read_csv(file, sep=';', encoding='utf-8')
        except:
            file.seek(0)
            df = pd.read_csv(file, sep=';', encoding='latin1')
        return df
    return pd.read_excel(file)

def normalize_columns(df):
    """Força o mapeamento das colunas essenciais."""
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    mapping = {
        "INSUMO": ["INSUMO", "COD", "CÓDIGO", "CODIGO", "CÓD"],
        "DESCRICAO": ["DESCRIÇÃO", "SERVIÇO", "ITEM", "DESCRICAO", "NOME"],
        "PRECO": ["PREÇO", "VALOR", "UNIT", "UNITÁRIO", "PRECO"],
        "QTD": ["QUANT", "QUANTIDADE", "QTD", "TOTAL"]
    }
    
    new_cols = {}
    for target, keys in mapping.items():
        for col in df.columns:
            if any(k in col for k in keys):
                new_cols[col] = target
                break
    return df.rename(columns=new_cols)

def to_float(value):
    """Limpa strings financeiras (ex: 1.250,50 -> 1250.50)."""
    if isinstance(value, str):
        value = value.replace('.', '').replace(',', '.')
    return pd.to_numeric(value, errors='coerce')

# ==========================================
# PROCESSAMENTO
# ==========================================
if file_seinfra and file_user:
    try:
        # 1. Carga
        df_s = normalize_columns(smart_load(file_seinfra))
        df_u = normalize_columns(smart_load(file_user))

        # 2. Verificação Crítica
        if "INSUMO" not in df_s.columns or "INSUMO" not in df_u.columns:
            st.error("❌ Erro: Não encontrei a coluna de 'Código' ou 'Insumo' nos ficheiros.")
            st.write("Colunas detetadas na Seinfra:", list(df_s.columns))
            st.write("Colunas detetadas no seu ficheiro:", list(df_u.columns))
            st.stop()

        # 3. Limpeza das Chaves de Cruzamento
        df_s["INSUMO"] = df_s["INSUMO"].astype(str).str.strip()
        df_u["INSUMO"] = df_u["INSUMO"].astype(str).str.strip()

        # 4. Cruzamento (Merge)
        # Pegamos apenas o último preço disponível para cada insumo na Seinfra
        df_s_precos = df_s.drop_duplicates(subset=["INSUMO"], keep='last')[["INSUMO", "PRECO"]]
        
        df_final = pd.merge(df_u, df_s_precos, on="INSUMO", how="left", suffixes=('_old', '_novo'))

        # 5. Cálculos Financeiros
        df_final["PRECO_FINAL"] = to_float(df_final["PRECO_novo"].fillna(df_final.get("PRECO_old", 0)))
        df_final["QTD"] = to_float(df_final.get("QTD", 0))
        
        df_final["TOTAL_ITEM"] = df_final["PRECO_FINAL"] * df_final["QTD"] * (1 + bdi/100)

        # 6. Dashboard
        c1, c2 = st.columns(2)
        total = df_final["TOTAL_ITEM"].sum()
        c1.metric("Orçamento Total (c/ BDI)", f"R$ {total:,.2f}")
        c2.metric("Itens Sincronizados", f"{len(df_final[df_final['PRECO_FINAL'] > 0])}")

        st.subheader("📋 Planilha Processada")
        st.dataframe(df_final, use_container_width=True)

        # 7. Exportação
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False)
        
        st.download_button("📥 Baixar Planilha Corrigida", output.getvalue(), "tla_final.xlsx")

    except Exception as e:
        st.error(f"Ocorreu um erro técnico: {e}")
else:
    st.info("Coloque os dois ficheiros acima para começar.")
