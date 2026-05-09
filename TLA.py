import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# Interface de Alta Fidelidade (Dark Tech)
st.set_page_config(
    page_title="TLA - Tech Layout Analytics",
    layout="wide"
)

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

st.title("⚡ TLA: Tech Layout Analytics")

st.caption(
    "Sincronização em Tempo Real: "
    "Tabela Seinfra + Orçamento do Usuário"
)

# =========================
# Sidebar
# =========================
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
        "O TLA cruzará os Insumos da sua "
        "planilha com os preços da Seinfra."
    )

# =========================
# Execução Principal
# =========================
if file_seinfra and file_user:

    try:

        # =========================
        # Base Seinfra
        # =========================
        df_seinfra = pd.read_excel(file_seinfra)

        # Remove espaços dos nomes
        df_seinfra.columns = (
            df_seinfra.columns
            .astype(str)
            .str.strip()
        )

        # =========================
        # Base Usuário
        # =========================
        if file_user.name.endswith('.csv'):

            df_user = pd.read_csv(
                file_user,
                skiprows=7
            )

        else:

            df_user = pd.read_excel(
                file_user,
                skiprows=7
            )

        # =========================
        # Limpeza Geral
        # =========================
        df_user.columns = (
            df_user.columns
            .astype(str)
            .str.strip()
        )

        # Remove linhas completamente vazias
        df_user = df_user.dropna(how='all')

        # Cria coluna Insumo vazia caso não exista
        if 'Insumo' not in df_user.columns:
            df_user['Insumo'] = ''

        # Limpeza da coluna Insumo
        df_user['Insumo'] = (
            df_user['Insumo']
            .fillna('')
            .astype(str)
            .str.strip()
        )

        # Remove linhas com Insumo vazio
        df_user = df_user[
            df_user['Insumo'] != ''
        ]

        # =========================
        # Garante colunas mínimas
        # =========================
        colunas_minimas = [
            'DESCRIÇÃO DOS SERVIÇOS',
            'UND',
            'QUANT.'
        ]

        for coluna in colunas_minimas:

            if coluna not in df_user.columns:
                df_user[coluna] = ''

        # =========================
        # Merge
        # =========================
        df_merged = pd.merge(

            df_user[
                [
                    'Insumo',
                    'DESCRIÇÃO DOS SERVIÇOS',
                    'UND',
                    'QUANT.'
                ]
            ],

            df_seinfra[
                [
                    'Insumo',
                    'PREÇO UNITÁRIO'
                ]
            ],

            on='Insumo',
            how='left'
        )

        # =========================
        # Trata valores vazios
        # =========================
        df_merged['PREÇO UNITÁRIO'] = (
            pd.to_numeric(
                df_merged['PREÇO UNITÁRIO'],
                errors='coerce'
            )
            .fillna(0)
        )

        df_merged['QUANT.'] = (
            pd.to_numeric(
                df_merged['QUANT.'],
                errors='coerce'
            )
            .fillna(0)
        )

        # =========================
        # Cálculos
        # =========================
        df_merged['Custo_Atualizado'] = (
            df_merged['PREÇO UNITÁRIO']
            * (1 + bdi / 100)
        )

        df_merged['Total_Item'] = (
            df_merged['Custo_Atualizado']
            * df_merged['QUANT.']
        )

        # =========================
        # Indicadores
        # =========================
        c1, c2, c3 = st.columns(3)

        total_geral = df_merged['Total_Item'].sum()

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
            f"{bdi}%"
        )

        # =========================
        # Gráfico
        # =========================
        st.subheader(
            "📈 Impacto Financeiro por Item"
        )

        df_chart = (
            df_merged
            .sort_values(
                'Total_Item',
                ascending=True
            )
        )

        fig = px.bar(

            df_chart,

            x='Total_Item',

            y='DESCRIÇÃO DOS SERVIÇOS',

            orientation='h',

            color='Total_Item',

            template='plotly_dark',

            color_continuous_scale='GnBu',

            labels={
                'Total_Item': 'Total (R$)',
                'DESCRIÇÃO DOS SERVIÇOS': 'Item'
            }
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # =========================
        # Tabela
        # =========================
        st.subheader(
            "📑 Planilha Final"
        )

        st.dataframe(

            df_merged[
                [
                    'Insumo',
                    'DESCRIÇÃO DOS SERVIÇOS',
                    'UND',
                    'QUANT.',
                    'Custo_Atualizado',
                    'Total_Item'
                ]
            ],

            use_container_width=True
        )

        # =========================
        # Exportação
        # =========================
        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine='openpyxl'
        ) as writer:

            df_merged.to_excel(
                writer,
                index=False,
                sheet_name='Orcamento_Atualizado'
            )

        st.download_button(
            "📥 Baixar Planilha TLA Atualizada",
            output.getvalue(),
            "orcamento_tla_final.xlsx"
        )

    except Exception:
        pass

else:

    st.warning(
        "⚠️ Faça upload dos dois arquivos "
        "para ativar o dashboard."
    )
