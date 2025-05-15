import streamlit as st
from modules.data_handler import carregar_dados, salvar_dados
import pandas as pd

def painel_administrador():
    st.subheader("Gerenciar Usuários")

    st.write("### Adicionar Novo Usuário")
    with st.form("add_user"):
        col1, col2, col3 = st.columns(3)
        with col1: novo_usuario = st.text_input("Usuário")
        with col2: nova_senha = st.text_input("Senha", type="password")
        with col3: nivel = st.selectbox("Nível", ["padrao", "admin"])
        if st.form_submit_button("Adicionar"):
            dados = carregar_dados()
            if novo_usuario in dados["usuarios"]:
                st.warning("Usuário já existe.")
            else:
                dados["usuarios"][novo_usuario] = {"senha": nova_senha, "nivel": nivel, "historico": []}
                if salvar_dados(dados): st.success("Usuário adicionado com sucesso.")

    st.write("### Usuários Cadastrados")
    dados = carregar_dados()
    usuarios = dados.get("usuarios", {})
    tabela = [{"Usuário": u, "Nível": v["nivel"], "Ações": len(v.get("historico", []))} for u, v in usuarios.items()]
    st.dataframe(tabela)

    selecionado = st.selectbox("Editar ou Remover", ["-"] + list(usuarios.keys()))
    if selecionado != "-":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Remover Usuário"):
                if selecionado == "admin":
                    st.warning("Não é permitido remover o admin.")
                else:
                    del dados["usuarios"][selecionado]
                    salvar_dados(dados)
                    st.success("Usuário removido.")
                    st.rerun()
        with col2:
            with st.form("editar_form"):
                nova_senha = st.text_input("Nova Senha", type="password")
                novo_nivel = st.selectbox("Novo Nível", ["padrao", "admin"], index=["padrao", "admin"].index(usuarios[selecionado]["nivel"]))
                if st.form_submit_button("Salvar Alteracoes"):
                    if nova_senha:
                        dados["usuarios"][selecionado]["senha"] = nova_senha
                    dados["usuarios"][selecionado]["nivel"] = novo_nivel
                    salvar_dados(dados)
                    st.success("Usuário atualizado.")
                    st.rerun()

        st.write(f"### Histórico de Ações: {selecionado}")
        historico = usuarios[selecionado].get("historico", [])
        historico_formatado = []
        for item in historico:
            if isinstance(item, dict) and "acao" in item and "data" in item:
                historico_formatado.append(item)
            elif isinstance(item, str):
                partes = item.split(" - ", 1)
                if len(partes) == 2:
                    historico_formatado.append({"data": partes[0], "acao": partes[1]})
        if historico_formatado:
            df_hist = pd.DataFrame(historico_formatado)
            df_hist["data"] = df_hist["data"].astype(str)
            df_hist["acao"] = df_hist["acao"].astype(str)
            df_hist = df_hist.sort_values("data", ascending=False)
            df_hist = df_hist[["acao", "data"]]
            st.dataframe(df_hist)
        else:
            st.info("Nenhum histórico disponível para este usuário.")
