# Pipeline de Dados: Análise Estruturada e Auditoria de Viagens a Serviço do Governo Federal

Este projeto implementa um pipeline de dados ponta a ponta focado na extração, tratamento, modelagem relacional e análise analítica dos dados abertos de viagens a serviço do Governo Federal referentes ao ano de 2025. O objetivo central é fornecer um arcabouço tecnológico robusto que transforme dados brutos e volumosos em uma base altamente confiável para auditoria interna e tomada de decisão estratégica.

---

## 1. Arquitetura do Sistema (Visão Geral)

O projeto adota a **Arquitetura Medallion** (Raw, Silver e Gold), permitindo o isolamento de responsabilidades, garantia de rastreabilidade e escalabilidade do processamento.

```
[Portal da Transparência] -> (gdown) -> [Dados Brutos (.zip)]
                                                |
                                                v
   +-------------------------------------------------------------------------+
   | CAMADA RAW (PostgreSQL): Cópia fiel do CSV original em strings (VARCHAR)|
   +-------------------------------------------------------------------------+
                                                |
                                                v
   +-------------------------------------------------------------------------+
   | CAMADA SILVER (PostgreSQL): Limpeza profunda, Tipagem e Constraints     |
   +-------------------------------------------------------------------------+
                                                |
                                                v
   +-------------------------------------------------------------------------+
   | CAMADA GOLD (Notebook/Views): Agregações analíticas e Visualizações     |
   +-------------------------------------------------------------------------+
```

### Stack Tecnológica Utilizada
* **Linguagem Principal:** Python 3.13
* **Manipulação de Dados:** Pandas
* **Processamento de Texto:** Expressões Regulares (Regex)
* **Banco de Dados:** PostgreSQL
* **Ingestão de Arquivos:** `gdown` e `zipfile`
* **Visualização Estática/Estatística:** Matplotlib e Seaborn
* **Visualização Dinâmica/Interativa:** Plotly (Express & Graph Objects)
* **Interface de Dashboard Contida:** ipywidgets (Componentes interativos no Notebook)

---

## 2. Estrutura do Roteiro e Execução

O pipeline é estritamente modularizado e ordenado sequencialmente para garantir a integridade referencial entre as execuções:

### Passo 0: Criação do Ambiente de Banco de Dados (`0_criar_banco.sql`)
Define a infraestrutura do banco de dados PostgreSQL. Cria 8 tabelas no total:
* **4 Tabelas Raw:** Todas as colunas configuradas como `VARCHAR` e sem restrições nativas para recepção segura de dados corrompidos ou mal formatados.
* **4 Tabelas Silver:** Modeladas com chaves primárias (`PRIMARY KEY`), chaves estrangeiras (`FOREIGN KEY`) e restrições de verificação (`CHECK`, `NOT NULL`, `UNIQUE`).

### Passo 1: Extração Automatizada (`1_extrair.py`)
* Realiza o download robusto do arquivo compactado via API do Google Drive utilizando `gdown`.
* Executa um diagnóstico de inspeção em disco exibindo colunas e metadados iniciais.
* Lê os arquivos CSV utilizando fragmentação em memória (`chunksize=50000`), blindando o pipeline contra estouros de memória RAM.
* Garante a **idempotência** do processo limpando dados históricos através do comando `TRUNCATE TABLE ... CASCADE;` antes de realizar o *bulk insert* performático.

### Passo 2: Transformação e Higienização Química (`2_transformar.py`)
Copia os dados da camada Raw para a Silver executando as regras de negócio e de qualidade textual/numérica.

### Passo 3: Analytics e Tomada de Decisão (`3_analise.ipynb`)
Consome as tabelas consolidadas da Silver, cria a **VIEW Gold** de agregação de custos e plota os indicadores estratégicos solicitados para a gestão pública.

---

## 3. Data Quality e Engenharia de Atributos (Camada Silver)

Para assegurar que nenhum dado inválido quebre as restrições físicas do PostgreSQL, o script de transformação executa sanitizações via código Pandas:

### Tabela de Mapeamento de Constraints Nativas
O banco de dados valida severamente as seguintes regras de negócio inseridas no DDL:

