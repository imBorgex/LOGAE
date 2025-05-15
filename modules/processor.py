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
            data_obj = datetime.strptime(data_limpa, "%d/%m/%Y %H:%M:%S")
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
    """Processa a planilha carregada"""
    extensao = os.path.splitext(uploaded_file.name)[1].lower()
    if extensao == '.csv':
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8', dtype=str, decimal='.')
        except Exception:
            uploaded_file.seek(0)
            try:
                df = pd.read_csv(uploaded_file, encoding='latin1', dtype=str, decimal='.')
            except Exception:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='iso-8859-1', dtype=str, decimal='.')
    else:
        df = pd.read_excel(uploaded_file, dtype=str, sheet_name=0, decimal='.')
        
    novo_df = pd.DataFrame(columns=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I'])
    colunas_originais = df.columns.tolist()
    col_placa = None
    col_data_hora = None
    col_latitude = None
    col_longitude = None

    for col in colunas_originais:
       col_lower = str(col).lower()
       col_normalizada = unicodedata.normalize('NFKD', col_lower).encode('ASCII', 'ignore').decode('ASCII')
       if not col_placa:
           for i, valor in df[col].dropna().head(10).items():
               if verificar_placa(str(valor)):
                   col_placa = col
                   break
       if any(termo in col_normalizada for termo in ['data/hora - gps', 'data posicao', 'data hora', 'data-hora', 'datahora', 'data_gps', 'data_gps_posicao']):
           col_data_hora = col
       if any(termo in col_normalizada for termo in ['latitude', 'lat']):
           col_latitude = col
       if any(termo in col_normalizada for termo in ['longitude', 'lon', 'long']):
           col_longitude = col

    with st.expander("Ver colunas detectadas no arquivo:"):
        colunas_formatadas = ", ".join([f"`{col}`" for col in df.columns.tolist()])
        st.markdown(colunas_formatadas)


    for col in df.columns:
        col_str = str(col).lower()
        col_norm = unicodedata.normalize('NFKD', col_str).encode('ASCII', 'ignore').decode('ASCII')

        if not col_placa:
            for _, valor in df[col].dropna().head(10).items():
                if verificar_placa(str(valor)):
                    col_placa = col
                    break

        if any(p in col_norm for p in ["datahora", "data_hora", "data posicao", "data/hora", "data gps", "data-hora", "horario"]):
            col_data_hora = col
        if any(p in col_norm for p in ["latitude", "lat", "gps_lat", "coordenada x"]):
            col_latitude = col
        if any(p in col_norm for p in ["longitude", "lon", "long", "gps_lon", "coordenada y"]):
            col_longitude = col

    if not col_placa:
        st.warning(f"Nenhuma coluna de placa foi encontrada no arquivo {uploaded_file.name}.")
        placa_usuario = st.text_input(f"Digite a placa para adicionar ao arquivo {uploaded_file.name}:")
        if not placa_usuario or not verificar_placa(placa_usuario):
            st.error("Placa inválida. Por favor, insira uma placa válida.")
            return None, extensao, 0
        col_placa = "placa_usuario"
        df[col_placa] = placa_usuario

    linhas_validas = 0
    for _, row in df.iterrows():
        placa = str(row[col_placa]) if col_placa in row else ""
        if not verificar_placa(placa):
            continue
        placa_formatada = formatar_placa(placa)
        data_formatada = ""
        if col_data_hora and col_data_hora in row:
            data_raw = row[col_data_hora]
            data_formatada = formatar_data(data_raw) if data_raw else ""
        latitude = processar_coordenada(row[col_latitude]) if col_latitude and col_latitude in row else ""
        longitude = processar_coordenada(row[col_longitude]) if col_longitude and col_longitude in row else ""

        novo_df.loc[linhas_validas] = [
            placa_formatada,
            data_formatada,
            data_formatada,
            "",
            "",
            latitude,
            longitude,
            codigo_empresa,
            0
        ]
        linhas_validas += 1

    registrar_edicao_planilha(usuario, uploaded_file.name)
    adicionar_ao_historico(usuario, f"Editou a planilha {uploaded_file.name} com código da empresa {codigo_empresa}")
    return novo_df, extensao, linhas_validas

def planilha_editor(usuario):
    st.subheader("Editor de Planilhas")
    codigo_empresa = st.text_input("Código da empresa:")
    uploaded_files = st.file_uploader("Selecione os arquivos de planilha (xlsx, xls, csv)", type=["xlsx", "xls", "csv"], accept_multiple_files=True)

    if uploaded_files and codigo_empresa:
        if st.button("Processar Arquivos"):
            progresso = st.progress(0)
            resultados, arquivos_csv = [], []

            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    progresso.progress(i / len(uploaded_files))
                    novo_df, extensao, linhas_validas = processar_planilha(uploaded_file, codigo_empresa, usuario)
                    output = io.StringIO()
                    novo_df.to_csv(output, index=False, header=False, quoting=csv.QUOTE_MINIMAL)
                    nome_saida = uploaded_file.name.rsplit('.', 1)[0] + ".csv"
                    arquivos_csv.append({"nome": nome_saida, "conteudo": output.getvalue()})
                    resultados.append({"nome_original": uploaded_file.name, "nome_saida": nome_saida, "linhas_validas": linhas_validas})
                    st.write(f"### Pré-visualização: {uploaded_file.name}")
                    st.dataframe(novo_df.head(10))
                except Exception as e:
                    st.error(f"Erro ao processar {uploaded_file.name}")

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
