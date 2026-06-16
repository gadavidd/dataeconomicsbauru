# DataEconomicsBauru

Dashboard de Business Intelligence para monitoramento de indicadores econômicos, de empregabilidade, empresas, renda e demografia do município de Bauru-SP e região.

## Sobre o projeto

O **DataEconomicsBauru** é uma solução de Business Intelligence desenvolvida como projeto acadêmico extensionista da UNISAGRADO. O objetivo do projeto é centralizar e transformar dados públicos sobre Bauru em informações visuais e interativas, facilitando a análise do cenário econômico local.

A solução foi construída a partir de dados públicos organizados e tratados por meio de um pipeline em Python, armazenados em um banco SQLite e consumidos no Power BI para criação de um dashboard interativo.

O painel busca apoiar empresas, entidades, gestores públicos, instituições de desenvolvimento econômico e demais interessados na compreensão de indicadores relacionados a emprego, empresas, MEIs, renda, PIB, movimentações financeiras e demografia.

## Link do dashboard

Acesse o painel publicado no Power BI:

https://app.powerbi.com/view?r=eyJrIjoiZTYwYmEwZWUtZWM4YS00OTNiLTk1OTQtYzVjMDg1ODJhMWE1IiwidCI6ImZlODc4N2JjLWM5MTQtNDY2NS04NTQ3LTI2OGUxNWNiMGQ5YSJ9

## Objetivo

Desenvolver um painel de Business Intelligence capaz de reunir, tratar e apresentar indicadores econômicos e sociais de Bauru-SP, contribuindo para a leitura de dados públicos e apoiando processos de consulta, planejamento e tomada de decisão.

## Principais funcionalidades

O dashboard é dividido em cinco páginas principais:

### 1. Visão Geral

Apresenta uma síntese dos principais indicadores do painel, incluindo população, PIB municipal, transferências via PIX, abertura de MEIs, novos empregos e setores com maior abertura de empresas.

### 2. Empregabilidade

Reúne indicadores do mercado de trabalho de Bauru, como empregos ativos, saldo de empregos, setor com maior destaque, último mês analisado, melhor mês, pior mês, evolução mensal do saldo e sazonalidade do emprego.

### 3. Empresas e MEIs

Apresenta informações sobre abertura de empresas e microempreendedores individuais, incluindo MEIs ativos, novas empresas em Bauru, setor líder, município líder na região e ranking regional de abertura de empresas.

### 4. Economia e Renda

Exibe indicadores econômicos e financeiros, como PIB municipal, renda tributável declarada, bens declarados, crédito, poupança, composição da renda por classe e evolução de indicadores financeiros.

### 5. Demografia

Mostra indicadores populacionais e demográficos, como população de Bauru, faixa etária predominante, distribuição por faixa etária, evolução populacional e comparativo populacional regional.

## Fontes de dados

O projeto utiliza dados públicos organizados e tratados a partir de diferentes fontes, incluindo:

- IBGE;
- Novo CAGED;
- Dados públicos organizados pela Caravela;
- Bases de indicadores econômicos, demográficos, financeiros, empresariais e de empregabilidade de Bauru e região.

As bases foram tratadas e padronizadas para permitir a integração com o Power BI.

## Arquitetura da solução

A solução foi organizada em três camadas principais:

1. **Coleta e tratamento de dados**  
   Os arquivos brutos são processados por scripts Python, que realizam limpeza, padronização, conversão de tipos, criação de colunas auxiliares e geração de bases tratadas.

2. **Banco de dados local**  
   As bases tratadas são carregadas no banco SQLite `databauru.db`, que funciona como repositório estruturado dos dados utilizados no projeto.

3. **Dashboard em Power BI**  
   O Power BI consome as tabelas do banco SQLite por meio de conexão ODBC, permitindo a criação de gráficos, cards, filtros e páginas interativas.

## Tecnologias utilizadas

- Python;
- Pandas;
- SQLite;
- SQL;
- Power BI;
- Devart ODBC Driver for SQLite;
- Git e GitHub.

## Estrutura do projeto

```text
dataeconomicsbauru/
│
├── powerbi/
│   └── arquivos relacionados ao dashboard em Power BI
│
├── scripts/
│   └── scripts Python para tratamento e geração das bases
│
├── data/
│   ├── raw/
│   │   └── bases brutas
│   │
│   └── processed/
│       ├── bases tratadas
│       └── databauru.db
│
└── README.md
```

## Como executar o pipeline de dados

Para gerar ou atualizar as bases tratadas, execute o script principal do pipeline a partir da raiz do projeto:

```bash
python scripts/databauru_pipeline_v3.py --input data/raw/caravelas --output data/processed
```

O script realiza o tratamento dos arquivos CSV, gera as bases padronizadas e atualiza o banco SQLite `databauru.db`.

## Conexão com o Power BI

O dashboard foi conectado ao banco `databauru.db` por meio de ODBC.

Fluxo utilizado:

```text
CSVs brutos → Script Python → Bases tratadas → databauru.db → Power BI
```

Para atualizar o dashboard:

1. Substituir ou adicionar novos arquivos na pasta de dados brutos;
2. Executar novamente o pipeline em Python;
3. Manter o arquivo `databauru.db` no mesmo caminho configurado no ODBC;
4. Abrir o Power BI e clicar em **Atualizar**.

## Validação extensionista

A solução foi apresentada para avaliação externa junto ao Emprega Bauru, vinculado à Secretaria Municipal de Desenvolvimento Econômico, Turismo e Renda da Prefeitura Municipal de Bauru.

O feedback recebido indicou que o dashboard reúne indicadores relevantes para a compreensão do cenário econômico local, centraliza informações úteis em um único ambiente e pode apoiar consultas, análises comparativas e discussões sobre desenvolvimento econômico.

Também foi sugerida como melhoria futura a inclusão de indicadores de posição de Bauru no ranking estadual de geração de empregos, ampliando o contexto da análise de empregabilidade.

## Resultados alcançados

O projeto entregou:

- banco SQLite com tabelas tratadas;
- pipeline de tratamento de dados em Python;
- dashboard publicado no Power BI;
- visualizações interativas sobre economia, empregabilidade, empresas, renda e demografia;
- validação externa por representante ligada ao desenvolvimento econômico municipal;
- documentação final do projeto extensionista.

## Limitações e melhorias futuras

Algumas bases utilizadas possuem recortes temporais diferentes, o que limita a comparação direta entre todos os indicadores em um mesmo ano. Além disso, algumas tabelas representam recortes consolidados e não séries históricas completas.

Como melhorias futuras, destacam-se:

- inclusão de ranking estadual de geração de empregos;
- atualização contínua dos dados;
- ampliação dos indicadores setoriais;
- criação de filtros por município em todas as páginas;
- integração automatizada com APIs públicas;
- publicação de documentação técnica mais detalhada sobre o modelo de dados.

## Integrantes do grupo

- Allisson Silva Raymundo;
- Carlos Augusto David Neto;
- Emerson Maia de Matos Toneti;
- Felipe dos Anjos Ramos;
- Gabriel Augusto David.

## Contexto acadêmico

Projeto desenvolvido para o módulo **Projeto Desenvolvimento de um Banco de Dados e um Painel no Power BI**, no contexto do Bootcamp Extensionista da UNISAGRADO.

Professor responsável: Prof. Victor Hugo Braguim Canto.

## Licença

Este projeto possui finalidade acadêmica e extensionista. Os dados utilizados são provenientes de bases públicas e/ou dados públicos organizados. O uso, reprodução ou adaptação do material deve preservar a finalidade educacional e a correta atribuição ao grupo responsável.
