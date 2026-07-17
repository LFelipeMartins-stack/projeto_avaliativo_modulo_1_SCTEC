"""
gerar_notebook.py
-----------------
Gera programaticamente o arquivo '3_analise.ipynb' completo com as células de 
Markdown, códigos de resolução de perguntas de negócio via Pandas e persistência da Camada Gold.
"""

import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 🏆 Projeto Final - Camada Gold: Análise e Visualização\n",
    "**Curso:** Análise de Dados com Python - SCtec  \n",
    "**Objetivo:** Responder às perguntas estratégicas de negócio utilizando os dados refinados da camada **Silver**, gerar visualizações analíticas de alta fidelidade e persistir tabelas agregadas na camada **Gold** do PostgreSQL.\n",
    "\n",
    "---\n",
    "### 1. Configuração do Ambiente e Extração"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "import warnings\n",
    "from banco import conectar, executar, inserir_em_lote\n",
    "\n",
    "# Desativa os avisos de conexão legada do Pandas com o psycopg2\n",
    "warnings.filterwarnings('ignore')\n",
    "\n",
    "# Configuração estética dos gráficos\n",
    "sns.set_theme(style=\"whitegrid\")\n",
    "plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12, 'figure.titlesize': 16})\n",
    "\n",
    "# Conecta ao PostgreSQL e extrai os dados refinados da Camada Silver\n",
    "conexao = conectar()\n",
    "df_viagem = pd.read_sql_query(\"SELECT * FROM silver_viagem\", conexao)\n",
    "df_pagamento = pd.read_sql_query(\"SELECT * FROM silver_pagamento\", conexao)\n",
    "df_passagem = pd.read_sql_query(\"SELECT * FROM silver_passagem\", conexao)\n",
    "df_trecho = pd.read_sql_query(\"SELECT * FROM silver_trecho\", conexao)\n",
    "conexao.close()\n",
    "\n",
    "print(f\"[*] Dados carregados com sucesso!\")\n",
    "print(f\"  • Viagens: {len(df_viagem):,}\")\n",
    "print(f\"  • Pagamentos: {len(df_pagamento):,}\")\n",
    "print(f\"  • Passagens: {len(df_passagem):,}\")\n",
    "print(f\"  • Trechos: {len(df_trecho):,}\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "### 💼 2. Resolução das Perguntas de Negócio"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "#### **P1. Quais são os 5 órgãos com maior custo total?**"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Agregação e ordenação dos custos por órgão\n",
    "q1 = df_viagem.groupby('nome_orgao_superior')['valor_total'].sum().reset_index()\n",
    "q1 = q1.sort_values(by='valor_total', ascending=False).head(5)\n",
    "\n",
    "# Exibição formatada\n",
    "print(\"=== OS 5 ÓRGÃOS COM MAIOR CUSTO TOTAL ===\")\n",
    "for idx, row in enumerate(q1.itertuples(), 1):\n",
    "    print(f\"{idx}. {row.nome_orgao_superior:<50} | R$ {row.valor_total:,.2f}\")\n",
    "\n",
    "# Plotagem do gráfico\n",
    "plt.figure(figsize=(10, 5))\n",
    "ax = sns.barplot(x=q1['valor_total'] / 1_000_000, y=q1['nome_orgao_superior'], palette='Blues_r')\n",
    "for container in ax.containers:\n",
    "    ax.bar_label(container, fmt='R$ %.1fM', padding=5)\n",
    "plt.title(\"Top 5 Órgãos Superiores com Maior Gasto Acumulado (2025)\")\n",
    "plt.xlabel(\"Custo Total (Milhões de R$)\")\n",
    "plt.ylabel(\"\")\n",
    "plt.tight_layout()\n",
    "plt.savefig(\"gold_p1_custo_orgao.png\", dpi=300)\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "#### **P2. Quais são os 3 destinos com maior custo médio por viagem?**"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Filtra destinos válidos, agrupa e calcula a média\n",
    "q2 = df_viagem[df_viagem['destinos'].notnull()].groupby('destinos')['valor_total'].agg(['mean', 'count']).reset_index()\n",
    "q2 = q2.sort_values(by='mean', ascending=False).head(3)\n",
    "\n",
    "print(\"=== TOP 3 DESTINOS COM MAIOR CUSTO MÉDIO ===\")\n",
    "for idx, row in enumerate(q2.itertuples(), 1):\n",
    "    print(f\"{idx}. Destino: {row.destinos:<50} | Custo Médio: R$ {row.mean:,.2f} ({row.count} viagens)\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "#### **P3. Qual é a viagem de maior duração e seu custo total?**"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Filtra durações válidas e localiza a viagem mais longa\n",
    "df_duracao_valida = df_viagem[df_viagem['duracao_dias'].notnull()]\n",
    "q3 = df_duracao_valida.sort_values(by='duracao_dias', ascending=False).iloc[0]\n",
    "\n",
    "print(\"=== VIAGEM DE MAIOR DURAÇÃO REGISTRADA ===\")\n",
    "print(f\"• ID da Viagem:  {q3['id_viagem']}\")\n",
    "print(f\"• Viajante:      {q3['nome_viajante']}\")\n",
    "print(f\"• Órgão:         {q3['nome_orgao_superior']}\")\n",
    "print(f\"• Destino:       {q3['destinos']}\")\n",
    "print(f\"• Período:       {q3['data_inicio']} até {q3['data_fim']}\")\n",
    "print(f\"• Duração total: {q3['duracao_dias']} dias\")\n",
    "print(f\"• Custo total:   R$ {q3['valor_total']:,.2f}\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "#### **P4. Qual o tipo de pagamento com maior valor médio?**"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Agrupamento e média por tipo de pagamento\n",
    "q4 = df_pagamento.groupby('tipo_pagamento')['valor'].mean().reset_index()\n",
    "q4 = q4.sort_values(by='valor', ascending=False).head(1).iloc[0]\n",
    "\n",
    "print(\"=== TIPO DE PAGAMENTO COM MAIOR VALOR MÉDIO ===\")\n",
    "print(f\"• Tipo de Pagamento: {q4['tipo_pagamento']}\")\n",
    "print(f\"• Valor Médio:       R$ {q4['valor']:,.2f}\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "#### **P5. Qual o meio de transporte mais usado nos trechos?**"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Filtra dados válidos de trecho e calcula a contagem de ocorrências\n",
    "df_transporte_valido = df_trecho[~df_trecho['meio_transporte'].isin([None, 'Sem informação', ''])]\n",
    "q5 = df_transporte_valido['meio_transporte'].value_counts().reset_index()\n",
    "q5.columns = ['meio_transporte', 'quantidade']\n",
    "\n",
    "print(\"=== MEIOS DE TRANSPORTE UTILIZADOS NOS TRECHOS ===\")\n",
    "for idx, row in enumerate(q5.itertuples(), 1):\n",
    "    print(f\"{idx}. {row.meio_transporte:<20} | {row.quantidade:,} trechos\")\n",
    "\n",
    "# Plotagem do gráfico de pizza/donut\n",
    "plt.figure(figsize=(6, 6))\n",
    "plt.pie(\n",
    "    q5['quantidade'], \n",
    "    labels=q5['meio_transporte'], \n",
    "    autopct='%1.1f%%', \n",
    "    startangle=90, \n",
    "    colors=['#2b5c8f', '#4682b4', '#b0c4de', '#d3d3d3'],\n",
    "    wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}\n",
    ")\n",
    "circulo_centro = plt.Circle((0,0), 0.60, fc='white')\n",
    "plt.gcf().gca().add_artist(circulo_centro)\n",
    "plt.title(\"Distribuição dos Meios de Transporte nos Trechos\")\n",
    "plt.tight_layout()\n",
    "plt.savefig(\"gold_p5_meio_transporte.png\", dpi=300)\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "#### **P6. Qual UF de destino aparece em mais trechos?**"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Filtra UFs válidas e realiza a contagem\n",
    "df_uf_valida = df_trecho[~df_trecho['destino_uf'].isin([None, 'Sem informação', ''])]\n",
    "q6 = df_uf_valida['destino_uf'].value_counts().reset_index()\n",
    "q6.columns = ['uf_destino', 'total_trechos']\n",
    "top_uf = q6.iloc[0]\n",
    "\n",
    "print(\"=== UF DE DESTINO MAIS FREQUENTE NOS TRECHOS ===\")\n",
    "print(f\"• UF de Destino: {top_uf['uf_destino']}\")\n",
    "print(f\"• Total de Trechos Ocorridos: {top_uf['total_trechos']:,} ocorrências\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "#### **P7. Qual órgão pagou mais no total?**"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Agrupamento dos gastos da tabela de pagamentos por órgão pagador\n",
    "df_pagador_valido = df_pagamento[~df_pagamento['nome_orgao_pagador'].isin([None, 'Sem informação', ''])]\n",
    "q7 = df_pagador_valido.groupby('nome_orgao_pagador')['valor'].sum().reset_index()\n",
    "q7 = q7.sort_values(by='valor', ascending=False).iloc[0]\n",
    "\n",
    "print(\"=== ÓRGÃO COM MAIOR GASTO TOTAL EM PAGAMENTOS ===\")\n",
    "print(f\"• Órgão Pagador:   {q7['nome_orgao_pagador']}\")\n",
    "print(f\"• Total Executado: R$ {q7['valor']:,.2f}\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "### 🏛️ 3. Camada Gold Agregada (Persistência de Dados)\n",
    "\n",
    "Nesta etapa final, consolidamos uma tabela agregada na Camada Gold do PostgreSQL (`gold_resumo_orgaos`). Essa tabela servirá como fonte de dados limpa e otimizada para futuras ferramentas de visualização executiva (como Power BI)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "print(\"[*] Criando a tabela agregada da camada Gold...\")\n",
    "\n",
    "# 1. Processamento da Agregação no Pandas\n",
    "df_gold_agregada = df_viagem.groupby('nome_orgao_superior').agg(\n",
    "    total_viagens=('id_viagem', 'count'),\n",
    "    custo_total=('valor_total', 'sum'),\n",
    "    custo_medio=('valor_total', 'mean'),\n",
    "    duracao_media_dias=('duracao_dias', 'mean')\n",
    ").reset_index()\n",
    "\n",
    "# Arredonda as colunas decimais para manter o padrão monetário/numérico limpo\n",
    "df_gold_agregada['custo_medio'] = df_gold_agregada['custo_medio'].round(2)\n",
    "df_gold_agregada['duracao_media_dias'] = df_gold_agregada['duracao_media_dias'].round(1)\n",
    "\n",
    "# Substitui possíveis valores nulos remanescentes de cálculos matemáticos por valores seguros\n",
    "df_gold_agregada = df_gold_agregada.where(pd.notnull(df_gold_agregada), None)\n",
    "\n",
    "# 2. Gravação Física da Tabela no Banco de Dados (PostgreSQL)\n",
    "conexao = conectar()\n",
    "\n",
    "# SQL para recriação limpa da tabela\n",
    "sql_ddl = \"\"\"\n",
    "DROP TABLE IF EXISTS gold_resumo_orgaos CASCADE;\n",
    "CREATE TABLE gold_resumo_orgaos (\n",
    "    nome_orgao_superior VARCHAR(255) PRIMARY KEY,\n",
    "    total_viagens INT,\n",
    "    custo_total DECIMAL(14,2),\n",
    "    custo_medio DECIMAL(12,2),\n",
    "    duracao_media_dias DECIMAL(5,1)\n",
    ");\n",
    "\"\"\"\n",
    "executar(conexao, sql_ddl)\n",
    "\n",
    "# Gravação das linhas agregadas via INSERT em lote\n",
    "colunas = ['nome_orgao_superior', 'total_viagens', 'custo_total', 'custo_medio', 'duracao_media_dias']\n",
    "placeholders = \", \".join([\"%s\"] * len(colunas))\n",
    "sql_insert = f\"INSERT INTO gold_resumo_orgaos ({', '.join(colunas)}) VALUES ({placeholders})\"\n",
    "\n",
    "registros = [tuple(x) for x in df_gold_agregada.itertuples(index=False, name=None)]\n",
    "inserir_em_lote(conexao, sql_insert, registros)\n",
    "conexao.close()\n",
    "\n",
    "print(f\"[SUCCESS] Tabela agregada 'gold_resumo_orgaos' gravada com sucesso!\")\n",
    "print(f\"  • Total de {len(df_gold_agregada)} registros de órgãos persistidos na camada Gold.\")"
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}

# Escreve o JSON estruturado no arquivo .ipynb
with open("3_analise.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print("\n[SUCCESS] O arquivo '3_analise.ipynb' foi gerado com sucesso na pasta do seu projeto!")
print("[*] Agora você pode abri-lo diretamente no VS Code e executá-lo.")