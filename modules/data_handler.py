import json
import os
from datetime import datetime
import streamlit as st

DADOS_FILE = "dados_usuarios.json"

def inicializar_dados():
    dados_iniciais = {
        "usuario_atual": {"id": None, "nome": None, "role": None},
        "usuarios": {
            "admin": {"senha": "admin123", "nivel": "admin", "historico": []},
            "usuario": {"senha": "usuario123", "nivel": "padrao", "historico": []}
        },
        "planilhas_editadas": [],
        "historico_downloads": []
    }

    if not os.path.exists(DADOS_FILE):
        with open(DADOS_FILE, "w", encoding="utf-8") as f:
            json.dump(dados_iniciais, f, indent=4)
        return dados_iniciais
    else:
        try:
            with open(DADOS_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
            modificado = False
            for chave in dados_iniciais:
                if chave not in dados:
                    dados[chave] = dados_iniciais[chave]
                    modificado = True
            if modificado:
                with open(DADOS_FILE, "w", encoding="utf-8") as f:
                    json.dump(dados, f, indent=4)
            return dados
        except:
            with open(DADOS_FILE, "w", encoding="utf-8") as f:
                json.dump(dados_iniciais, f, indent=4)
            return dados_iniciais

def carregar_dados():
    return inicializar_dados()

def salvar_dados(dados):
    try:
        with open(DADOS_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4)
        return True
    except:
        return False
