
import streamlit as st
import pandas as pd
import io
import csv
import zipfile
import re
import unicodedata
import os
from datetime import datetime
from modules.data_handler import carregar_dados, salvar_dados
from modules.auth import adicionar_ao_historico

def formatar_data(data_str):
    data_limpa = re.sub(r'\s*\(UTC-\d\)', '', str(data_str))
    try:
        data_obj = datetime.strptime(data_limpa, "%d/%m/%Y %H:%M:%S")
        return data_obj.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        try:
            data_obj = datetime.strptime(data_limpa, "%Y-%m-%d %H:%M:%S")
            return data_obj.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return data_limpa

def processar_coordenada(valor):
    if pd.isna(valor) or valor == "":
        return ""
    try:
        valor = float(valor)
        if abs(valor) > 1000:
            valor = valor / 1_000_000
        return f"{valor:.6f}"
    except ValueError:
        return str(valor)

def verificar_placa(texto):
    if not isinstance(texto, str):
        return False
    padrao_antigo = re.compile(r'^[A-Za-z]{3}[-]?[0-9]{4}$')
    padrao_novo = re.compile(r'^[A-Za-z]{3}[0-9][A-Za-z][0-9]{2}$')
    return padrao_antigo.match(texto) or padrao_novo.match(texto)

def formatar_placa(placa):
    placa = placa.upper().replace("-", "").strip()
    if re.match(r'^[A-Z]{3}[0-9]{4}$', placa):
        return placa[:3] + '-' + placa[3:]
    if re.match(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$', placa):
        return placa
    return placa

def registrar_edicao_planilha(usuario, nome_planilha):
    dados = carregar_dados()
    if "planilhas_editadas" not in dados:
        dados["planilhas_editadas"] = []
    dados["planilhas_editadas"].append({
        "data": datetime.now().isoformat(),
        "usuario": usuario,
        "planilha": nome_planilha
    })
    salvar_dados(dados)

def registrar_download_planilha(usuario, nome_planilha):
    dados = carregar_dados()
    if "historico_downloads" not in dados:
        dados["historico_downloads"] = []
    dados["historico_downloads"].append({
        "data": datetime.now().isoformat(),
        "usuario": usuario,
        "planilha": nome_planilha
    })
    salvar_dados(dados)

def processar_planilha(uploaded_file, codigo_empresa, usuario):
    df_raw = pd.read_excel(uploaded_file, dtype=str, header=None)

    placa_detectada = None
    for i in range(15):
        for val in df_raw.iloc[i].dropna().astype(str):
            if verificar_placa(val):
                placa_detectada = formatar_placa(val)
                break
        if placa_detectada:
            break

    header_row = None
    for idx, row in df_raw.iterrows():
        row_str = row.astype(str).str.lower()
        if row_str.str.contains("data").any() and row_str.str.contains("longitude").any():
            header_row = idx
            break

    if header_row is None:
        st.error("Cabeçalho com 'data' e 'longitude' não encontrado.")
        return None, None, 0

    df = pd.read_excel(uploaded_file, dtype=str, header=header_row)
    df = df.dropna(how="all")

    col_data = next((c for c in df.columns if "data" in str(c).lower()), None)
    col_lat = next((c for c in df.columns if "lat" in str(c).lower()), None)
    col_lon = next((c for c in df.columns if "lon" in str(c).lower()), None)

    if not all([col_data, col_lat, col_lon]):
        st.error("Colunas obrigatórias não foram encontradas na planilha.")
        return None, None, 0

    novo_df = pd.DataFrame(columns=['Placa', 'Data Original', 'Data Formatada', 'Latitude', 'Longitude', 'Código Empresa'])
    for _, row in df.iterrows():
        data = row.get(col_data, "")
        data_fmt = formatar_data(data)
        latitude = processar_coordenada(row.get(col_lat, ""))
        longitude = processar_coordenada(row.get(col_lon, ""))
        novo_df.loc[len(novo_df)] = [
            placa_detectada or "", data, data_fmt, latitude, longitude, codigo_empresa
        ]

    registrar_edicao_planilha(usuario, uploaded_file.name)
    adicionar_ao_historico(usuario, f"Editou a planilha {uploaded_file.name} com código da empresa {codigo_empresa}")
    return novo_df, ".xlsx", len(novo_df)

def planilha_editor(usuario):
    st.subheader("Editor de Planilhas")
    codigo_empresa = st.text_input("Código da empresa:")
    uploaded_files = st.file_uploader("Selecione os arquivos de planilha (xlsx, xls, csv)", type=["xlsx", "xls"], accept_multiple_files=True)

    if uploaded_files and codigo_empresa:
        if st.button("Processar Arquivos"):
            progresso = st.progress(0)
            resultados, arquivos_csv = [], []

            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    progresso.progress(i / len(uploaded_files))
                    novo_df, extensao, linhas_validas = processar_planilha(uploaded_file, codigo_empresa, usuario)
                    output = io.StringIO()
                    novo_df.to_csv(output, index=False, header=True, quoting=csv.QUOTE_MINIMAL)
                    nome_saida = uploaded_file.name.rsplit('.', 1)[0] + ".csv"
                    arquivos_csv.append({"nome": nome_saida, "conteudo": output.getvalue()})
                    resultados.append({"nome_original": uploaded_file.name, "nome_saida": nome_saida, "linhas_validas": linhas_validas})
                    st.write(f"### Pré-visualização: {uploaded_file.name}")
                    st.dataframe(novo_df.head(10))
                except Exception as e:
                    st.error(f"Erro ao processar {uploaded_file.name}: {e}")

            progresso.progress(1.0)
            if resultados:
                st.success(f"{len(resultados)} arquivos processados com sucesso.")
                st.dataframe(pd.DataFrame(resultados))
                for idx, arq in enumerate(arquivos_csv):
                    if st.download_button(f"Baixar {arq['nome']}", arq['conteudo'], arq['nome'], "text/csv", key=idx):
                        registrar_download_planilha(usuario, arq['nome'])
                if len(arquivos_csv) > 1:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                        for arq in arquivos_csv:
                            zip_file.writestr(arq['nome'], arq['conteudo'])
                    if st.download_button("Baixar tudo (ZIP)", zip_buffer.getvalue(), "planilhas.zip", "application/zip"):
                        for arq in arquivos_csv:
                            registrar_download_planilha(usuario, arq['nome'])
            else:
                st.warning("Nenhum arquivo foi processado com sucesso.")
