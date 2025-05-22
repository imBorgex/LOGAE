import streamlit as st
from modules.auth import login_screen
from modules.processor import planilha_editor
from modules.admin import painel_administrador
from modules.analytics import painel_dashboard
from modules.data_handler import carregar_dados

st.set_page_config(page_title="Sistema de Planilha - Logae", layout="wide")
st.title("Sistema de Planilha - Logae")

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
    st.session_state.nivel_acesso = None

if not st.session_state.usuario_logado:
    login_screen()
else:
    usuario = st.session_state.usuario_logado
    nivel = st.session_state.nivel_acesso

    st.sidebar.success(f"Logado como: {usuario} ({nivel})")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    abas = ["Editor de Planilhas"]
    if nivel == "admin":
        abas += ["Dashboard", "Gerenciar Usuários"]

    tab = st.tabs(abas)

    with tab[0]:
        planilha_editor(usuario)

    if nivel == "admin":
        with tab[1]:
            painel_dashboard()
        with tab[2]:
            painel_administrador()