| Tabela | Atributo | Tipo de Restrição | Objetivo de Engenharia |
| :--- | :--- | :--- | :--- |
| `silver_viagem` | `nome_orgao_superior` | `NOT NULL` | Evitar registros órfãos de macroestrutura governamental. |
| `silver_viagem` | `valor_diarias` | `CHECK (>= 0)` | Impedir valores monetários negativos invertidos. |
| `silver_pagamento` | `valor` | `CHECK (>= 0)` | Validar que desembolsos financeiros sejam sempre positivos. |
| `silver_pagamento` | `tipo_pagamento` | `NOT NULL` | Rastreabilidade do método de liquidação da despesa. |
| `silver_passagem` | `valor_passagem` | `CHECK (>= 0)` | Garantir consistência contábil de bilhetes. |
| `silver_passagem` | `taxa_servico` | `CHECK (>= 0)` | Bloquear taxas de agenciamento negativas. |
| `silver_trecho` | `numero_diarias` | `CHECK (>= 0)` | Assegurar contagem temporal coerente. |
| `silver_trecho` | `(id_viagem, sequencia_trecho)` | `UNIQUE` | Bloquear duplicação física de pernas de um mesmo itinerário. |

### Funções Customizadas de Conversão
1. **Limpeza Decimal:** Transforma strings monetárias brasileiras (ex: `"1.272,97"`) em decimais de ponto flutuante válidos (`1272.97`), tratando simultaneamente strings vazias e erros de fórmula legados do Excel (como `#N/D`, `#VALOR!`). Valores negativos são truncados para `0.00` via `.clip(lower=0.00)`.
2. **Limpeza de Datas:** Converte strings textuais no padrão brasileiro (`DD/MM/AAAA`) para formato temporal estruturado ISO (`YYYY-MM-DD`).
3. **Tratamento de Strings via Regex:** Aplica a função `limpar_texto_regex` para varrer todas as colunas de texto livre. A expressão regular `re.sub(r'\s+', ' ', texto)` elimina quebras de linha (`\n`), tabulações (`\t`) e múltiplos espaços em branco inseridos por erro humano de digitação, unificando os dados em caixa alta (*Uppercase*).

### Métricas Finais de Ingestão (Volume de Auditoria)
A execução bem-sucedida do pipeline consolidou o seguinte volume final de registros limpos na Camada Silver:
* **`silver_viagem`**: 341.860 registros.
* **`silver_pagamento`**: 606.916 registros.
* **`silver_passagem`**: 167.260 registros.
* **`silver_trecho`**: 763.349 registros.

---

## 4. Estudo de Caso de Engenharia de Dados: O Bug da Sequência Omitida

Durante o desenvolvimento do pipeline, o módulo de auditoria de qualidade (**Data QA**) identificou uma anomalia analítica crítica: a tabela de trechos estava descartando **473.090 registros legítimos** (62% da base total) na restrição `UNIQUE` da chave composta.

* **Causa Raiz:** No arquivo CSV original enviado pelo Governo, o cabeçalho chamava-se `"Sequência Trecho"`. No arquivo de configuração do pipeline, a string esperada era `"Sequência do trecho"`. O conectivo `"do"` quebrou o algoritmo de similaridade automática, gerando uma coluna inteiramente nula (`NULL`) na camada RAW.
* **Efeito Cascata:** No tratamento de dados, o Pandas preenchia os nulos com o valor padrão `1` (`.fillna(1)`). Consequentemente, viagens complexas com múltiplas conexões ou escalas tinham todos os seus subtrechos gravados com a sequência `1`. Ao rodar a limpeza de duplicatas, o Pandas mantinha apenas o primeiro trecho e eliminava todas as outras pernas da viagem.
* **Correção Realizada:** O mapeador de extração foi corrigido para `"Sequência Trecho"`. Isso recuperou a integridade física de todas as 763.349 linhas originais. 
* **Impacto no Negócio:** Sem essa correção, o ranking de destinos mais frequentes ficava severamente enviesado, apontando o **Distrito Federal** em 1º lugar porque o pipeline contabilizava apenas a perna inicial de ida das viagens. Ao restaurar os dados, a realidade estatística emergiu: **São Paulo** é o verdadeiro polo central (Top 1) de tráfego a serviço devido ao seu papel como grande *hub* de conexões e escalas da malha aérea nacional.

