import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="TLA - Tech Layout Analytics",
    layout="wide"
)

# ==========================================
# CSS CUSTOMIZADO
# ==========================================
st.markdown("""
<style>
.main { background-color: #0e1117; color: #ffffff; }
.stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #00ff88; }
h1, h2, h3 { color: #00ff88 !important; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ TLA: Tech Layout Analytics")
st.caption("Sincronização: Tabela Seinfra + Orçamento do Usuário")

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.header("📊 Upload de Dados")
    file_seinfra = st.file_uploader("1. Tabela Oficial Seinfra (xlsx/csv)", type=["xlsx", "csv"])
    file_user = st.file_uploader("2. Sua Planilha de Quantidades (xlsx/csv)", type=["xlsx", "csv"])
    bdi = st.number_input("BDI Padrão (%)", value=25.0)
    st.divider()
    st.info("O TLA cruzará os códigos de insumo para atualizar os preços.")

# ==========================================
# FUNÇÕES DE LIMPEZA
# ==========================================
def fix_numeric(series):
    """Converte strings no formato BR (1.200,50) para float."""
    if series.dtype == 'object':
        series = series.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(series, errors='coerce').fillna(0)

def load_data(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file, sep=None, engine='python')
    return pd.read_excel(file)

# ==========================================
# EXECUÇÃO
# ==========================================
if file_seinfra and file_user:
    try:
        df_seinfra = load_data(file_seinfra)
        df_user = load_data(file_user)

        # Padroniza nomes de colunas (Minúsculo e sem espaços)
        df_seinfra.columns = df_seinfra.columns.astype(str).str.strip()
        df_user.columns = df_user.columns.astype(str).str.strip()

        # MAPEAMENTO DINÂMICO DE COLUNAS
        map_cols = {
            "Insumo": ["INSUMO", "COD", "CÓDIGO", "CÓD"],
            "Descrição": ["DESCRIÇÃO", "SERVIÇO", "ITEM", "DESCRICAO"],
            "Preço": ["PREÇO", "VALOR", "UNIT", "UNITÁRIO"],
            "Qtd": ["QUANT", "QUANTIDADE", "QTD"]
        }

        def rename_cols(df):
            for target, keywords in map_cols.items():
                for col in df.columns:
                    if any(k in col.upper() for k in keywords):
                        df.rename(columns={col: target}, inplace=True)
                        break
            return df

        df_seinfra = rename_cols(df_seinfra)
        df_user = rename_cols(df_user)

        # LIMPEZA DOS CÓDIGOS PARA O MERGE
        for df in [df_seinfra, df_user]:
            if "Insumo" in df.columns:
                df["Insumo"] = df["Insumo"].astype(str).str.replace('.0', '', regex=False).str.strip()

        # MERGE (Cruzamento de dados)
        if "Insumo" in df_user.columns and "Insumo" in df_seinfra.columns:
            # Mantém apenas colunas essenciais da Seinfra para o merge
            seinfra_subset = df_seinfra[["Insumo", "Preço"]].drop_duplicates("Insumo")
            
            df_final = pd.merge(df_user, seinfra_subset, on="Insumo", how="left", suffixes=('_original', '_seinfra'))

            # Se a planilha do usuário não tinha preço, usa o da Seinfra
            if "Preço_seinfra" in df_final.columns:
                df_final["Preço"] = df_final["Preço_seinfra"]
            
            # TRATAMENTO DE VALORES
            df_final["Preço"] = fix_numeric(df_final["Preço"])
            df_final["Qtd"] = fix_numeric(df_final["Qtd"])
            
            # CÁLCULOS
            df_final["Total_S/BDI"] = df_final["Preço"] * df_final["Qtd"]
            df_final["Total_C/BDI"] = df_final["Total_S/BDI"] * (1 + bdi/100)

            # EXIBIÇÃO
            c1, c2 = st.columns(2)
            c1.metric("Total Geral (Com BDI)", f"R$ {df_final['Total_C/BDI'].sum():,.2f}")
            c2.metric("Itens Encontrados", len(df_final[df_final["Preço"] > 0]))

            st.subheader("📋 Orçamento Atualizado")
            st.dataframe(df_final, use_container_width=True)

            # DOWNLOAD
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Orçamento TLA')
            
            st.download_button(
                label="📥 Baixar Orçamento Atualizado",
                data=output.getvalue(),
                file_name="orcamento_tla_final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Não foi possível localizar a coluna 'Insumo' em ambos os arquivos.")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
else:
    st.warning("Aguardando upload dos arquivos Seinfra e Orçamento.")
