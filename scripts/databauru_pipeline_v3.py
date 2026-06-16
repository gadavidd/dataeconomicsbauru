#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataBauru - Pipeline de tratamento das bases CSV do Caravelas
Versão 3

Uso recomendado na raiz do projeto:
    python scripts/databauru_pipeline_v3.py --input data/raw/caravelas --output data/processed

O script:
1. Lê os arquivos CSV brutos recebidos;
2. Corrige problemas comuns de CSV, inclusive nomes de setores com vírgula;
3. Padroniza nomes de colunas;
4. Cria colunas de data, ano, mês e tipo de valor quando aplicável;
5. Gera bases tratadas em CSV;
6. Gera um banco SQLite databauru.db;
7. Gera uma base consolidada em formato longo para páginas-resumo no Power BI.
"""

from __future__ import annotations

import argparse
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd


MUNICIPIO_REFERENCIA = "Bauru"
UF_REFERENCIA = "SP"
FONTE_DADOS = "Caravelas / dados públicos organizados"


MESES_ORDEM = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}

def slugify(texto: str) -> str:
    """Transforma texto em nome seguro para coluna/tabela."""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.replace("%", "percentual")
    for char in ["º", "ª", "(", ")", "[", "]", "{", "}", "/", "\\", ".", "-", "–", "—"]:
        texto = texto.replace(char, "_")
    texto = texto.replace(" ", "_")
    while "__" in texto:
        texto = texto.replace("__", "_")
    return texto.strip("_")


def primeiro_existente(input_dir: Path, nomes: list[str]) -> Path | None:
    for nome in nomes:
        caminho = input_dir / nome
        if caminho.exists():
            return caminho
    return None


def ler_csv_robusto(caminho: Path) -> pd.DataFrame:
    """
    Lê CSV comum. Se houver vírgulas no texto do primeiro campo, tenta reconstruir
    arquivos de duas colunas separando a última vírgula como valor numérico.
    """
    try:
        return pd.read_csv(caminho, encoding="utf-8")
    except Exception:
        pass

    linhas = caminho.read_text(encoding="utf-8").splitlines()
    if not linhas:
        return pd.DataFrame()

    cabecalho = linhas[0].strip().split(",")
    if len(cabecalho) < 2:
        raise ValueError(f"Não foi possível identificar colunas no arquivo: {caminho.name}")

    coluna_texto = cabecalho[0].strip()
    coluna_valor = ",".join(cabecalho[1:]).strip()

    registros = []
    for linha in linhas[1:]:
        linha = linha.strip()
        if not linha:
            continue
        if "," not in linha:
            continue
        texto, valor = linha.rsplit(",", 1)
        registros.append({coluna_texto: texto.strip(), coluna_valor: valor.strip()})

    return pd.DataFrame(registros)


def padronizar_base(df: pd.DataFrame, fonte_arquivo: str, municipio: str | None = MUNICIPIO_REFERENCIA) -> pd.DataFrame:
    df = df.copy()
    df.columns = [slugify(c) for c in df.columns]
    df["fonte_arquivo"] = fonte_arquivo
    df["fonte_dados"] = FONTE_DADOS
    if municipio is not None:
        df["municipio_referencia"] = municipio
        df["uf_referencia"] = UF_REFERENCIA
    return df


def converter_periodo_mensal(df: pd.DataFrame, coluna: str = "periodo") -> pd.DataFrame:
    """Converte períodos no formato YYYYMM para data, ano, mês e nome do mês."""
    df = df.copy()
    s = df[coluna].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    df[coluna] = s
    df["ano"] = s.str.slice(0, 4).astype("Int64")
    df["mes"] = s.str.slice(4, 6).astype("Int64")
    df["data_referencia"] = pd.to_datetime(s + "01", format="%Y%m%d", errors="coerce")
    df["mes_nome"] = df["mes"].map({v: k for k, v in MESES_ORDEM.items()})
    return df


def converter_periodo_anual(df: pd.DataFrame, coluna: str = "periodo") -> pd.DataFrame:
    """Converte períodos no formato YYYY para data e ano."""
    df = df.copy()
    s = df[coluna].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    df[coluna] = s
    df["ano"] = s.astype("Int64")
    df["data_referencia"] = pd.to_datetime(s + "-01-01", errors="coerce")
    return df


def preparar_ranking(df: pd.DataFrame, nome_categoria: str, nome_valor: str, fonte: str, municipio: str | None = MUNICIPIO_REFERENCIA) -> pd.DataFrame:
    """Padroniza bases de ranking/categoria com uma coluna textual e uma coluna numérica."""
    df = padronizar_base(df, fonte, municipio=municipio)
    cols = [c for c in df.columns if c not in ["fonte_arquivo", "fonte_dados", "municipio_referencia", "uf_referencia"]]
    if len(cols) < 2:
        raise ValueError(f"Base {fonte} precisa ter pelo menos duas colunas.")
    df = df.rename(columns={cols[0]: nome_categoria, cols[1]: nome_valor})
    df[nome_categoria] = df[nome_categoria].astype(str).str.strip()
    df[nome_valor] = pd.to_numeric(df[nome_valor], errors="coerce")
    df = df.dropna(subset=[nome_categoria, nome_valor])
    df["ordem"] = df[nome_valor].rank(method="first", ascending=False).astype(int)
    return df.sort_values("ordem")


def preparar_evolucao_com_projecao(df: pd.DataFrame, valor_coluna_final: str, fonte: str) -> pd.DataFrame:
    df = padronizar_base(df, fonte)
    # Colunas esperadas após slug: periodo, <valor>, projecao
    cols = list(df.columns)
    valor_original = [c for c in cols if c not in ["periodo", "projecao", "fonte_arquivo", "fonte_dados", "municipio_referencia", "uf_referencia"]][0]
    df = df.rename(columns={valor_original: valor_coluna_final})
    df = converter_periodo_mensal(df, "periodo")
    df[valor_coluna_final] = pd.to_numeric(df[valor_coluna_final], errors="coerce")
    if "projecao" in df.columns:
        df["projecao"] = pd.to_numeric(df["projecao"], errors="coerce").fillna(0).astype(int)
        df["tipo_valor"] = df["projecao"].map(lambda x: "Projeção" if x == 1 else "Observado")
    else:
        df["projecao"] = 0
        df["tipo_valor"] = "Observado"
    return df


def preparar_evolucao_simples(df: pd.DataFrame, valor_coluna_final: str, fonte: str) -> pd.DataFrame:
    df = padronizar_base(df, fonte)
    cols = [c for c in df.columns if c not in ["fonte_arquivo", "fonte_dados", "municipio_referencia", "uf_referencia"]]
    df = df.rename(columns={cols[0]: "periodo", cols[1]: valor_coluna_final})
    df = converter_periodo_mensal(df, "periodo")
    df[valor_coluna_final] = pd.to_numeric(df[valor_coluna_final], errors="coerce")
    return df


def preparar_sazonalidade(df: pd.DataFrame, valor_coluna_final: str, fonte: str) -> pd.DataFrame:
    df = padronizar_base(df, fonte)
    cols = [c for c in df.columns if c not in ["fonte_arquivo", "fonte_dados", "municipio_referencia", "uf_referencia"]]
    df = df.rename(columns={cols[0]: "mes_nome", cols[1]: valor_coluna_final})
    df["mes_nome"] = df["mes_nome"].astype(str).str.strip()
    df["mes"] = df["mes_nome"].map(MESES_ORDEM).astype("Int64")
    df[valor_coluna_final] = pd.to_numeric(df[valor_coluna_final], errors="coerce")
    return df.sort_values("mes")


def adicionar_long(lista: list[pd.DataFrame], df: pd.DataFrame, eixo: str, indicador: str, categoria_col: str, valor_col: str, unidade: str):
    """Adiciona um indicador na base consolidada em formato longo, evitando colunas duplicadas."""
    tmp = df.copy()

    base_cols = ["periodo", "ano", "mes", "mes_nome", "data_referencia", "tipo_valor", "municipio_referencia", "uf_referencia", "fonte_dados", "fonte_arquivo"]
    keep_cols = []
    for col in base_cols:
        if col in tmp.columns and col not in keep_cols:
            keep_cols.append(col)

    out = tmp[keep_cols].copy()
    out["categoria"] = tmp[categoria_col].astype(str) if categoria_col in tmp.columns else indicador
    out["valor"] = pd.to_numeric(tmp[valor_col], errors="coerce") if valor_col in tmp.columns else pd.NA
    out["eixo"] = eixo
    out["indicador"] = indicador
    out["unidade"] = unidade
    lista.append(out)


def gerar_dim_calendario(dataframes: list[pd.DataFrame]) -> pd.DataFrame:
    datas = []
    for df in dataframes:
        if "data_referencia" in df.columns:
            datas.extend(df["data_referencia"].dropna().tolist())
    if not datas:
        return pd.DataFrame()
    inicio = pd.Timestamp(min(datas)).to_period("M").to_timestamp()
    fim = pd.Timestamp(max(datas)).to_period("M").to_timestamp()
    calendario = pd.DataFrame({"data_referencia": pd.date_range(inicio, fim, freq="MS")})
    calendario["ano"] = calendario["data_referencia"].dt.year
    calendario["mes"] = calendario["data_referencia"].dt.month
    calendario["mes_nome"] = calendario["mes"].map({v: k for k, v in MESES_ORDEM.items()})
    calendario["ano_mes"] = calendario["data_referencia"].dt.strftime("%Y-%m")
    calendario["trimestre"] = "T" + calendario["data_referencia"].dt.quarter.astype(str)
    return calendario


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/caravelas", help="Pasta com CSVs brutos")
    parser.add_argument("--output", default="data/processed", help="Pasta para CSVs tratados e banco SQLite")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    bases: dict[str, pd.DataFrame] = {}
    long_parts: list[pd.DataFrame] = []

    def load(nomes: list[str]) -> tuple[Path, pd.DataFrame] | tuple[None, None]:
        caminho = primeiro_existente(input_dir, nomes)
        if caminho is None:
            print(f"[AVISO] Arquivo não encontrado: {nomes}")
            return None, None
        return caminho, ler_csv_robusto(caminho)

    # Empregabilidade
    caminho, df = load(["evolucao-saldo-empregos.csv"])
    if df is not None:
        bases["base_evolucao_saldo_empregos"] = preparar_evolucao_simples(df, "saldo_empregos", caminho.name)
        adicionar_long(long_parts, bases["base_evolucao_saldo_empregos"], "Empregabilidade", "Saldo de empregos", "periodo", "saldo_empregos", "empregos")

    caminho, df = load(["evolucao-saldo-empregos-com-projecao.csv"])
    if df is not None:
        bases["base_evolucao_saldo_empregos_com_projecao"] = preparar_evolucao_com_projecao(df, "saldo_empregos", caminho.name)
        adicionar_long(long_parts, bases["base_evolucao_saldo_empregos_com_projecao"], "Empregabilidade", "Saldo de empregos com projeção", "periodo", "saldo_empregos", "empregos")

    caminho, df = load(["setores-saldo-de-empregos.csv"])
    if df is not None:
        bases["base_setores_saldo_empregos"] = preparar_ranking(df, "setor", "saldo_empregos", caminho.name)
        adicionar_long(long_parts, bases["base_setores_saldo_empregos"], "Empregabilidade", "Saldo de empregos por setor", "setor", "saldo_empregos", "empregos")

    caminho, df = load(["sazonalidade-saldo-de-empregos.csv", "saonalidade-saldo-de-empregos.csv"])
    if df is not None:
        bases["base_sazonalidade_saldo_empregos"] = preparar_sazonalidade(df, "saldo_empregos_medio", caminho.name)
        adicionar_long(long_parts, bases["base_sazonalidade_saldo_empregos"], "Empregabilidade", "Sazonalidade do saldo de empregos", "mes_nome", "saldo_empregos_medio", "empregos")

    # Empreendedorismo
    caminho, df = load(["ranking-empresas-abertura.csv", "ranking-cidades-novas-empresas.csv"])
    if df is not None:
        bases["base_ranking_empresas_abertura"] = preparar_ranking(df, "municipio", "novas_empresas", caminho.name, municipio=None)
        adicionar_long(long_parts, bases["base_ranking_empresas_abertura"], "Empreendedorismo", "Novas empresas por município", "municipio", "novas_empresas", "empresas")

    caminho, df = load(["setores-novas-empresas.csv"])
    if df is not None:
        bases["base_setores_novas_empresas"] = preparar_ranking(df, "setor", "novas_empresas", caminho.name)
        adicionar_long(long_parts, bases["base_setores_novas_empresas"], "Empreendedorismo", "Novas empresas por setor", "setor", "novas_empresas", "empresas")

    caminho, df = load(["evolucao-mei.csv"])
    if df is not None:
        bases["base_evolucao_mei"] = preparar_evolucao_simples(df, "meis", caminho.name)
        adicionar_long(long_parts, bases["base_evolucao_mei"], "Empreendedorismo", "Evolução de MEIs", "periodo", "meis", "MEIs")

    # Demografia
    caminho, df = load(["evolucao-populacao.csv"])
    if df is not None:
        tmp = padronizar_base(df, caminho.name)
        cols = [c for c in tmp.columns if c not in ["fonte_arquivo", "fonte_dados", "municipio_referencia", "uf_referencia"]]
        tmp = tmp.rename(columns={cols[0]: "periodo", cols[1]: "populacao"})
        tmp = converter_periodo_anual(tmp, "periodo")
        tmp["populacao"] = pd.to_numeric(tmp["populacao"], errors="coerce")
        bases["base_evolucao_populacao"] = tmp
        adicionar_long(long_parts, tmp, "Demografia", "Evolução populacional", "periodo", "populacao", "pessoas")

    caminho, df = load(["indicadores_demograficos.csv"])
    if df is not None:
        bases["base_indicadores_demograficos"] = preparar_ranking(df, "faixa_etaria", "participacao", caminho.name)
        bases["base_indicadores_demograficos"]["participacao_percentual"] = bases["base_indicadores_demograficos"]["participacao"] * 100
        adicionar_long(long_parts, bases["base_indicadores_demograficos"], "Demografia", "Distribuição por faixa etária", "faixa_etaria", "participacao", "proporção")

    caminho, df = load(["comparativo-municipios.csv"])
    if df is not None:
        bases["base_comparativo_municipios"] = preparar_ranking(df, "municipio", "populacao", caminho.name, municipio=None)
        adicionar_long(long_parts, bases["base_comparativo_municipios"], "Demografia", "População por município", "municipio", "populacao", "pessoas")

    caminho, df = load(["urbanizacao.csv"])
    if df is not None:
        bases["base_urbanizacao"] = preparar_ranking(df, "municipio", "grau_urbanizacao", caminho.name, municipio=None)
        bases["base_urbanizacao"]["grau_urbanizacao_percentual"] = bases["base_urbanizacao"]["grau_urbanizacao"] * 100
        adicionar_long(long_parts, bases["base_urbanizacao"], "Demografia", "Grau de urbanização por município", "municipio", "grau_urbanizacao", "proporção")

    caminho, df = load(["domicilios.csv"])
    if df is not None:
        bases["base_domicilios"] = preparar_ranking(df, "tipo_domicilio", "moradores", caminho.name)
        adicionar_long(long_parts, bases["base_domicilios"], "Demografia", "Moradores por tipo de domicílio", "tipo_domicilio", "moradores", "pessoas")

    # Economia/renda
    caminho, df = load(["composicao-da-renda.csv"])
    if df is not None:
        bases["base_composicao_renda"] = preparar_ranking(df, "classe_renda", "participacao_percentual", caminho.name)
        adicionar_long(long_parts, bases["base_composicao_renda"], "Renda", "Composição da renda", "classe_renda", "participacao_percentual", "percentual")

    caminho, df = load(["evolucao-pib.csv"])
    if df is not None:
        tmp = padronizar_base(df, caminho.name)
        cols = [c for c in tmp.columns if c not in ["fonte_arquivo", "fonte_dados", "municipio_referencia", "uf_referencia"]]
        tmp = tmp.rename(columns={cols[0]: "periodo", cols[1]: "pib"})
        tmp = converter_periodo_anual(tmp, "periodo")
        tmp["pib"] = pd.to_numeric(tmp["pib"], errors="coerce")
        bases["base_evolucao_pib"] = tmp
        adicionar_long(long_parts, tmp, "Economia", "Evolução do PIB", "periodo", "pib", "R$")

    caminho, df = load(["evolucao-rendimentos-declarados.csv"])
    if df is not None:
        tmp = padronizar_base(df, caminho.name)
        tmp = tmp.rename(columns={"periodo": "periodo"})
        tmp = converter_periodo_anual(tmp, "periodo")
        for col in ["rendimentos_tributaveis", "bens_declarados"]:
            if col in tmp.columns:
                tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
        bases["base_evolucao_rendimentos_declarados"] = tmp
        if "rendimentos_tributaveis" in tmp.columns:
            adicionar_long(long_parts, tmp, "Renda", "Rendimentos tributáveis declarados", "periodo", "rendimentos_tributaveis", "R$")
        if "bens_declarados" in tmp.columns:
            adicionar_long(long_parts, tmp, "Renda", "Bens declarados", "periodo", "bens_declarados", "R$")

    caminho, df = load(["evolucao-gastos-declarados.csv"])
    if df is not None:
        tmp = padronizar_base(df, caminho.name)
        tmp = converter_periodo_mensal(tmp, "periodo")
        for col in ["poupanca", "credito", "financiamentos_imobiliarios"]:
            if col in tmp.columns:
                tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
        bases["base_evolucao_gastos_declarados"] = tmp
        for col, label in [("poupanca", "Poupança declarada"), ("credito", "Crédito declarado"), ("financiamentos_imobiliarios", "Financiamentos imobiliários declarados")]:
            if col in tmp.columns:
                adicionar_long(long_parts, tmp, "Financeiro", label, "periodo", col, "R$")

    # PIX
    caminho, df = load(["evolucao-transferencias-pix.csv"])
    if df is not None:
        bases["base_evolucao_transferencias_pix"] = preparar_evolucao_com_projecao(df, "transferencias_pix", caminho.name)
        adicionar_long(long_parts, bases["base_evolucao_transferencias_pix"], "Financeiro", "Transferências PIX com projeção", "periodo", "transferencias_pix", "R$")

    caminho, df = load(["sazonalidade-transferencias-pix.csv", "saonalidade-transferencias-pix.csv"])
    if df is not None:
        bases["base_sazonalidade_transferencias_pix"] = preparar_sazonalidade(df, "valor_medio_transferencias_pix", caminho.name)
        adicionar_long(long_parts, bases["base_sazonalidade_transferencias_pix"], "Financeiro", "Sazonalidade de transferências PIX", "mes_nome", "valor_medio_transferencias_pix", "R$")

    # Vulnerabilidade
    caminho, df = load(["vulnerabilidade-social.csv"])
    if df is not None:
        tmp = padronizar_base(df, caminho.name)
        tmp = converter_periodo_mensal(tmp, "periodo")
        for col in ["pobreza", "extrema_pobreza"]:
            if col in tmp.columns:
                tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
        bases["base_vulnerabilidade_social"] = tmp
        if "pobreza" in tmp.columns:
            adicionar_long(long_parts, tmp, "Vulnerabilidade", "Pessoas em situação de pobreza", "periodo", "pobreza", "pessoas")
        if "extrema_pobreza" in tmp.columns:
            adicionar_long(long_parts, tmp, "Vulnerabilidade", "Pessoas em situação de extrema pobreza", "periodo", "extrema_pobreza", "pessoas")

    # Estabelecimentos
    caminho, df = load(["estabelecimentos.csv"])
    if df is not None:
        bases["base_estabelecimentos"] = preparar_ranking(df, "municipio", "taxa_estabelecimentos", caminho.name, municipio=None)
        adicionar_long(long_parts, bases["base_estabelecimentos"], "Empreendedorismo", "Taxa de estabelecimentos por município", "municipio", "taxa_estabelecimentos", "taxa")

    # Base consolidada
    if long_parts:
        consolidada = pd.concat(long_parts, ignore_index=True, sort=False)
        consolidada["valor"] = pd.to_numeric(consolidada["valor"], errors="coerce")
        consolidada["data_processamento"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bases["base_indicadores_consolidada_long"] = consolidada

    # Dimensão calendário
    dim_cal = gerar_dim_calendario(list(bases.values()))
    if not dim_cal.empty:
        bases["dim_calendario"] = dim_cal

    # Exporta CSV e SQLite
    db_path = output_dir / "databauru.db"
    if db_path.exists():
        db_path.unlink()

    con = sqlite3.connect(db_path)
    for nome, df in bases.items():
        csv_path = output_dir / f"{nome}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        df.to_sql(nome, con, if_exists="replace", index=False)
        print(f"[OK] {nome}: {len(df)} linhas -> {csv_path}")
    con.close()
    print(f"[OK] Banco SQLite gerado: {db_path}")


if __name__ == "__main__":
    main()
