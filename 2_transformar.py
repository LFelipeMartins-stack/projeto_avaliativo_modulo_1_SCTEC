"""
2_transformar.py
----------------
Pipeline de Transformação (ETL) utilizando Pandas para processamento em memória
e PostgreSQL para carga final da camada Silver.
"""

import pandas as pd
import numpy as np
from banco import conectar, executar, inserir_em_lote

# ---------------------------------------------------------------------------
# Funções Auxiliares de Tratamento de Dados (Transform)
# ---------------------------------------------------------------------------

def limpar_decimal(serie: pd.Series) -> pd.Series:
    """
    Converte strings numéricas brasileiras para floats válidos.
    Exemplo: "1.272,97" -> 1272.97
    """
    if serie is None or serie.empty:
        return pd.Series(0.00, index=serie.index)
    
    # .str.lower() padroniza os textos para busca exata sem case=False
    s = serie.astype(str).str.strip().str.lower()
    s = s.str.replace(r'\.', '', regex=True)  # Remove ponto de milhar
    s = s.str.replace(',', '.', regex=False)  # Substitui vírgula decimal por ponto
    s = s.replace(['sem informação', 'nan', 'null', 'none', ''], '0.00')
    
    # Converte e garante que valores inválidos virem 0.00
    num = pd.to_numeric(s, errors="coerce").fillna(0.00)
    # Garante a regra de negócio do CHECK (valores >= 0)
    return num.clip(lower=0.00)


def limpar_data(serie: pd.Series) -> pd.Series:
    """Converte strings DD/MM/AAAA em strings padrão ISO YYYY-MM-DD ou None."""
    datas_dt = pd.to_datetime(serie, format="%d/%m/%Y", errors="coerce")
    return datas_dt.dt.strftime('%Y-%m-%d').where(datas_dt.notnull(), None)


