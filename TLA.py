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
.main {
    background-color: #0e1117;
    color: #ffffff;
}
.stMetric {
    background-color: #1a1c24;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #00ff88;
}
h1, h2, h3 {
    color: #00ff88 !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# TÍTULO
# ==========================================
st.title("⚡ TLA: Tech Layout Analytics")
st.caption("Sincronização em Tempo Real: Tabela Seinfra + Orçamento do Usuário")

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.header("📊 Upload de Dados")
    file_seinfra = st.file_uploader("1. Tabela Oficial Seinfra (xlsx)", type=["xlsx"])
    file_user = st.file_uploader("2. Sua Planilha de Quantidades (xlsx/csv)", type=["xlsx", "csv"])
    bdi = st.number_input("BDI Padrão (%)", value=25.0)
    st.divider()
    st.info("O TLA cruzará os Insumos da sua planilha com os preços da Seinfra.")

# ==========================================
# FUNÇÕES DE APOIO
# ==========================================
def clean_numeric(series):
    """Converte strings com vírgula para float de forma segura."""
    if series.dtype == 'object':
        series = series.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(series, errors='coerce').fillna(0)

# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================
if file_seinfra and file_user:
    try:
        # LEITURA SEINFRA
        df_seinfra = pd.read_excel(file_seinfra, engine='openpyxl')
        df_seinfra.columns = df_seinfra.columns.astype(str).str.strip()

        # LEITURA PLANILHA USUÁRIO
        if file_user.name.endswith(".csv"):
            df_user = pd.read_csv(file_user, skiprows=1)
        else:
            df_user = pd.read_excel(file_user, skiprows=1, engine='openpyxl')
        
        df_user.columns = df_user.columns.astype(str).str.strip()
        df_user = df_user.dropna(how="all")

        # PADRONIZAÇÃO DE COLUNAS (BUSCA POR KEYWORDS)
        mapping = {
            "Insumo": ["INSUMO", "CODIGO", "CÓDIGO"],
            "DESCRIÇÃO DOS SERVIÇOS": ["DESCRIÇÃO", "SERVIÇO", "ITEM", "DESCRICAO"],
            "UND": ["UNIDADE", "UND", "UNID"],
            "QUANT.": ["QUANT", "QUANTIDADE", "QTD"]
        }

        for target, keywords in mapping.items():
            for col in df_user.columns:
                if any(kw in col.upper() for kw in keywords):
                    df_user.rename(columns={col: target}, inplace=True)
                    break

        # GARANTE COLUNA PREÇO NA SEINFRA
        for col in df_seinfra.columns:
            if "PREÇO" in col.upper() or "PRECO" in col.upper():
                df_seinfra.rename(columns={col: "PREÇO UNITÁRIO"}, inplace=True)
                break
        
        # GARANTE COLUNA INSUMO NA SEINFRA
        for col in df_seinfra.columns:
            if col.upper() in ["INSUMO", "CÓDIGO", "CODIGO"]:
                df_seinfra.rename(columns={col: "Insumo"}, inplace=True)
                break

        # LIMPEZA E FORMATAÇÃO DE CHAVES (IMPORTANTE PARA O MERGE)
        for df in [df_user, df_seinfra]:
            if "Insumo" in df.columns:
                df["Insumo"] = df["Insumo"].astype(str).str.strip()

        # MERGE
        cols_to_keep = [c for c in ["Insumo", "DESCRIÇÃO DOS SERVIÇOS", "UND", "QUANT."] if c in df_user.columns]
        df_merged = pd.merge(
            df_user[cols_to_keep],
            df_seinfra[["Insumo", "PREÇO UNITÁRIO"]],
            on="Insumo",
            how="left"
        )

        # TRATAMENTO NUMÉRICO PÓS-MERGE
        df_merged["PREÇO UNITÁRIO"] = clean_numeric(df_merged["PREÇO UNITÁRIO"])
        df_merged["QUANT."] = clean_numeric(df_merged["QUANT."])

        # CÁLCULOS
        df_merged["Custo_Atualizado"] = df_merged["PREÇO UNITÁRIO"] * (1 + bdi / 100)
        df_merged["Total_Item"] = df_merged["Custo_Atualizado"] * df_merged["QUANT."]

        # MÉTRICAS
        total_geral = df_merged["Total_Item"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Valor Total (C/ BDI)", f"R$ {total_geral:,.2f}")
        c2.metric("Itens Processados", len(df_merged))
        c3.metric("BDI Aplicado", f"{bdi}%")

        # GRÁFICO
        st.subheader("📈 Impacto Financeiro por Item")
        df_chart = df_merged.nlargest(15, "Total_Item").sort_values("Total_Item")
        fig = px.bar(
            df_chart,
            x="Total_Item",
            y="DESCRIÇÃO DOS SERVIÇOS",
            orientation="h",
            color="Total_Item",
            template="plotly_dark",
            color_continuous_scale="GnBu"
        )
        st.plotly_chart(fig, use_container_width=True)

        # TABELA
        st.subheader("📑 Planilha Final")
        st.dataframe(df_merged, use_container_width=True)

        # EXPORTAÇÃO
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_merged.to_excel(writer, index=False, sheet_name="Orcamento_TLA")
        
        st.download_button(
            "📥 Baixar Planilha TLA Atualizada",
            output.getvalue(),
            "orcamento_tla_final.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Erro ao processar arquivos: {e}")
        st.info("Dica: Verifique se os nomes das colunas nas planilhas são compatíveis.")

else:
    st.warning("⚠️ Faça upload dos dois arquivos (Seinfra + Sua Planilha) para ativar o dashboard.")