---

## 5. Insights de Negócio e Otimização de Gastos (Foco Gestão Pública)

Com a camada Gold devidamente estruturada e alimentada por dados livres de inconsistências estruturais, os analistas governamentais podem derivar os seguintes planos de ação para otimização do erário público:

### Análise Volumétrica e Eficiência de Tráfego (Pergunta 6 e 5)
* **Fato:** O Estado de **São Paulo** lidera a frequência absoluta com **82.722 trechos**, seguido de perto pelo **Distrito Federal** com **79.962 trechos**. O meio de transporte massivamente mais utilizado em toda a estrutura é o **Aéreo**.
* **Oportunidade de Melhoria:** Dado o tráfego regular e massivo no eixo SP-DF por funcionários da máquina pública, o Ministério da Gestão e Inovação pode negociar **acordos corporativos de longo prazo (*Corporate Travel Agreements*)** diretamente com as companhias aéreas que operam nos *hubs* de Congonhas, Guarulhos e Brasília, fixando tarifas máximas de bilhetes (*capped fares*) para reduzir o impacto financeiro da flutuação da aviação civil comercial.

### Gestão e Auditoria de Padrões de Despesa
* **Fato:** A identificação dos 5 órgãos com maior custo total e a segregação do órgão que pagou o maior volume financeiro absoluto permite isolar onde estão os macro-ofensores do orçamento de viagens.
* **Oportunidade de Melhoria:** A implementação de políticas restritivas baseadas na **antecedência de compra** (ex: obrigatoriedade de emissão de bilhetes com no mínimo 14 dias de antecedência para viagens ordinárias) foca diretamente na redução do custo médio por trecho nesses órgãos de alta volumetria.

### Otimização Logística de Itinerários Complexos
* **Fato:** A análise de custo médio por destino combinada com o rastreamento da **viagem de maior duração** (que cruzou múltiplos dias e acumulou valores elevados de diárias e passagens) joga luz sobre a eficiência das missões institucionais.
* **Oportunidade de Melhoria:** Viagens com durações excessivamente longas e fluxos contínuos de diárias devem ser submetidas a uma matriz de custo-benefício automatizada no sistema de concessão de viagens (SCDP), avaliando se a substituição por agendas concentradas ou reuniões virtuais em plataformas oficiais não atenderia o interesse público com custo zero para os cofres do Estado.

---

## 6. Como Configurar e Executar o Projeto

### Pré-requisitos
Certifique-se de ter instalado em sua máquina:
* PostgreSQL (Serviço ativo e rodando localmente ou em container)
* Python 3.11 ou superior

### Passo 1: Clonar o Repositório e Instalar Dependências
```bash
git clone [https://github.com/seu-usuario/PROJETO_FINAL_SCTEC.git](https://github.com/seu-usuario/PROJETO_FINAL_SCTEC.git)
cd PROJETO_FINAL_SCTEC
pip install -r requirements.txt
```

### Passo 2: Configurar Variáveis de Ambiente
Copie o arquivo `.env.example` para `.env` e preencha com as credenciais do seu banco de dados local:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=viagens_governo
DB_USER=seu_usuario
DB_PASS=sua_senha
DRIVE_FILE_ID=15vGhmvT0Ux2crqHy_YeRoRiaiCkdB88A
```

### Passo 3: Criar a Infraestrutura de Tabelas
Execute o script DDL no seu banco de dados PostgreSQL para estruturar as camadas Raw e Silver:
```bash
psql -h localhost -U seu_usuario -d viagens_governo -f 0_criar_banco.sql
```

### Passo 4: Executar a Cadeia do Pipeline
Execute sequencialmente os módulos Python no terminal:

```bash
# 1. Faz o download, descompacta os CSVs e carrega a Camada Raw
python 1_extrair.py

# 2. Executa a limpeza química com Regex, formatação monetária e persiste na Camada Silver
python 2_transformar.py
```

Abra o ambiente do VS Code ou Jupyter Notebook para rodar o arquivo **`3_analise.ipynb`**, gerando a camada agregada Gold e as exibições visuais dinâmicas das métricas públicas.
```