def tratar_nulos_para_db(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante que NaNs, NaTs e floats invalidos do Pandas sejam convertidos 
    para o objeto None (que vira NULL nativamente no PostgreSQL).
    """
    # Convertemos o DF inteiro para o tipo genérico 'object'.
    # Isso impede que o Pandas force None a virar NaN em colunas numéricas ou de data.
    return df.astype(object).where(pd.notnull(df), None)

# ---------------------------------------------------------------------------
# Etapas do Pipeline (ETL)
# ---------------------------------------------------------------------------

def executar_etl_silver():
    conexao = conectar()
    
    try:
        # 1. EXTRACT: Extração dos dados das tabelas RAW para o Pandas
        print("[*] Extraindo dados da camada RAW...")
        df_raw_viagem = pd.read_sql_query("SELECT * FROM raw_viagem", conexao)
        df_raw_pagamento = pd.read_sql_query("SELECT * FROM raw_pagamento", conexao)
        df_raw_passagem = pd.read_sql_query("SELECT * FROM raw_passagem", conexao)
        df_raw_trecho = pd.read_sql_query("SELECT * FROM raw_trecho", conexao)
        
        # 2. TRANSFORM: Processamento da Tabela silver_viagem
        print("[*] Transformando silver_viagem...")
        df_silver_viagem = pd.DataFrame()
        
        # Chave Primária
        df_silver_viagem['id_viagem'] = df_raw_viagem['id_viagem'].astype(str).str.strip()
        df_silver_viagem.drop_duplicates(subset=['id_viagem'], keep='first', inplace=True)
        
        # Campos simples
        df_silver_viagem['num_proposta'] = df_raw_viagem['num_proposta']
        df_silver_viagem['situacao'] = df_raw_viagem['situacao']
        df_silver_viagem['viagem_urgente'] = df_raw_viagem['viagem_urgente']
        df_silver_viagem['cod_orgao_superior'] = df_raw_viagem['cod_orgao_superior']
        
        # Constraint NOT NULL resolvida programaticamente
        df_silver_viagem['nome_orgao_superior'] = df_raw_viagem['nome_orgao_superior'].fillna("NÃO INFORMADO")
        df_silver_viagem['nome_viajante'] = df_raw_viagem['nome_viajante']
        df_silver_viagem['cargo'] = df_raw_viagem['cargo']
        
        # Tratamento de Datas
        df_silver_viagem['data_inicio'] = limpar_data(df_raw_viagem['data_inicio'])
        df_silver_viagem['data_fim'] = limpar_data(df_raw_viagem['data_fim'])
        
        # Textos longos
        df_silver_viagem['destinos'] = df_raw_viagem['destinos']
        df_silver_viagem['motivo'] = df_raw_viagem['motivo']
        
        # Tratamento de Decimais com validação do CHECK >= 0
        df_silver_viagem['valor_diarias'] = limpar_decimal(df_raw_viagem['valor_diarias'])
        df_silver_viagem['valor_passagens'] = limpar_decimal(df_raw_viagem['valor_passagens'])
        df_silver_viagem['valor_devolucao'] = limpar_decimal(df_raw_viagem['valor_devolucao'])
        df_silver_viagem['valor_outros_gastos'] = limpar_decimal(df_raw_viagem['valor_outros_gastos'])
        
        # COLUNAS CALCULADAS
        # valor_total = (diarias + passagens + outros) - devolucao
        df_silver_viagem['valor_total'] = (
            df_silver_viagem['valor_diarias'] + 
            df_silver_viagem['valor_passagens'] + 
            df_silver_viagem['valor_outros_gastos'] - 
            df_silver_viagem['valor_devolucao']
        )
        
        # duracao_dias = data_fim - data_inicio
        data_ini_dt = pd.to_datetime(df_silver_viagem['data_inicio'], errors='coerce')
        data_fim_dt = pd.to_datetime(df_silver_viagem['data_fim'], errors='coerce')
        df_silver_viagem['duracao_dias'] = (data_fim_dt - data_ini_dt).dt.days
        
        # Ajuste final de tipos para o banco de dados
        df_silver_viagem = tratar_nulos_para_db(df_silver_viagem)
        
        # Conjunto de IDs válidos para validação de integridade referencial (FK) nas tabelas filhas
        viagens_validas = set(df_silver_viagem['id_viagem'].tolist())

        # ---------------------------------------------------------------------------
        # 3. TRANSFORM: Processamento da Tabela silver_pagamento
        # ---------------------------------------------------------------------------
        print("[*] Transformando silver_pagamento...")
        df_silver_pagamento = pd.DataFrame()
        df_silver_pagamento['id_viagem'] = df_raw_pagamento['id_viagem'].astype(str).str.strip()
        
        # Validação de integridade referencial (Foreign Key em memória)
        df_silver_pagamento = df_silver_pagamento[df_silver_pagamento['id_viagem'].isin(viagens_validas)].copy()
        
        # Mapeamento do restante dos campos baseando-se no índice original filtrado
        indices_filtrados = df_silver_pagamento.index
        df_silver_pagamento['num_proposta'] = df_raw_pagamento.loc[indices_filtrados, 'num_proposta']
        df_silver_pagamento['nome_orgao_pagador'] = df_raw_pagamento.loc[indices_filtrados, 'nome_orgao_pagador']
        df_silver_pagamento['nome_ug_pagadora'] = df_raw_pagamento.loc[indices_filtrados, 'nome_ug_pagadora']
        df_silver_pagamento['tipo_pagamento'] = df_raw_pagamento.loc[indices_filtrados, 'tipo_pagamento'].fillna("NÃO INFORMADO")
        df_silver_pagamento['valor'] = limpar_decimal(df_raw_pagamento.loc[indices_filtrados, 'valor'])
        
        df_silver_pagamento = tratar_nulos_para_db(df_silver_pagamento)

        # ---------------------------------------------------------------------------
        # 4. TRANSFORM: Processamento da Tabela silver_passagem
        # ---------------------------------------------------------------------------
        print("[*] Transformando silver_passagem...")
        df_silver_passagem = pd.DataFrame()
        df_silver_passagem['id_viagem'] = df_raw_passagem['id_viagem'].astype(str).str.strip()
        
        # Integridade referencial (FK)
        df_silver_passagem = df_silver_passagem[df_silver_passagem['id_viagem'].isin(viagens_validas)].copy()
        indices_filtrados = df_silver_passagem.index
        
        df_silver_passagem['meio_transporte'] = df_raw_passagem.loc[indices_filtrados, 'meio_transporte']
        df_silver_passagem['pais_origem_ida'] = df_raw_passagem.loc[indices_filtrados, 'pais_origem_ida']
        df_silver_passagem['uf_origem_ida'] = df_raw_passagem.loc[indices_filtrados, 'uf_origem_ida']
        df_silver_passagem['cidade_origem_ida'] = df_raw_passagem.loc[indices_filtrados, 'cidade_origem_ida']
        df_silver_passagem['pais_destino_ida'] = df_raw_passagem.loc[indices_filtrados, 'pais_destino_ida']
        df_silver_passagem['uf_destino_ida'] = df_raw_passagem.loc[indices_filtrados, 'uf_destino_ida']
        df_silver_passagem['cidade_destino_ida'] = df_raw_passagem.loc[indices_filtrados, 'cidade_destino_ida']
        df_silver_passagem['valor_passagem'] = limpar_decimal(df_raw_passagem.loc[indices_filtrados, 'valor_passagem'])
        df_silver_passagem['taxa_servico'] = limpar_decimal(df_raw_passagem.loc[indices_filtrados, 'taxa_servico'])
        df_silver_passagem['data_emissao'] = limpar_data(df_raw_passagem.loc[indices_filtrados, 'data_emissao'])
        
        df_silver_passagem = tratar_nulos_para_db(df_silver_passagem)

        # ---------------------------------------------------------------------------
        # 5. TRANSFORM: Processamento da Tabela silver_trecho
        # ---------------------------------------------------------------------------
        print("[*] Transformando silver_trecho...")
        df_silver_trecho = pd.DataFrame()
        df_silver_trecho['id_viagem'] = df_raw_trecho['id_viagem'].astype(str).str.strip()
        
        # Integridade referencial (FK)
        df_silver_trecho = df_silver_trecho[df_silver_trecho['id_viagem'].isin(viagens_validas)].copy()
        indices_filtrados = df_silver_trecho.index
        
        # Conversão explícita para inteiro seguro
        seq_limpa = pd.to_numeric(df_raw_trecho.loc[indices_filtrados, 'sequencia_trecho'], errors='coerce').fillna(1).astype(int)
        df_silver_trecho['sequencia_trecho'] = seq_limpa
        
        # Tratamento da constraint UNIQUE (id_viagem, sequencia_trecho)
        df_silver_trecho.drop_duplicates(subset=['id_viagem', 'sequencia_trecho'], keep='first', inplace=True)
        indices_finais = df_silver_trecho.index
        
        df_silver_trecho['origem_data'] = limpar_data(df_raw_trecho.loc[indices_finais, 'origem_data'])
        df_silver_trecho['origem_uf'] = df_raw_trecho.loc[indices_finais, 'origem_uf']
        df_silver_trecho['origem_cidade'] = df_raw_trecho.loc[indices_finais, 'origem_cidade']
        df_silver_trecho['destino_data'] = limpar_data(df_raw_trecho.loc[indices_finais, 'destino_data'])
        df_silver_trecho['destino_uf'] = df_raw_trecho.loc[indices_finais, 'destino_uf']
        df_silver_trecho['destino_cidade'] = df_raw_trecho.loc[indices_finais, 'destino_cidade']
        df_silver_trecho['meio_transporte'] = df_raw_trecho.loc[indices_finais, 'meio_transporte']
        df_silver_trecho['numero_diarias'] = limpar_decimal(df_raw_trecho.loc[indices_finais, 'numero_diarias'])
        
        df_silver_trecho = tratar_nulos_para_db(df_silver_trecho)

        # ---------------------------------------------------------------------------
        # 6. LOAD: Carga idempotente na Camada Silver do PostgreSQL
        # ---------------------------------------------------------------------------
        print("\n[-] Iniciando carga (LOAD) na base de dados...")
        
        # Limpeza prévia para garantir a idempotência
        executar(conexao, "TRUNCATE TABLE silver_trecho, silver_passagem, silver_pagamento, silver_viagem CASCADE;")
        
        # Carga sequencial estrita (Pai -> Filhos) respeitando as restrições físicas das Foreign Keys
        
        # Carga silver_viagem
        colunas_viagem = list(df_silver_viagem.columns)
        registros_viagem = [tuple(x) for x in df_silver_viagem.itertuples(index=False, name=None)]
        placeholders_viagem = ", ".join(["%s"] * len(colunas_viagem))
        sql_viagem = f"INSERT INTO silver_viagem ({', '.join(colunas_viagem)}) VALUES ({placeholders_viagem})"
        inserir_em_lote(conexao, sql_viagem, registros_viagem)
        print(f"[+] LOAD concluído: {len(registros_viagem)} linhas inseridas em silver_viagem.")
        
        # Carga silver_pagamento
        colunas_pagamento = list(df_silver_pagamento.columns)
        registros_pagamento = [tuple(x) for x in df_silver_pagamento.itertuples(index=False, name=None)]
        placeholders_pagamento = ", ".join(["%s"] * len(colunas_pagamento))
        sql_pagamento = f"INSERT INTO silver_pagamento ({', '.join(colunas_pagamento)}) VALUES ({placeholders_pagamento})"
        inserir_em_lote(conexao, sql_pagamento, registros_pagamento)
        print(f"[+] LOAD concluído: {len(registros_pagamento)} linhas inseridas em silver_pagamento.")
        
        # Carga silver_passagem
        colunas_passagem = list(df_silver_passagem.columns)
        registros_passagem = [tuple(x) for x in df_silver_passagem.itertuples(index=False, name=None)]
        placeholders_passagem = ", ".join(["%s"] * len(colunas_passagem))
        sql_passagem = f"INSERT INTO silver_passagem ({', '.join(colunas_passagem)}) VALUES ({placeholders_passagem})"
        inserir_em_lote(conexao, sql_passagem, registros_passagem)
        print(f"[+] LOAD concluído: {len(registros_passagem)} linhas inseridas em silver_passagem.")
        
        # Carga silver_trecho
        colunas_trecho = list(df_silver_trecho.columns)
        registros_trecho = [tuple(x) for x in df_silver_trecho.itertuples(index=False, name=None)]
        placeholders_trecho = ", ".join(["%s"] * len(colunas_trecho))
        sql_trecho = f"INSERT INTO silver_trecho ({', '.join(colunas_trecho)}) VALUES ({placeholders_trecho})"
        inserir_em_lote(conexao, sql_trecho, registros_trecho)
        print(f"[+] LOAD concluído: {len(registros_trecho)} linhas inseridas em silver_trecho.")
        
        print("\n=== PIPELINE ETL SILVER EXECUTADO COM SUCESSO! ===")
        
    except Exception as e:
        print(f"\n[ERRO CRÍTICO NO PIPELINE SILVER]: {e}")
        conexao.rollback()
        raise e
    finally:
        conexao.close()


if __name__ == "__main__":
    executar_etl_silver()