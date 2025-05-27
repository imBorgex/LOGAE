import streamlit as st
import pandas as pd
import io
import csv
import zipfile
import re
import unicodedata
from datetime import datetime
from modules.data_handler import carregar_dados, salvar_dados
from modules.auth import adicionar_ao_historico

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
    def formatar_data(data_str):
        data_limpa = str(data_str).strip()
        data_limpa = re.sub(r'\s*\(UTC.*?\)', '', data_limpa)
        data_limpa = re.sub(r'\(.*?\)', '', data_limpa).strip()
        formatos = [
            "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
            "%d-%m-%Y %H:%M", "%d/%m/%y %H:%M"
        ]
        for fmt in formatos:
            try:
                return datetime.strptime(data_limpa, fmt).strftime("%Y-%m-%d %H:%M")
            except:
                continue
        return ""

    def processar_coordenada(valor):
        try:
            texto = str(valor).strip().replace(",", ".")
            if re.match(r'^-?\d+(?:[.,]\d+)?$', texto):
                valor = float(texto)
                if abs(valor) > 1000:
                    valor /= 1_000000
                if -90 <= valor <= 90 or -180 <= valor <= 180:
                    return f"{valor:.6f}"
            return texto
        except:
            return str(valor)

    def formatar_placa(placa):
        if not isinstance(placa, str): return ""
        placa = placa.upper().replace("-", "").strip()
        return placa[:3] + '-' + placa[3:] if re.match(r'^[A-Z]{3}[0-9]{4}$', placa) else placa

    try:
        extensao = uploaded_file.name.lower().split('.')[-1]
        if extensao == "csv":
            try:
                df_raw = pd.read_csv(uploaded_file, dtype=str, header=None, sep=";", encoding="utf-8", engine="python")
            except:
                uploaded_file.seek(0)
                df_raw = pd.read_csv(uploaded_file, dtype=str, header=None, sep=";", encoding="latin1", engine="python")
        else:
            xls = pd.ExcelFile(uploaded_file)
            df_raw = pd.read_excel(xls, sheet_name=0, dtype=str, header=None)
        df_raw.fillna('', inplace=True)
    except Exception as e:
        st.error(f"Erro ao ler {uploaded_file.name}: {e}")
        return None, "", 0

    linha_cabecalho = None
    for i in range(min(30, len(df_raw))):
        linha = df_raw.iloc[i].astype(str).str.lower().tolist()
        if any("latitude" in v for v in linha) and any("longitude" in v for v in linha):
            linha_cabecalho = i
            break
        if any("data" in v or "hora" in v or "posição" in v for v in linha):
            linha_cabecalho = i

    if linha_cabecalho is None:
        st.warning(f"🔍 Cabeçalho não encontrado automaticamente no arquivo: **{uploaded_file.name}**")
        linha_cabecalho = st.number_input(f"Informe a linha do cabeçalho (0 a {len(df_raw)-1}) para {uploaded_file.name}", min_value=0, max_value=len(df_raw)-1, value=0)

    try:
        if extensao == "csv":
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, dtype=str, header=linha_cabecalho, sep=";", encoding="utf-8", engine="python")
            except:
                uploaded_file.seek(0)
                try:
                    df = pd.read_csv(uploaded_file, dtype=str, header=linha_cabecalho, sep=";", encoding="latin1", engine="python")
                except:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, dtype=str, header=linha_cabecalho, sep=";", encoding="iso-8859-1", engine="python")
        else:
            df = pd.read_excel(xls, sheet_name=0, header=linha_cabecalho, dtype=str)
        df.fillna('', inplace=True)
    except Exception as e:
        st.error(f"Erro ao carregar conteúdo de {uploaded_file.name}: {e}")
        return None, "", 0

    colunas = list(df.columns)

    col_lat = next((c for c in colunas if 'lat' in str(c).lower()), None)
    col_lon = next((c for c in colunas if 'lon' in str(c).lower()), None)
    col_data = next((c for c in colunas if any(k in str(c).lower() for k in ['data', 'hora', 'posicao'])), None)

    if not (col_lat and col_lon and col_data):
        st.warning(f"⚠️ Não foram detectadas colunas automaticamente para: **{uploaded_file.name}**")
        col_data = st.selectbox(f"Selecionar coluna de Data/Hora - {uploaded_file.name}", colunas)
        col_lat = st.selectbox(f"Selecionar coluna de Latitude - {uploaded_file.name}", colunas)
        col_lon = st.selectbox(f"Selecionar coluna de Longitude - {uploaded_file.name}", colunas)

    placa_detectada = ""
    match_nome = re.search(r'[A-Z]{3}[0-9][A-Z0-9][0-9]{2}', uploaded_file.name.upper())
    if match_nome:
        placa_detectada = formatar_placa(match_nome.group())

    final_df = pd.DataFrame(columns=['A', 'B', 'C', 'D', 'E', 'F'])

    for _, row in df.iterrows():
        placa = formatar_placa(placa_detectada)
        data = formatar_data(row.get(col_data, ""))
        lat = processar_coordenada(row.get(col_lat, ""))
        lon = processar_coordenada(row.get(col_lon, ""))
        if data and lat and lon:
            final_df.loc[len(final_df)] = [placa, data, data, lat, lon, codigo_empresa]

    registrar_edicao_planilha(usuario, uploaded_file.name)
    adicionar_ao_historico(usuario, f"Editou a planilha {uploaded_file.name} com código da empresa {codigo_empresa}")
    return final_df, ".csv", len(final_df)

def planilha_editor(usuario):
    st.subheader("Editor de Planilhas")
    codigo_empresa = st.text_input("Código da empresa:")
    uploaded_files = st.file_uploader("Selecione os arquivos de planilha", type=["xlsx", "xls", "csv"], accept_multiple_files=True)

    if uploaded_files and codigo_empresa:
        if st.button("Processar Arquivos"):
            progresso = st.progress(0)
            resultados, arquivos_csv = [], []

            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    progresso.progress(i / len(uploaded_files))
                    novo_df, extensao, linhas_validas = processar_planilha(uploaded_file, codigo_empresa, usuario)
                    if novo_df is None:
                        continue
                    output = io.StringIO()
                    novo_df.to_csv(output, index=False, header=False, sep=";", quoting=csv.QUOTE_MINIMAL)
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
