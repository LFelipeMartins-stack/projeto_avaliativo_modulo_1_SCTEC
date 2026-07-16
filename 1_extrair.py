"""
1_extrair.py
------------
Pipeline de Extração: Download robusto via gdown, Descompactação e Carga na Camada RAW.
"""

import os
import re
import zipfile
import pandas as pd
from pathlib import Path

# Importação do gdown para bypass do bloqueio do Google Drive
try:
    import gdown
except ImportError:
    print("[!] A biblioteca 'gdown' não está instalada.")
    print("[*] Instale-a rodando: pip install gdown")
    raise RuntimeError("Instale 'gdown' para prosseguir de forma segura.")

# Importações modulares do seu projeto
from config import (
    PASTA_DADOS,
    DRIVE_FILE_ID,
    ARQUIVOS,
    CSV_SEPARADOR,
    CSV_ENCODING,
    TAMANHO_BLOCO
)
from banco import conectar, executar, inserir_em_lote

# Mapeamento físico de colunas para garantir inserções exatas
MAPEAMENTO_COLUNAS = {
    "raw_viagem": {
        "id_viagem": "Identificador do processo de viagem",
        "num_proposta": "Número da Proposta (PCDP)",
        "situacao": "Situação da viagem",
        "viagem_urgente": "Viagem Urgente",
        "cod_orgao_superior": "Código do órgão superior",
        "nome_orgao_superior": "Nome do órgão superior",
        "cpf_viajante": "CPF viajante",
        "nome_viajante": "Nome do viajante",
        "cargo": "Cargo",
        "funcao": "Função",
        "data_inicio": "Data de início",
        "data_fim": "Data de fim",
        "destinos": "Destinos",
        "motivo": "Motivo",
        "valor_diarias": "Valor diárias",
        "valor_passagens": "Valor passagens",
        "valor_devolucao": "Valor devolução",
        "valor_outros_gastos": "Valor outros gastos"
    },
    "raw_passagem": {
        "id_viagem": "Identificador do processo de viagem",
        "meio_transporte": "Meio de transporte",
        "pais_origem_ida": "País - Origem ida",
        "uf_origem_ida": "UF - Origem ida",
        "cidade_origem_ida": "Cidade - Origem ida",
        "pais_destino_ida": "País - Destino ida",
        "uf_destino_ida": "UF - Destino ida",
        "cidade_destino_ida": "Cidade - Destino ida",
        "valor_passagem": "Valor da passagem",
        "taxa_servico": "Taxa de serviço",
        "data_emissao": "Data da emissão/compra",
        "dados_volta_passagem": "Hora da emissão/compra"
    },
    "raw_pagamento": {
        "id_viagem": "Identificador do processo de viagem",
        "num_proposta": "Número da Proposta (PCDP)",
        "nome_orgao_pagador": "Nome do órgão pagador",
        "nome_ug_pagadora": "Nome da UG pagadora",
        "tipo_pagamento": "Tipo de pagamento",
        "valor": "Valor"
    },
    "raw_trecho": {
        "id_viagem": "Identificador do processo de viagem",
        "sequencia_trecho": "Sequência do trecho",
        "origem_data": "Origem - Data",
        "origem_uf": "Origem - UF",
        "origem_cidade": "Origem - Cidade",
        "destino_data": "Destino - Data",
        "destino_uf": "Destino - UF",
        "destino_cidade": "Destino - Cidade",
        "meio_transporte": "Meio de transporte",
        "numero_diarias": "Número de diárias"
    }
}


def extrair_id_drive(valor: str) -> str:
    """Extrai o ID puro do arquivo, suportando URLs completas do Google Drive."""
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", valor)
    if match:
        return match.group(1)
    return valor.strip()


def extrair_zip(caminho_zip: Path, pasta_destino: Path):
    """Extrai o conteúdo do arquivo ZIP na pasta destino."""
    print(f"[*] Descompactando {caminho_zip.name}...")
    with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
        zip_ref.extractall(pasta_destino)
    print("[+] Arquivos descompactados com sucesso.")


def obter_indices_colunas(colunas_csv: list, dicionario_mapeamento: dict) -> list:
    """Mapeia dinamicamente a posição das colunas físicas com base nos cabeçalhos reais do CSV."""
    indices = []
    colunas_csv_limpas = [col.strip().lower() for col in colunas_csv]
    
    for col_banco, col_csv_ideal in dicionario_mapeamento.items():
        alvo = col_csv_ideal.strip().lower()
        try:
            # Busca correspondência exata ou por similaridade parcial
            idx = next(i for i, col in enumerate(colunas_csv_limpas) if col == alvo or alvo in col)
            indices.append((col_banco, idx))
        except StopIteration:
            indices.append((col_banco, None))
            
    return indices


