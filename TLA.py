import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# Interface de Alta Fidelidade (Dark Tech)
st.set_page_config(page_title="TLA - Tech Layout Analytics", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #00ff88; }
    h1, h2, h3 { color: #00ff88 !important; }
    .stDataFrame { border: 1px solid #2d2e35; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ TLA: Tech Layout Analytics")
st.caption("Sincronização em Tempo Real: Tabela Seinfra + Orçamento do Usuário")

# Sidebar de Controle
with st.sidebar:
    st.header("📊 Upload de Dados")
    file_seinfra = st.file_uploader("1. Tabela Oficial Seinfra (xlsx)", type=["xlsx"])
    file_usuario = st.file_uploader("2. Sua Planilha de Quantidades (xlsx/csv)", type=["xlsx", "csv"])
    bdi = st.number_input("BDI Padrão (%)", value=25.0)
    st.divider()
    st.info("O TLA cruzará os Insumos da sua planilha com os preços da Seinfra.")

if file_seinfra and file_usuario:
    # Lendo Base Seinfra
    df_seinfra = pd.read_excel(file_seinfra)
    
    # Lendo Planilha do Usuário (Tratando o CSV enviado ou XLSX)
    if file_usuario.name.endswith('.csv'):
        df_user = pd.read_csv(file_usuario, skiprows=7) # Pula o cabeçalho conforme seu modelo
    else:
        df_user = pd.read_excel(file_usuario, skiprows=7)

    # Limpeza de dados (removendo linhas vazias de Insumo)
    df_user = df_user.dropna(subset=['Insumo'])

    # Cruzamento de Dados (Merge)
    # Buscamos o Preço Unitário na Seinfra usando o Insumo da sua planilha
    df_merged = pd.merge(
        df_user[['Insumo', 'DESCRIÇÃO DOS SERVIÇOS', 'UND', 'QUANT.']], 
        df_seinfra[['Insumo', 'PREÇO UNITÁRIO']], 
        left_on='Insumo', 
        right_on='Insumo', 
        how='left'
    )

    # Cálculos Dinâmicos
    df_merged['Custo_Atualizado'] = df_merged['PREÇO UNITÁRIO'] * (1 + bdi/100)
    df_merged['Total_Item'] = df_merged['Custo_Atualizado'] * df_merged['QUANT.'].fillna(0)

    # Indicadores Topo
    c1, c2, c3 = st.columns(3)
    total_geral = df_merged['Total_Item'].sum()
    c1.metric("Valor Total Orçado", f"R$ {total_geral:,.2f}")
    c2.metric("Itens Sincronizados", len(df_merged))
    c3.metric("BDI Aplicado", f"{bdi}%")

    # Gráfico de Pareto / Ordem Crescente de Custo
    st.subheader("📈 Impacto Financeiro por Item (Sincronizado Seinfra)")
    df_chart = df_merged.sort_values('Total_Item', ascending=True).query("Total_Item > 0")
    
    fig = px.bar(
        df_chart, 
        x='Total_Item', 
        y='DESCRIÇÃO DOS SERVIÇOS', 
        orientation='h',
        color='Total_Item',
        template="plotly_dark",
        color_continuous_scale='GnBu',
        labels={'Total_Item': 'Total (R$)', 'DESCRIÇÃO DOS SERVIÇOS': 'Item'}
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabela Editável e Final
    st.subheader("📑 Planilha Final para Exportação")
    st.write("Valores recalculados com base na última tabela Seinfra carregada:")
    st.dataframe(df_merged[['Insumo', 'DESCRIÇÃO DOS SERVIÇOS', 'UND', 'QUANT.', 'Custo_Atualizado', 'Total_Item']], use_container_width=True)

    # Exportação
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_merged.to_excel(writer, index=False, sheet_name='Orcamento_Atualizado')
    
    st.download_button("📥 Baixar Planilha TLA Atualizada", output.getvalue(), "orcamento_tla_final.xlsx")

else:
    st.warning("⚠️ Por favor, faça o upload de ambos os arquivos (Tabela Seinfra e Seu Modelo) para ativar o Dashboard.")
