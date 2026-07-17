"""
gerar_notebook.py
-----------------
Gera programaticamente o arquivo '3_analise.ipynb' completo com as células de 
Markdown, códigos de resolução de perguntas de negócio, o Dashboard Interativo 
Tema Escuro (Estilo Power BI) e a gravação da Camada Gold agregada no PostgreSQL.
"""

import json
import os

filename = "3_analise.ipynb"
target_dir = "/home/flip/Downloads/Projeto_final_SCTEC/"

notebook_data = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 🏆 Projeto Final - Camada Gold: Análise, Visualização e Dashboard\n",
    "**Curso:** Análise de Dados com Python - SCtec  \n",
    "**Aluno:** L. Felipe Martins  \n",
    "\n",
    "Este Jupyter Notebook consolida a **Fase 3 (Camada Gold)** da nossa arquitetura de dados. \n",
    "Aqui realizamos:\n",
    "1. Resolução das **7 Perguntas de Negócio** com exibições textuais e gráficas estáticas e defensivas.\n",
    "2. Um **Dashboard Interativo Integrado (Tema Escuro - Estilo Power BI)** usando Plotly e `ipywidgets` para análise em tempo real.\n",
    "3. Persistência da tabela física agregada `gold_resumo_orgaos` no PostgreSQL com confirmação transacional (`commit`).\n",
    "4. Validação final lendo os dados de volta do banco de dados.\n",
    "\n",
    "---\n",
    "### ⚙️ 1. Gerenciamento Automatizado de Dependências e Carga de Dados"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import sys\n",
    "import subprocess\n",
    "\n",
    "# Lista de dependências críticas para o ambiente interativo do Jupyter\n",
    "dependencias = [\"plotly\", \"ipywidgets\", \"nbformat\"]\n",
    "instalou = False\n",
    "\n",
    "for lib in dependencias:\n",
    "    try:\n",
    "        __import__(lib)\n",
    "    except ImportError:\n",
    "        print(f\"[*] Instalação automática da biblioteca ausente: {lib}...\")\n",
    "        subprocess.check_call([\n",
    "            sys.executable, \"-m\", \"pip\", \"install\", lib, \"--break-system-packages\"\n",
    "        ])\n",
    "        instalou = True\n",
    "\n",
    "if instalou:\n",
    "    print(\"[SUCCESS] Dependências instaladas! Por favor, reinicie o Kernel do Jupyter para carregar as alterações.\")\n",
    "else:\n",
    "    print(\"[+] Todas as dependências necessárias estão presentes no ambiente!\")\n",
    "\n",
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "import plotly.express as px\n",
    "import plotly.graph_objects as go\n",
    "from plotly.subplots import make_subplots\n",
    "import ipywidgets as widgets\n",
    "from ipywidgets import interact\n",
    "import warnings\n",
    "from banco import conectar, executar, inserir_em_lote\n",
    "\n",
    "warnings.filterwarnings('ignore')\n",
    "\n",
    "# Configurações estéticas para os gráficos estáticos do Matplotlib\n",
    "sns.set_theme(style=\"whitegrid\")\n",
    "plt.rcParams.update({\n",
    "    'font.size': 11,\n",
    "    'axes.labelsize': 12,\n",
    "    'figure.titlesize': 16,\n",
    "    'text.color': 'black',\n",
    "    'axes.labelcolor': 'black',\n",
    "    'xtick.color': 'black',\n",
    "    'ytick.color': 'black'\n",
    "})\n",
    "\n",
    "# Conexão com o PostgreSQL e carga dos dados refinados\n",
    "conexao = conectar()\n",
    "df_viagem = pd.read_sql_query(\"SELECT * FROM silver_viagem\", conexao)\n",
    "df_pagamento = pd.read_sql_query(\"SELECT * FROM silver_pagamento\", conexao)\n",
    "df_passagem = pd.read_sql_query(\"SELECT * FROM silver_passagem\", conexao)\n",
    "df_trecho = pd.read_sql_query(\"SELECT * FROM silver_trecho\", conexao)\n",
    "conexao.close()\n",
    "\n",
    "print(\"\\n[*] Dados da Camada Silver carregados com sucesso:\")\n",
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
    "q1 = df_viagem.groupby('nome_orgao_superior')['valor_total'].sum().reset_index()\n",
    "q1 = q1.sort_values(by='valor_total', ascending=False).head(5)\n",
    "\n",
    "print(\"=== P1: OS 5 ÓRGÃOS COM MAIOR CUSTO TOTAL ===\")\n",
    "for idx, row in enumerate(q1.itertuples(), 1):\n",
    "    print(f\"{idx}. {row.nome_orgao_superior:<50} | R$ {row.valor_total:,.2f}\")\n",
    "\n",
    "plt.figure(figsize=(10, 4))\n",
    "ax = sns.barplot(\n",
    "    x=q1['valor_total'] / 1_000_000, \n",
    "    y=q1['nome_orgao_superior'], \n",
    "    palette='Blues_r', \n",
    "    hue=q1['nome_orgao_superior'], \n",
    "    legend=False\n",
    ")\n",
    "for container in ax.containers:\n",
    "    ax.bar_label(container, fmt='R$ %.1fM', padding=5)\n",
    "plt.title(\"Top 5 Órgãos Superiores por Gasto Acumulado (2025)\")\n",
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
    "q2 = df_viagem[df_viagem['destinos'].notnull()].groupby('destinos')['valor_total'].agg(['mean', 'count']).reset_index()\n",
    "q2 = q2.sort_values(by='mean', ascending=False).head(3)\n",
    "\n",
    "print(\"=== P2: OS 3 DESTINOS COM MAIOR CUSTO MÉDIO ===\")\n",
    "for idx, row in enumerate(q2.itertuples(), 1):\n",
    "    print(f\"{idx}. Destino: {row.destinos:<50} | Média: R$ {row.mean:,.2f} ({row.count} viagens)\")"
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
    "df_duracao_valida = df_viagem[df_viagem['duracao_dias'].notnull()]\n",
    "\n",
    "print(\"=== P3: VIAGEM DE MAIOR DURAÇÃO E SEU CUSTO TOTAL ===\")\n",
    "if not df_duracao_valida.empty:\n",
    "    q3 = df_duracao_valida.sort_values(by='duracao_dias', ascending=False).iloc[0]\n",
    "    print(f\"• ID da Viagem:  {q3['id_viagem']}\")\n",
    "    print(f\"• Viajante:      {q3['nome_viajante']}\")\n",
    "    print(f\"• Órgão:         {q3['nome_orgao_superior']}\")\n",
    "    print(f\"• Destino:       {q3['destinos']}\")\n",
    "    print(f\"• Período:       {q3['data_inicio']} até {q3['data_fim']}\")\n",
    "    print(f\"• Duração:       {int(q3['duracao_dias'])} dias\")\n",
    "    print(f\"• Custo Total:   R$ {q3['valor_total']:,.2f}\")\n",
    "else:\n",
    "    print(\"[!] Nenhum registro de viagem com duração válida disponível.\")"
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
    "q4 = df_pagamento.groupby('tipo_pagamento')['valor'].mean().reset_index()\n",
    "\n",
    "print(\"=== P4: TIPO DE PAGAMENTO COM MAIOR VALOR MÉDIO ===\")\n",
    "if not q4.empty:\n",
    "    top_q4 = q4.sort_values(by='valor', ascending=False).iloc[0]\n",
    "    print(f\"• Tipo de Pagamento: {top_q4['tipo_pagamento']}\")\n",
    "    print(f\"• Valor Médio:       R$ {top_q4['valor']:,.2f}\")\n",
    "else:\n",
    "    print(\"[!] Tabela de pagamentos vazia ou sem dados válidos.\")"
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
    "df_transporte_valido = df_trecho[~df_trecho['meio_transporte'].isin([None, 'Sem informação', ''])]\n",
    "q5 = df_transporte_valido['meio_transporte'].value_counts().reset_index()\n",
    "q5.columns = ['meio_transporte', 'quantidade']\n",
    "\n",
    "print(\"=== P5: MEIO DE TRANSPORTE MAIS USADO NOS TRECHOS ===\")\n",
    "for idx, row in enumerate(q5.itertuples(), 1):\n",
    "    print(f\"{idx}. {row.meio_transporte:<20} | {row.quantidade:,} trechos\")\n",
    "\n",
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
    "df_uf_valida = df_trecho[~df_trecho['destino_uf'].isin([None, 'Sem informação', ''])]\n",
    "\n",
    "print(\"=== P6: UF DE DESTINO MAIS FREQUENTE NOS TRECHOS ===\")\n",
    "if not df_uf_valida.empty:\n",
    "    q6 = df_uf_valida['destino_uf'].value_counts().reset_index()\n",
    "    q6.columns = ['uf_destino', 'total_trechos']\n",
    "    top_uf = q6.iloc[0]\n",
    "    print(f\"• UF de Destino: {top_uf['uf_destino']}\")\n",
    "    print(f\"• Ocorrências:   {top_uf['total_trechos']:,} trechos\")\n",
    "else:\n",
    "    print(\"[!] Nenhum trecho com UF de destino válida cadastrado.\")"
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
    "df_pagador_valido = df_pagamento[~df_pagamento['nome_orgao_pagador'].isin([None, 'Sem informação', ''])]\n",
    "q7 = df_pagador_valido.groupby('nome_orgao_pagador')['valor'].sum().reset_index()\n",
    "\n",
    "print(\"=== P7: ÓRGÃO COM MAIOR GASTO EM PAGAMENTOS CONSOLIDADOS ===\")\n",
    "if not q7.empty:\n",
    "    top_q7 = q7.sort_values(by='valor', ascending=False).iloc[0]\n",
    "    print(f\"• Órgão Pagador:   {top_q7['nome_orgao_pagador']}\")\n",
    "    print(f\"• Total Pago:      R$ {top_q7['valor']:,.2f}\")\n",
    "else:\n",
    "    print(\"[!] Sem dados ou apenas 'Sem informação' listado na tabela de pagamentos.\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "### 🎨 3. Dashboard Executivo Interativo (Tema Escuro - Estilo Power BI)\n",
    "Utilize o seletor dropdown para filtrar dinamicamente todos os dados e gráficos interativos no próprio corpo do notebook."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "TEMA_DARK = \"plotly_dark\"\n",
    "COR_PRINCIPAL = \"#2ecc71\"  # Verde Neon clássico do Power BI\n",
    "\n",
    "def renderizar_dashboard_interativo(orgao_selecionado=\"Todos\"):\n",
    "    df_filtrado = df_viagem.copy()\n",
    "    if orgao_selecionado != \"Todos\":\n",
    "        df_filtrado = df_filtrado[df_filtrado['nome_orgao_superior'] == orgao_selecionado]\n",
    "        \n",
    "    custo_total = df_filtrado['valor_total'].sum()\n",
    "    qtd_viagens = len(df_filtrado)\n",
    "    duracao_media = df_filtrado['duracao_dias'].mean() if len(df_filtrado) > 0 else 0\n",
    "    \n",
    "    if orgao_selecionado == \"Todos\":\n",
    "        total_pago = df_pagamento['valor'].sum()\n",
    "    else:\n",
    "        ids_viagem_filtradas = set(df_filtrado['id_viagem'])\n",
    "        total_pago = df_pagamento[df_pagamento['id_viagem'].isin(ids_viagem_filtradas)]['valor'].sum()\n",
    "\n",
    "    html_kpis = f\"\"\"\n",
    "    <div style=\"background-color: #111; padding: 20px; border-radius: 10px; margin-bottom: 20px; font-family: sans-serif;\">\n",
    "        <h2 style=\"color: white; margin-top: 0; text-align: center; border-bottom: 2px solid {COR_PRINCIPAL}; padding-bottom: 10px;\">\n",
    "            ✈️ Portal da Transparência: Painel Analítico de Viagens\n",
    "        </h2>\n",
    "        <div style=\"display: flex; justify-content: space-around; text-align: center; margin-top: 15px;\">\n",
    "            <div style=\"flex: 1;\">\n",
    "                <span style=\"color: #888; font-size: 13px; text-transform: uppercase;\">Custo Total</span><br>\n",
    "                <strong style=\"color: white; font-size: 22px;\">R$ {custo_total:,.2f}</strong>\n            </div>\n",
    "            <div style=\"flex: 1; border-left: 1px solid #333;\">\n",
    "                <span style=\"color: #888; font-size: 13px; text-transform: uppercase;\">Qtd. de Viagens</span><br>\n",
    "                <strong style=\"color: white; font-size: 22px;\">{qtd_viagens:,}</strong>\n            </div>\n",
    "            <div style=\"flex: 1; border-left: 1px solid #333;\">\n",
    "                <span style=\"color: #888; font-size: 13px; text-transform: uppercase;\">Total Pago</span><br>\n                <strong style=\"color: white; font-size: 22px;\">R$ {total_pago:,.2f}</strong>\n            </div>\n",
    "            <div style=\"flex: 1; border-left: 1px solid #333;\">\n",
    "                <span style=\"color: #888; font-size: 13px; text-transform: uppercase;\">Duração Média</span><br>\n                <strong style=\"color: {COR_PRINCIPAL}; font-size: 22px;\">{duracao_media:.1f} dias</strong>\n            </div>\n",
    "        </div>\n",
    "    </div>\n",
    "    \"\"\"\n",
    "    display(widgets.HTML(html_kpis))\n",
    "\n",
    "    fig = make_subplots(\n",
    "        rows=1, cols=2, \n",
    "        column_widths=[0.45, 0.55],\n",
    "        subplot_titles=(\"Ranking: Órgãos por Custo\", \"Custo Total por Mês\")\n",
    "    )\n",
    "\n",
    "    g1_data = df_filtrado.groupby('nome_orgao_superior')['valor_total'].sum().reset_index()\n",
    "    g1_data = g1_data.sort_values(by='valor_total', ascending=False).head(5)\n",
    "    \n",
    "    fig.add_trace(\n",
    "        go.Bar(\n",
    "            x=g1_data['valor_total'],\n",
    "            y=g1_data['nome_orgao_superior'],\n",
    "            orientation='h',\n",
    "            marker_color=COR_PRINCIPAL,\n",
    "            text=[f\"R$ {val/1e6:.1f}M\" for val in g1_data['valor_total']],\n",
    "            textposition='auto',\n",
    "            name=\"Custo Total\"\n",
    "        ),\n",
    "        row=1, col=1\n",
    "    )\n",
    "\n",
    "    df_filtrado['mes_ano'] = pd.to_datetime(df_filtrado['data_inicio'], errors='coerce').dt.to_period('M').astype(str)\n",
    "    g2_data = df_filtrado[df_filtrado['mes_ano'] != 'NaT'].groupby('mes_ano')['valor_total'].sum().reset_index()\n",
    "    g2_data = g2_data.sort_values(by='mes_ano')\n",
    "\n",
    "    fig.add_trace(\n",
    "        go.Scatter(\n",
    "            x=g2_data['mes_ano'],\n",
    "            y=g2_data['valor_total'],\n",
    "            mode='lines+markers',\n",
    "            line=dict(color=COR_PRINCIPAL, width=3),\n",
    "            marker=dict(size=8),\n",
    "            name=\"Evolução Mensal\"\n",
    "        ),\n",
    "        row=1, col=2\n",
    "    )\n",
    "\n",
    "    fig.update_layout(\n",
    "        template=TEMA_DARK,\n",
    "        height=450,\n",
    "        showlegend=False,\n",
    "        paper_bgcolor=\"#111\",\n",
    "        plot_bgcolor=\"#111\",\n",
    "        margin=dict(l=20, r=20, t=40, b=20)\n",
    "    )\n",
    "    \n",
    "    fig.update_yaxes(autorange=\"reversed\", row=1, col=1)\n",
    "    fig.show()\n",
    "\n",
    "lista_orgaos = [\"Todos\"] + sorted(df_viagem['nome_orgao_superior'].dropna().unique().tolist())\n",
    "\n",
    "interact(\n",
    "    renderizar_dashboard_interativo, \n",
    "    orgao_selecionado=widgets.Dropdown(\n",
    "        options=lista_orgaos, \n",
    "        value=\"Todos\", \n",
    "        description=\"Filtro Órgão:\",\n",
    "        style={'description_width': 'initial'},\n",
    "        layout={'width': '400px'}\n",
    "    )\n",
    ");"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "### 🏛️ 4. Camada Gold Agregada (Persistência no PostgreSQL)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "print(\"[*] Processando agregação para a camada Gold agregada...\")\n",
    "\n",
    "df_gold_agregada = df_viagem.groupby('nome_orgao_superior').agg(\n",
    "    total_viagens=('id_viagem', 'count'),\n",
    "    custo_total=('valor_total', 'sum'),\n",
    "    custo_medio=('valor_total', 'mean'),\n",
    "    duracao_media_dias=('duracao_dias', 'mean')\n",
    ").reset_index()\n",
    "\n",
    "df_gold_agregada['custo_medio'] = df_gold_agregada['custo_medio'].round(2)\n",
    "df_gold_agregada['duracao_media_dias'] = df_gold_agregada['duracao_media_dias'].round(1)\n",
    "\n",
    "# Tratamento estrito de valores nulos matemáticos antes de persistir no Postgres\n",
    "df_gold_agregada = df_gold_agregada.where(pd.notnull(df_gold_agregada), None)\n",
    "\n",
    "conexao = conectar()\n",
    "\n",
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
    "colunas = ['nome_orgao_superior', 'total_viagens', 'custo_total', 'custo_medio', 'duracao_media_dias']\n",
    "placeholders = \", \".join([\"%s\"] * len(colunas))\n",
    "sql_insert = f\"INSERT INTO gold_resumo_orgaos ({', '.join(colunas)}) VALUES ({placeholders})\"\n",
    "\n",
    "registros = [tuple(x) for x in df_gold_agregada.itertuples(index=False, name=None)]\n",
    "inserir_em_lote(conexao, sql_insert, registros)\n",
    "\n",
    "# SALVAMENTO FÍSICO COM COMMIT\n",
    "conexao.commit()\n",
    "conexao.close()\n",
    "\n",
    "print(f\"[SUCCESS] Tabela 'gold_resumo_orgaos' gravada com sucesso!\")\n",
    "print(f\"  • {len(df_gold_agregada)} órgãos persistidos na camada Gold.\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "### 🔎 5. Validação e Consulta Direta da Camada Gold"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "print(\"[*] Conectando ao banco de dados para validar a tabela 'gold_resumo_orgaos'...\")\n",
    "\n",
    "conexao = conectar()\n",
    "query_validacao = \"\"\"\n",
    "    SELECT \n",
    "        nome_orgao_superior, \n",
    "        total_viagens, \n",
    "        custo_total, \n",
    "        custo_medio, \n",
    "        duracao_media_dias\n",
    "    FROM gold_resumo_orgaos\n",
    "    ORDER BY custo_total DESC\n",
    "    LIMIT 10;\n",
    "\"\"\"\n",
    "df_gold_verificacao = pd.read_sql_query(query_validacao, conexao)\n",
    "conexao.close()\n",
    "\n",
    "print(f\"[+] Consulta de auditoria concluída com sucesso!\")\n",
    "print(f\"  • Exibindo os 10 órgãos de maior relevância orçamentária persistidos na base:\")\n",
    "display(df_gold_verificacao)"
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

# Salva localmente na pasta raiz de execução
with open(filename, "w", encoding="utf-8") as f:
    json.dump(notebook_data, f, indent=1, ensure_ascii=False)

# Tenta salvar diretamente na pasta Downloads/Projeto_final_SCTEC
try:
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    target_path = os.path.join(target_dir, filename)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(notebook_data, f, indent=1, ensure_ascii=False)
    print(f"\n[SUCCESS] O arquivo '{filename}' foi gravado em: {target_path}")
except Exception as e:
    print(f"\n[Aviso] Erro ao gravar no diretório absoluto: {e}")
    print(f"O arquivo foi salvo na pasta local onde o terminal foi executado.")