def carregar_camada_raw():
    """Lê os CSVs em chunks e executa a carga na camada RAW garantindo idempotência."""
    conexao = conectar()
    
    try:
        for chave, meta in ARQUIVOS.items():
            tabela = meta["tabela_raw"]
            csv_nome = meta["csv"]
            caminho_csv = PASTA_DADOS / csv_nome
            
            if not caminho_csv.exists():
                raise FileNotFoundError(f"Arquivo CSV não encontrado em: {caminho_csv}")
                
            print(f"\n[*] Iniciando processamento da tabela: {tabela}")
            
            # Garantia de Idempotência: Limpeza prévia
            print(f"[-] Limpando dados históricos de {tabela}...")
            executar(conexao, f"TRUNCATE TABLE {tabela} CASCADE;")
            
            # Lê apenas a primeira linha para gerar o mapeamento dinâmico posicional das colunas
            temp_df = pd.read_csv(caminho_csv, sep=CSV_SEPARADOR, encoding=CSV_ENCODING, nrows=1)
            mapeamento = obter_indices_colunas(temp_df.columns.tolist(), MAPEAMENTO_COLUNAS[tabela])
            
            colunas_destino = [m[0] for m in mapeamento]
            indices_origem = [m[1] for m in mapeamento]
            
            # Configuração do comando INSERT SQL em lote
            colunas_str = ", ".join(colunas_destino)
            placeholders = ", ".join(["%s"] * len(colunas_destino))
            sql_insert = f"INSERT INTO {tabela} ({colunas_str}) VALUES ({placeholders})"
            
            # Leitura estruturada em blocos (chunks) para controle rígido de memória RAM
            chunks = pd.read_csv(
                caminho_csv,
                sep=CSV_SEPARADOR,
                encoding=CSV_ENCODING,
                chunksize=TAMANHO_BLOCO,
                dtype=str,
                header=0
            )
            
            bloco_num = 1
            for chunk in chunks:
                linhas_inserir = []
                for row in chunk.itertuples(index=False, name=None):
                    valores_linha = []
                    for idx in indices_origem:
                        if idx is not None and idx < len(row):
                            val = str(row[idx]).strip()
                            valores_linha.append(None if val.lower() in ("nan", "", "null", "sem informação") else val)
                        else:
                            valores_linha.append(None)
                    linhas_inserir.append(tuple(valores_linha))
                
                # Ingestão física em lote no Postgres (bulk insert performático)
                inserir_em_lote(conexao, sql_insert, linhas_inserir)
                print(f"[+] Bloco {bloco_num}: {len(linhas_inserir)} linhas persistidas na base.")
                bloco_num += 1
                
            print(f"[SUCCESS] Ingestão da tabela {tabela} concluída com sucesso!")
            
    except Exception as e:
        print(f"\n[FALHA NO PROCESSO RAW]: {e}")
        conexao.rollback()
        raise e
    finally:
        conexao.close()


def main():
    try:
        print("=== INICIANDO PIPELINE DE EXTRAÇÃO (CAMADA RAW) ===")
        
        # 1. Ajusta o ID do drive
        file_id = extrair_id_drive(DRIVE_FILE_ID)
        caminho_zip = PASTA_DADOS / "dados.zip"
        
        # Garante a existência física do diretório de armazenamento de dados
        PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        
        # 2. Executa download via gdown (by-pass automatizado de limites e avisos de vírus)
        print(f"[*] Solicitando download do arquivo Google Drive ID: {file_id}")
        gdown.download(id=file_id, output=str(caminho_zip), quiet=False)
        print(f"[+] Download concluído com sucesso: {caminho_zip.name}")
        
        # 3. Executa a descompactação física
        extrair_zip(caminho_zip, PASTA_DADOS)
        
        # 4. Processa a carga estruturada no Postgres
        carregar_camada_raw()
        
        print("\n=== PIPELINE DE EXTRAÇÃO CONCLUÍDO COM SUCESSO! ===")
        
    except Exception as e:
        print(f"\n[ERRO CRÍTICO NO PIPELINE]: {e}")


if __name__ == "__main__":
    main()