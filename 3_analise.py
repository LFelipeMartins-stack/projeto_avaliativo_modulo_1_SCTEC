"""
3_analise.py
------------
Pipeline da Camada Gold: Geração de KPIs estratégicos e exportação de gráficos 
de alta qualidade a partir dos dados refinados da camada Silver.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from banco import conectar

# Configuração estética global para os gráficos (Seaborn + Matplotlib)
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.titlesize': 16
})

def obter_dados_analiticos(conexao):
    """Carrega dados estratégicos agregados diretamente da camada Silver."""
    print("[*] Consultando dados da camada Silver no PostgreSQL...")
    
    # Query 1: Visão Geral e KPIs Consolidados
    query_kpis = """
    SELECT 
        COUNT(id_viagem) as total_viagens,
        SUM(valor_total) as custo_total,
        AVG(valor_total) as custo_medio,
        AVG(duracao_dias) as duracao_media,
        SUM(valor_diarias) as total_diarias,
        SUM(valor_passagens) as total_passagens,
        SUM(valor_outros_gastos) as total_outros,
        SUM(valor_devolucao) as total_devolvido
    FROM silver_viagem;
    """
    df_kpis = pd.read_sql_query(query_kpis, conexao)
    
    # Query 2: Top 10 Órgãos com Maior Gasto Total
    query_orgaos = """
    SELECT 
        nome_orgao_superior as orgao,
        SUM(valor_total) as gasto_total,
        COUNT(id_viagem) as qtd_viagens
    FROM silver_viagem
    GROUP BY nome_orgao_superior
    ORDER BY gasto_total DESC
    LIMIT 10;
    """
    df_orgaos = pd.read_sql_query(query_orgaos, conexao)
    
    # Query 3: Distribuição Mensal de Gastos (Evolução Temporal)
    query_temporal = """
    SELECT 
        TO_CHAR(data_inicio, 'YYYY-MM') as mes,
        SUM(valor_total) as gasto_total,
        COUNT(id_viagem) as qtd_viagens
    FROM silver_viagem
    WHERE data_inicio IS NOT NULL
    GROUP BY mes
    ORDER BY mes;
    """
    df_temporal = pd.read_sql_query(query_temporal, conexao)
    
    # Query 4: Meios de Transporte mais Utilizados nas Passagens
    query_transportes = """
    SELECT 
        meio_transporte,
        COUNT(id_passagem) as qtd_passagens,
        SUM(valor_passagem) as gasto_passagens
    FROM silver_passagem
    GROUP BY meio_transporte
    ORDER BY qtd_passagens DESC;
    """
    df_transportes = pd.read_sql_query(query_transportes, conexao)
    
    return df_kpis, df_orgaos, df_temporal, df_transportes


def gerar_relatorio_executivo(df_kpis):
    """Gera um painel executivo textual formatado diretamente no terminal."""
    row = df_kpis.iloc[0]
    
    print("\n" + "="*60)
    print("      PORTAL DA TRANSPARÊNCIA - PAINEL EXECUTIVO GOLD (2025)   ")
    print("="*60)
    print(f" Total de Viagens Analisadas : {row['total_viagens']:,}")
    print(f" Custo Total do Período      : R$ {row['custo_total']:,.2f}")
    print(f" Custo Médio por Viagem      : R$ {row['custo_medio']:,.2f}")
    print(f" Duração Média das Viagens   : {row['duracao_media']:.1f} dias")
    print("-"*60)
    print(" DETALHAMENTO DOS GASTOS BRUTOS:")
    print(f"  • Diárias Pagas            : R$ {row['total_diarias']:,.2f}")
    print(f"  • Passagens Compradas      : R$ {row['total_passagens']:,.2f}")
    print(f"  • Outros Gastos            : R$ {row['total_outros']:,.2f}")
    print(f"  • Valores Devolvidos (Ref) : R$ {row['total_devolvido']:,.2f}")
    print("="*60 + "\n")


def plotar_graficos(df_orgaos, df_temporal, df_transportes):
    """Gera e exporta as visualizações de dados para arquivos PNG."""
    print("[*] Renderizando gráficos analíticos...")
    
    # ---------------------------------------------------------------------------
    # GRÁFICO 1: Maiores Gastos por Órgão Superior (Barras Horizontais)
    # ---------------------------------------------------------------------------
    plt.figure(figsize=(12, 6))
    # Divide os valores por 1 milhão para facilitar a leitura do gráfico
    df_orgaos['gasto_milhoes'] = df_orgaos['gasto_total'] / 1_000_000
    
    ax = sns.barplot(
        x='gasto_milhoes', 
        y='orgao', 
        data=df_orgaos, 
        palette='Blues_r',
        hue='orgao',
        legend=False
    )
    
    # Adiciona rótulos com os valores exatos nas pontas das barras
    for container in ax.containers:
        ax.bar_label(container, fmt='R$ %.1fM', padding=5, fontsize=9)
        
    plt.title("Top 10 Órgãos Superiores com Maior Gasto Acumulado (2025)")
    plt.xlabel("Gasto Total (em Milhões de R$)")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig("gold_gasto_por_orgao.png", dpi=300)
    plt.close()
    print("[+] Gráfico exportado: gold_gasto_por_orgao.png")

    # ---------------------------------------------------------------------------
    # GRÁFICO 2: Evolução Mensal dos Gastos (Linha de Tendência)
    # ---------------------------------------------------------------------------
    plt.figure(figsize=(10, 5))
    df_temporal['gasto_milhoes'] = df_temporal['gasto_total'] / 1_000_000
    
    sns.lineplot(
        x='mes', 
        y='gasto_milhoes', 
        data=df_temporal, 
        marker='o', 
        color='#2b5c8f', 
        linewidth=2.5
    )
    
    # Adiciona os valores monetários em cada ponto do gráfico de linha
    for x, y in zip(df_temporal['mes'], df_temporal['gasto_milhoes']):
        plt.text(x, y + 0.5, f"R$ {y:.1f}M", ha='center', fontsize=9, fontweight='bold')
        
    plt.title("Evolução Mensal do Custo de Viagens Públicas (2025)")
    plt.xlabel("Mês de Início da Viagem")
    plt.ylabel("Gasto Total (em Milhões de R$)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("gold_evolucao_mensal.png", dpi=300)
    plt.close()
    print("[+] Gráfico exportado: gold_evolucao_mensal.png")

    # ---------------------------------------------------------------------------
    # GRÁFICO 3: Preferência de Meios de Transporte (Rosca/Donut)
    # ---------------------------------------------------------------------------
    plt.figure(figsize=(7, 7))
    # Consolida categorias menores em 'Outros' para evitar poluição visual
    total_outros_transportes = df_transportes.iloc[3:]['qtd_passagens'].sum()
    df_pizza = df_transportes.head(3).copy()
    if total_outros_transportes > 0:
        df_pizza = pd.concat([df_pizza, pd.DataFrame([{'meio_transporte': 'OUTROS', 'qtd_passagens': total_outros_transportes}])], ignore_index=True)
    
    cores = ['#2b5c8f', '#4682b4', '#b0c4de', '#d3d3d3']
    plt.pie(
        df_pizza['qtd_passagens'], 
        labels=df_pizza['meio_transporte'], 
        autopct='%1.1f%%', 
        startangle=90, 
        colors=cores,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
    )
    
    # Desenha o círculo central branco (transformando pizza em rosca/donut)
    circulo_centro = plt.Circle((0,0), 0.60, fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(circulo_centro)
    
    plt.title("Distribuição de Passagens por Meio de Transporte")
    plt.tight_layout()
    plt.savefig("gold_meios_transporte.png", dpi=300)
    plt.close()
    print("[+] Gráfico exportado: gold_meios_transporte.png")


def main():
    try:
        conexao = conectar()
        
        # 1. Busca os dados agregados
        df_kpis, df_orgaos, df_temporal, df_transportes = obter_dados_analiticos(conexao)
        
        # 2. Exibe o painel textual
        gerar_relatorio_executivo(df_kpis)
        
        # 3. Exporta as imagens analíticas
        plotar_graficos(df_orgaos, df_temporal, df_transportes)
        
        print("\n=== PIPELINE GOLD CONCLUÍDO COM SUCESSO! GRÁFICOS GERADOS ===")
        
    except Exception as e:
        print(f"\n[ERRO CRÍTICO NA GERAÇÃO DA CAMADA GOLD]: {e}")
    finally:
        conexao.close()

if __name__ == "__main__":
    main()