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

# =====================
# UTILITÁRIOS
# =====================

def formatar_data_series(series):
    return pd.to_datetime(series, errors='coerce', dayfirst=True).dt.strftime("%Y-%m-%d %H:%M")

def verificar_placas_series(series):
    padrao_antigo = r'^[A-Za-z]{3}-?[0-9]{4}$'
    padrao_novo = r'^[A-Za-z]{3}[0-9][A-Za-z0-9][0-9]{2}$'
    return series.str.upper().str.strip().str.match(padrao_antigo) | series.str.upper().str.strip().str.match(padrao_novo)

def formatar_placa(placa):
    placa = placa.upper().replace("-", "").strip()
    if re.match(r'^[A-Z]{3}[0-9]{4}$', placa):
        return placa[:3] + '-' + placa[3:]
    return placa

def extrair_placa_de_arquivo(nome):
    placas = re.findall(r'[A-Z]{3}[0-9][A-Z0-9][0-9]{2}', nome.upper())
    return formatar_placa(placas[0]) if placas else ""

def pontuar_coluna_data(col, df):
    nome = unicodedata.normalize('NFKD', str(col).lower()).encode('ASCII', 'ignore').decode('ASCII')
    score = 0
    if any(p in nome for p in ['evento', 'rastreamento', 'posicao', 'gps']):
        score += 5
    if any(p in nome for p in ['data', 'hora', 'dh']):
        score += 3
    if any(p in nome for p in ['chegada', 'entrega', 'fim', 'saida', 'retorno']):
        score -= 10
    amostra = df[col].astype(str).head(20)
    padrao_data = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4} \d{2}:\d{2}')
    qtd_validos = sum(bool(padrao_data.match(v)) for v in amostra)
    if len(amostra) > 0 and qtd_validos / len(amostra) >= 0.8:
        score += 10
    return score

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

# =====================
# PROCESSADOR
# =====================

def processar_planilha(uploaded_file, codigo_empresa, usuario):
    def formatar_data(data_str):
      data_limpa = str(data_str).strip()
   # Remove qualquer sufixo UTC ou () no final
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
            texto = str(valor).strip()

            # Decimal padrão
            if re.match(r'^-?\d+(?:[.,]\d+)?$', texto):
                valor = float(texto.replace(",", "."))
                if abs(valor) > 1000:
                    valor /= 1_000_000
                if -90 <= valor <= 90 or -180 <= valor <= 180:
                    return f"{valor:.6f}"

            # DMS - aceita vários tipos de aspas, espaçamentos e direções
            dms_match = re.search(
                r"(\d{1,3})[°º\s]*['′´ ]?(\d{1,2})['’′´ ]?(\d{1,2})[\"”″ ]*\s*(Norte|Sul|Leste|Oeste)?",
                texto, flags=re.IGNORECASE)

            if dms_match:
                graus = int(dms_match.group(1))
                minutos = int(dms_match.group(2))
                segundos = int(dms_match.group(3))
                direcao = (dms_match.group(4) or "").strip().lower()
                decimal = graus + minutos / 60 + segundos / 3600
            if direcao in ["sul", "oeste"]:
                    decimal *= -1
            return f"{decimal:.6f}"

        except:
            pass
        return ""

    def formatar_placa(placa):
        if not isinstance(placa, str): return ""
        placa = placa.upper().replace("-", "").strip()
        return placa[:3] + '-' + placa[3:] if re.match(r'^[A-Z]{3}[0-9]{4}$', placa) else placa

    # === Detectar número de abas e iterar
    try:
        xls = pd.ExcelFile(uploaded_file)
    except Exception:
        return None, "", 0

    placa_detectada = ""
    final_df = pd.DataFrame(columns=['A', 'B', 'C', 'D', 'E', 'F'])

    for sheet in xls.sheet_names:
        try:
# === Leitura inicial (sem header)
            df_raw = pd.read_excel(uploaded_file, sheet_name=0, dtype=str, header=None)
            df_raw.fillna('', inplace=True)

            # === Início da detecção da placa
            placa_detectada = ""

            # Procurar placa no nome do arquivo
            match_nome = re.search(r'[A-Z]{3}[0-9][A-Z0-9][0-9]{2}', uploaded_file.name.upper())
            if match_nome:
                placa_detectada = formatar_placa(match_nome.group())

            # Procurar nas primeiras 10 linhas da planilha
            if not placa_detectada:
                for i in range(min(10, len(df_raw))):
                    for val in df_raw.iloc[i]:
                        val = str(val)
                        match = re.search(r'[A-Z]{3}[0-9][A-Z0-9][0-9]{2}', val.upper())
                        if match:
                            placa_detectada = formatar_placa(match.group())
                            break
                    if placa_detectada:
                        break

            # Se ainda assim não encontrou, tentar buscar nos valores mesclados de colunas
            if not placa_detectada:
                try:
                    primeira_linha = df_raw.iloc[0].astype(str).tolist()
                    linha_completa = " ".join(primeira_linha)
                    match = re.search(r'[A-Z]{3}[0-9][A-Z0-9][0-9]{2}', linha_completa.upper())
                    if match:
                        placa_detectada = formatar_placa(match.group())
                except:
                    pass


            # Detectar header
            linha_cabecalho = None
            for i in range(min(30, len(df_raw))):
                linha = df_raw.iloc[i].astype(str).str.lower().tolist()
                if any("latitude" in v for v in linha) and any("longitude" in v for v in linha):
                    linha_cabecalho = i
                    break
                if any("data" in v or "hora" in v or "posição" in v for v in linha):
                    linha_cabecalho = i
            if linha_cabecalho is None:
                continue

            # Leitura real com header
            df = pd.read_excel(xls, sheet_name=sheet, header=linha_cabecalho, dtype=str)
            df.fillna('', inplace=True)

            # Detectar colunas
            col_lat = col_lon = col_data = None
            for col in df.columns:
                nome = unicodedata.normalize('NFKD', str(col).lower()).encode('ASCII', 'ignore').decode('ASCII')
                if not col_lat and 'lat' in nome:
                    col_lat = col
                if not col_lon and 'lon' in nome:
                    col_lon = col
                if not col_data and any(p in nome for p in ['data', 'hora', 'posicao']):
                    col_data = col

            if not (col_lat and col_lon and col_data):
                continue

            for _, row in df.iterrows():
                placa = formatar_placa(placa_detectada)
                data = formatar_data(row.get(col_data, ""))
                lat = processar_coordenada(row.get(col_lat, ""))
                lon = processar_coordenada(row.get(col_lon, ""))
                if data and lat and lon:
                    final_df.loc[len(final_df)] = [placa, data, data, lat, lon, codigo_empresa]
        except:
            continue

    registrar_edicao_planilha(usuario, uploaded_file.name)
    adicionar_ao_historico(usuario, f"Editou a planilha {uploaded_file.name} com código da empresa {codigo_empresa}")
    return final_df, ".csv", len(final_df)

# =====================
# STREAMLIT INTERFACE
# =====================

def planilha_editor(usuario):
    st.subheader("Editor de Planilhas")
    codigo_empresa = st.text_input("Código da empresa:")
    uploaded_files = st.file_uploader("Selecione os arquivos de planilha", type=["xlsx", "xls", "cvs"], accept_multiple_files=True)

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
