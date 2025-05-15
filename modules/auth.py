import streamlit as st
from modules.data_handler import carregar_dados, salvar_dados

def verificar_login(usuario, senha):
    dados = carregar_dados()
    if usuario in dados["usuarios"] and dados["usuarios"][usuario]["senha"] == senha:
        dados["usuario_atual"] = {
            "id": usuario,
            "nome": usuario,
            "role": dados["usuarios"][usuario]["nivel"]
        }
        salvar_dados(dados)
        return True, dados["usuarios"][usuario]["nivel"]
    return False, None

def adicionar_ao_historico(usuario, acao):
    dados = carregar_dados()
    if usuario in dados["usuarios"]:
        if "historico" not in dados["usuarios"][usuario]:
            dados["usuarios"][usuario]["historico"] = []
        dados["usuarios"][usuario]["historico"].append({
            "acao": acao,
            "data": st.session_state.get("data_atual", "") or ""
        })
        salvar_dados(dados)

def login_screen():
    st.subheader("Login")
    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        if submit:
            sucesso, nivel = verificar_login(usuario, senha)
            if sucesso:
                st.session_state.usuario_logado = usuario
                st.session_state.nivel_acesso = nivel
                adicionar_ao_historico(usuario, "Login")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
