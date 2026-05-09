import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import sys

# Impede conflitos de bibliotecas internas
if 'warnings' in sys.modules:
    import warnings
    warnings.filterwarnings('ignore')

st.set_page_config(page_title="TLA - Tech Layout Analytics", layout="wide")

# Estética Dark Tech
st.markdown('''
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #00ff88 !important; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #00ff88 !important; }
    </style>
''', unsafe_allow_html=True)

st.title("⚡ TLA: Tech Layout Analytics")

with st.sidebar:
    st.header("📂 Importação")
    file_seinfra = st.file_uploader("1. Tabela Seinfra (xlsx)", type=["xlsx"])
    file_usuario = st.file_uploader("2. Sua Planilha (xlsx/csv)", type=["xlsx", "csv"])
    bdi = st.number_input("BDI (%)", value=25.0)

if file_seinfra and file_usuario:
    try:
        # 1. PROCESSAMENTO SEINFRA - Usando motor openpyxl para evitar o erro de 'warnings'
        df_seinfra = pd.read_excel(file_seinfra, engine='openpyxl')
        df_seinfra.columns = [str(c).strip().upper() for c in df_seinfra.columns]
        
        # Busca dinâmica das colunas da Seinfra
        col_id_seinfra = next((c for c in df_seinfra.columns if any(x in c for x in ['CÓDIGO', 'CODIGO', 'INSUMO'])), None)
        col_preco_seinfra = next((c for c in df_seinfra.columns if any(x in c for x in ['PREÇO UNITÁRIO', 'PRECO UNITARIO', 'TOTAL', 'VALOR UNIT', 'PREÇO'])), None)

        if not col_id_seinfra or not col_preco_seinfra:
            st.error(f"❌ Colunas não identificadas na Seinfra. Colunas lidas: {list(df_seinfra.columns)}")
            st.stop()

        # 2. PROCESSAMENTO USUÁRIO
        if file_usuario.name.endswith('.csv'):
            df_raw = pd.read_csv(file_usuario)
        else:
            df_raw = pd.read_excel(file_usuario, engine='openpyxl')
        
        # Localiza cabeçalho (procura 'Codigo Seinfra')
        header_row = 0
        for i in range(min(len(df_raw), 30)):
            row_str = [str(val).strip().lower() for val in df_raw.iloc[i].values]
            if any('codigo' in val or 'seinfra' in val for val in row_str):
                header_row = i + 1
                break
        
        # Recarrega com o cabeçalho correto
        file_usuario.seek(0)
        if file_usuario.name.endswith('.csv'):
            df_user = pd.read_csv(file_usuario, skiprows=header_row)
        else:
            df_user = pd.read_excel(file_usuario, skiprows=header_row, engine='openpyxl')
            
        df_user.columns = [str(c).strip() for c in df_user.columns]
        col_projeto = next((c for c in df_user.columns if 'Codigo' in c or 'Seinfra' in c), None)

        if not col_projeto:
            st.error("❌ Coluna 'Codigo Seinfra' não encontrada na sua planilha de projeto.")
            st.stop()

        # 3. MERGE E CÁLCULOS
        df_user[col_projeto] = df_user[col_projeto].astype(str).str.strip()
        df_seinfra[col_id_seinfra] = df_seinfra[col_id_seinfra].astype(str).str.strip()

        df_final = pd.merge(
            df_user,
            df_seinfra[[col_id_seinfra, col_preco_seinfra]],
            left_on=col_projeto,
            right_on=col_id_seinfra,
            how='left'
        )
        
        # Conversão de valores
        df_final[col_preco_seinfra] = pd.to_numeric(df_final[col_preco_seinfra], errors='coerce').fillna(0)
        col_quant = next((c for c in df_final.columns if 'QUANT' in c.upper()), 'QUANT.')
        df_final[col_quant] = pd.to_numeric(df_final[col_quant], errors='coerce').fillna(0)
        
        df_final['Custo_Unit_BDI'] = df_final[col_preco_seinfra] * (1 + bdi/100)
        df_final['Subtotal'] = df_final['Custo_Unit_BDI'] * df_final[col_quant]
        
        # 4. DASHBOARD
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Total Orçado", f"R$ {df_final['Subtotal'].sum():,.2f}")
            st.metric("Itens Sincronizados", len(df_final[df_final[col_preco_seinfra] > 0]))
            
        with c2:
            df_chart = df_final.sort_values('Subtotal', ascending=True).query("Subtotal > 0")
            if not df_chart.empty:
                col_desc = next((c for c in df_final.columns if 'DESCRI' in c.upper()), df_final.columns[1])
                fig = px.bar(df_chart, x='Subtotal', y=col_desc, orientation='h',
                             color='Subtotal', template="plotly_dark", color_continuous_scale='GnBu')
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("📑 Tabela Analítica TLA")
        st.dataframe(df_final, use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False)
        st.download_button("📥 Baixar Planilha TLA", output.getvalue(), "tla_resultado.xlsx")

    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
        st.info("Dica: Tente salvar sua tabela Seinfra como um arquivo .xlsx simples antes de carregar.")

else:
    st.info("💡 Carregue a Seinfra e sua Planilha para iniciar.")
