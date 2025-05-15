import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from modules.data_handler import carregar_dados, salvar_dados
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from modules.data_handler import carregar_dados, salvar_dados

plt.style.use("ggplot")

def mostrar_grafico_edicoes_por_mes():
    from matplotlib import ticker
    dados = carregar_dados()
    if not dados.get("planilhas_editadas"):
        return st.info("Sem dados de edições.")
    
    df = pd.DataFrame(dados['planilhas_editadas'])
    df['data'] = pd.to_datetime(df['data'])
    df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
    resumo = df.groupby('mes_ano').size().reset_index(name='contagem')

    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    bars = ax.bar(resumo['mes_ano'], resumo['contagem'], color="#4A90E2", edgecolor="black")

    ax.set_title("Edições por Mês", fontsize=14, weight='bold')
    ax.set_xlabel("Mês", fontsize=11)
    ax.set_ylabel("Quantidade", fontsize=11)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    if not resumo.empty:
        ax.set_ylim(0, resumo['contagem'].max() * 1.2)

        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.05, int(yval),
                    ha='center', va='bottom', fontsize=10, color='black')

    plt.tight_layout()
    st.pyplot(fig)

def mostrar_grafico_edicoes_por_usuario():
    from matplotlib import ticker
    dados = carregar_dados()
    if not dados.get("planilhas_editadas"):
        return st.info("Sem dados de edições.")
    
    df = pd.DataFrame(dados['planilhas_editadas'])
    contagem = df['usuario'].value_counts().reset_index()
    contagem.columns = ['usuario', 'quantidade']

    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    bars = ax.bar(contagem['usuario'], contagem['quantidade'], color="#50E3C2", edgecolor="black")

    ax.set_title("Edições por Usuário", fontsize=14, weight='bold')
    ax.set_xlabel("Usuário", fontsize=11)
    ax.set_ylabel("Quantidade", fontsize=11)
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    if not contagem.empty:
        ax.set_ylim(0, contagem['quantidade'].max() * 1.2)

        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.05, int(yval),
                    ha='center', va='bottom', fontsize=10, color='black')

    plt.tight_layout()
    st.pyplot(fig)

def mostrar_historico_downloads():
    dados = carregar_dados()
    if not dados.get("historico_downloads"): return st.info("Sem histórico de downloads.")
    df = pd.DataFrame(dados['historico_downloads'])
    df['data'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d %H:%M:%S')
    st.dataframe(df[['data', 'usuario', 'planilha']])

def limpar_historico_downloads():
    dados = carregar_dados()
    dados['historico_downloads'] = []
    return salvar_dados(dados)

def painel_dashboard():
    st.subheader("Dashboard")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Limpar Edições"):
            dados = carregar_dados()
            dados['planilhas_editadas'] = []
            salvar_dados(dados)
            st.rerun()
    with col2:
        if st.button("Limpar Downloads"):
            if limpar_historico_downloads():
                st.rerun()

    st.markdown("### Estatísticas de Edição")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        mostrar_grafico_edicoes_por_mes()
    with col_g2:
        mostrar_grafico_edicoes_por_usuario()

    st.markdown("### Histórico de Downloads")
    mostrar_historico_downloads()
