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

.stDataFrame {
    border: 1px solid #2d2e35;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)

# ==========================================
# TÍTULO
# ==========================================
st.title("⚡ TLA: Tech Layout Analytics")

st.caption(
    "Sincronização em Tempo Real: "
    "Tabela Seinfra + Orçamento do Usuário"
)

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:

    st.header("📊 Upload de Dados")

    file_seinfra = st.file_uploader(
        "1. Tabela Oficial Seinfra (xlsx)",
        type=["xlsx"]
    )

    file_user = st.file_uploader(
        "2. Sua Planilha de Quantidades (xlsx/csv)",
        type=["xlsx", "csv"]
    )

    bdi = st.number_input(
        "BDI Padrão (%)",
        value=25.0
    )

    st.divider()

    st.info(
        "O TLA cruzará os Insumos "
        "da sua planilha com os "
        "preços da Seinfra."
    )

# ==========================================
# FUNÇÃO DE LIMPEZA DE COLUNAS
# ==========================================
def limpar_colunas(df):

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace("\n", "", regex=False)
        .str.replace("\r", "", regex=False)
        .str.replace("  ", " ", regex=False)
    )

    return df

# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================
if file_seinfra is not None and file_user is not None:

    try:

        # ==========================================
        # LEITURA SEINFRA
        # ==========================================
        df_seinfra = pd.read_excel(file_seinfra)

        # Limpa colunas
        df_seinfra = limpar_colunas(df_seinfra)

        # ==========================================
        # GARANTE COLUNA INSUMO NA SEINFRA
        # ==========================================
        if "Insumo" not in df_seinfra.columns:

            for coluna in df_seinfra.columns:

                if "insumo" in coluna.lower():

                    df_seinfra.rename(
                        columns={coluna: "Insumo"},
                        inplace=True
                    )

                    break

        # ==========================================
        # GARANTE COLUNA PREÇO UNITÁRIO
        # ==========================================
        if "PREÇO UNITÁRIO" not in df_seinfra.columns:

            for coluna in df_seinfra.columns:

                nome = coluna.upper()

                if (
                    "PREÇO" in nome
                    or "PRECO" in nome
                    or "UNITÁRIO" in nome
                    or "UNITARIO" in nome
                ):

                    df_seinfra.rename(
                        columns={coluna: "PREÇO UNITÁRIO"},
                        inplace=True
                    )

                    break

        # ==========================================
        # LEITURA PLANILHA USUÁRIO
        # ==========================================
        if file_user.name.lower().endswith(".csv"):

            df_user = pd.read_csv(
                file_user,
                skiprows=1
            )

        else:

            df_user = pd.read_excel(
                file_user,
                skiprows=1
            )

        # ==========================================
        # LIMPA COLUNAS
        # ==========================================
        df_user = limpar_colunas(df_user)

        # ==========================================
        # REMOVE LINHAS VAZIAS
        # ==========================================
        df_user = df_user.dropna(how="all")

        # ==========================================
        # DEBUG
        # ==========================================
        st.subheader("🔍 Colunas Detectadas")

        c1, c2 = st.columns(2)

        with c1:
            st.write("Planilha Usuário:")
            st.write(df_user.columns.tolist())

        with c2:
            st.write("Tabela Seinfra:")
            st.write(df_seinfra.columns.tolist())

        # ==========================================
        # GARANTE COLUNA INSUMO NO USUÁRIO
        # ==========================================
        if "Insumo" not in df_user.columns:

            for coluna in df_user.columns:

                if "insumo" in coluna.lower():

                    df_user.rename(
                        columns={coluna: "Insumo"},
                        inplace=True
                    )

                    break

        # ==========================================
        # VERIFICA INSUMO
        # ==========================================
        if "Insumo" not in df_user.columns:

            st.error(
                "A coluna 'Insumo' não foi encontrada "
                "na planilha do usuário."
            )

            st.stop()

        if "Insumo" not in df_seinfra.columns:

            st.error(
                "A coluna 'Insumo' não foi encontrada "
                "na tabela Seinfra."
            )

            st.stop()

        # ==========================================
        # LIMPEZA INSUMO
        # ==========================================
        df_user["Insumo"] = (
            df_user["Insumo"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df_seinfra["Insumo"] = (
            df_seinfra["Insumo"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        # ==========================================
        # REMOVE LINHAS SEM INSUMO
        # ==========================================
        df_user = df_user[
            df_user["Insumo"] != ""
        ]

        # ==========================================
        # GARANTE OUTRAS COLUNAS
        # ==========================================
        colunas_necessarias = [
            "DESCRIÇÃO DOS SERVIÇOS",
            "UND",
            "QUANT."
        ]

        for coluna in colunas_necessarias:

            if coluna not in df_user.columns:

                if coluna == "QUANT.":
                    df_user[coluna] = 0
                else:
                    df_user[coluna] = ""

        # ==========================================
        # MERGE
        # ==========================================
        df_merged = pd.merge(

            df_user[
                [
                    "Insumo",
                    "DESCRIÇÃO DOS SERVIÇOS",
                    "UND",
                    "QUANT."
                ]
            ],

            df_seinfra[
                [
                    "Insumo",
                    "PREÇO UNITÁRIO"
                ]
            ],

            on="Insumo",
            how="left"

        )

        # ==========================================
        # CONVERSÃO NUMÉRICA
        # ==========================================
        df_merged["PREÇO UNITÁRIO"] = (
            pd.to_numeric(
                df_merged["PREÇO UNITÁRIO"],
                errors="coerce"
            )
            .fillna(0)
        )

        df_merged["QUANT."] = (
            pd.to_numeric(
                df_merged["QUANT."],
                errors="coerce"
            )
            .fillna(0)
        )

        # ==========================================
        # CÁLCULOS
        # ==========================================
        df_merged["Custo_Atualizado"] = (
            df_merged["PREÇO UNITÁRIO"]
            * (1 + bdi / 100)
        )

        df_merged["Total_Item"] = (
            df_merged["Custo_Atualizado"]
            * df_merged["QUANT."]
        )

        # ==========================================
        # MÉTRICAS
        # ==========================================
        st.subheader("📊 Indicadores")

        c1, c2, c3 = st.columns(3)

        total_geral = df_merged["Total_Item"].sum()

        c1.metric(
            "Valor Total Orçado",
            f"R$ {total_geral:,.2f}"
        )

        c2.metric(
            "Itens Sincronizados",
            len(df_merged)
        )

        c3.metric(
            "BDI Aplicado",
            f"{bdi:.2f}%"
        )

        # ==========================================
        # GRÁFICO
        # ==========================================
        st.subheader(
            "📈 Impacto Financeiro por Item"
        )

        df_chart = (
            df_merged
            .sort_values(
                "Total_Item",
                ascending=True
            )
        )

        fig = px.bar(

            df_chart,

            x="Total_Item",

            y="DESCRIÇÃO DOS SERVIÇOS",

            orientation="h",

            color="Total_Item",

            template="plotly_dark",

            color_continuous_scale="GnBu",

            labels={
                "Total_Item": "Total (R$)",
                "DESCRIÇÃO DOS SERVIÇOS": "Item"
            }
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ==========================================
        # TABELA
        # ==========================================
        st.subheader("📑 Planilha Final")

        st.dataframe(

            df_merged[
                [
                    "Insumo",
                    "DESCRIÇÃO DOS SERVIÇOS",
                    "UND",
                    "QUANT.",
                    "PREÇO UNITÁRIO",
                    "Custo_Atualizado",
                    "Total_Item"
                ]
            ],

            use_container_width=True
        )

        # ==========================================
        # EXPORTAÇÃO EXCEL
        # ==========================================
        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df_merged.to_excel(
                writer,
                index=False,
                sheet_name="Orcamento_Atualizado"
            )

        st.download_button(
            label="📥 Baixar Planilha TLA Atualizada",
            data=output.getvalue(),
            file_name="orcamento_tla_final.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

    except Exception as e:

        st.error("❌ Erro detectado no processamento")

        st.code(str(e))

else:

    st.warning(
        "⚠️ Faça upload dos dois arquivos "
        "para ativar o dashboard."
    )
