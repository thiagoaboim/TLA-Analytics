import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# Configuração de Interface
st.set_page_config(page_title="TLA - Tech Layout Analytics", layout="wide")

st.markdown('''
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #00ff88 !important; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #00ff88 !important; }
    .stDataFrame { border: 1px solid #1a1c24; }
    </style>
''', unsafe_allow_html=True)

st.title("⚡ TLA: Tech Layout Analytics")
st.caption("Filtro Ativo: Apenas itens preenchidos com Código e Quantidade")

with st.sidebar:
    st.header("📂 Importação")
    file_seinfra = st.file_uploader("1. Tabela Seinfra (.xlsx)", type=["xlsx"])
    file_usuario = st.file_uploader("2. Sua Planilha de Orçamento (.xlsx/.csv)", type=["xlsx", "csv"])
    bdi = st.number_input("BDI (%)", value=25.0)

if file_seinfra and file_usuario:
    try:
        # 1. LEITURA DA SEINFRA (Base de Preços)
        df_seinfra = pd.read_excel(file_seinfra, engine='openpyxl')
        df_seinfra.columns = [str(c).strip().upper() for c in df_seinfra.columns]
        
        col_id_seinfra = next((c for c in df_seinfra.columns if any(x in c for x in ['CÓDIGO', 'CODIGO', 'INSUMO'])), None)
        col_preco_seinfra = next((c for c in df_seinfra.columns if any(x in c for x in ['PREÇO UNITÁRIO', 'PRECO UNITARIO', 'TOTAL', 'VALOR UNIT'])), None)

        # 2. LEITURA DO ORÇAMENTO DO USUÁRIO
        # Localização dinâmica do cabeçalho
        df_raw = pd.read_csv(file_usuario) if file_usuario.name.endswith('.csv') else pd.read_excel(file_usuario, engine='openpyxl')
        
        header_idx = 0
        for i in range(min(len(df_raw), 40)):
            row = [str(val).strip().lower() for val in df_raw.iloc[i].values]
            if any('codigo' in val for val in row) and any('descri' in val for val in row):
                header_idx = i + 1
                break
        
        file_usuario.seek(0)
        df_user = pd.read_csv(file_usuario, skiprows=header_idx) if file_usuario.name.endswith('.csv') else pd.read_excel(file_usuario, skiprows=header_idx, engine='openpyxl')
        
        # Limpeza de nomes de colunas
        df_user.columns = [str(c).strip() for c in df_user.columns]
        
        # Identificação de colunas críticas
        col_cod = next((c for c in df_user.columns if 'Codigo' in c or 'Seinfra' in c), None)
        col_qnt = next((c for c in df_user.columns if 'QUANT' in c.upper()), None)
        col_des = next((c for c in df_user.columns if 'DESCRI' in c.upper()), None)

        if not col_cod or not col_qnt:
            st.error("❌ Não foi possível identificar as colunas de 'Código' ou 'Quantidade'.")
            st.stop()

        # --- FILTRO CRÍTICO: APENAS ITENS PREENCHIDOS ---
        # 1. Remove linhas onde o código está vazio
        df_user = df_user.dropna(subset=[col_cod])
        # 2. Converte quantidade para número e remove zeros ou vazios
        df_user[col_qnt] = pd.to_numeric(df_user[col_qnt], errors='coerce').fillna(0)
        df_user = df_user[df_user[col_qnt] > 0]
        
        # 3. MERGE (Sincronização)
        df_user[col_cod] = df_user[col_cod].astype(str).str.strip()
        df_seinfra[col_id_seinfra] = df_seinfra[col_id_seinfra].astype(str).str.strip()

        df_final = pd.merge(df_user, df_seinfra[[col_id_seinfra, col_preco_seinfra]], 
                            left_on=col_cod, right_on=col_id_seinfra, how='left')

        # 4. CÁLCULOS FINAIS
        df_final[col_preco_seinfra] = pd.to_numeric(df_final[col_preco_seinfra], errors='coerce').fillna(0)
        df_final['Preço Unit c/ BDI'] = df_final[col_preco_seinfra] * (1 + bdi/100)
        df_final['Total Item'] = df_final['Preço Unit c/ BDI'] * df_final[col_qnt]

        # 5. EXIBIÇÃO DASHBOARD
        c1, c2, c3 = st.columns(3)
        total_geral = df_final['Total Item'].sum()
        c1.metric("Orçamento Total", f"R$ {total_geral:,.2f}")
        c2.metric("Itens com Valor", len(df_final[df_final['Total Item'] > 0]))
        c3.metric("BDI Aplicado", f"{bdi}%")

        # Gráfico de Impacto Financeiro (Apenas itens com valor > 0)
        st.subheader("📊 Ranking de Custos (Ordem Crescente)")
        df_chart = df_final[df_final['Total Item'] > 0].sort_values('Total Item', ascending=True)
        
        if not df_chart.empty:
            fig = px.bar(df_chart, x='Total Item', y=col_des, orientation='h',
                         color='Total Item', template="plotly_dark", 
                         color_continuous_scale='GnBu', height=600)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📑 Tabela de Insumos Processados")
        st.dataframe(df_final[[col_cod, col_des, 'UND', col_qnt, 'Preço Unit c/ BDI', 'Total Item']], use_container_width=True)

        # Exportação
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False)
        st.download_button("📥 Baixar Orçamento TLA Sincronizado", output.getvalue(), "orcamento_tla_final.xlsx")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
        st.info("Certifique-se de que a planilha não contém células mescladas nos títulos das colunas.")

else:
    st.info("Aguardando upload dos arquivos Seinfra e Orçamento para análise.")
