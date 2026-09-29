"""
02 - Coleta dos dados financeiros (SEC XBRL Company Facts API)

Extrai dos 10-Ks de cada empresa incluída na amostra os valores anuais de 2015 a 2024.
Os conceitos US-GAAP de cada variável estão em CONCEITOS, em ordem de prioridade:
usa-se o primeiro disponível no exercício.

Regras de extração:
  - contas de resultado: só períodos de 330 a 400 dias (exclui valores trimestrais);
  - contas de balanço: saldo na data de encerramento do exercício;
  - havendo mais de um registro, vale o do 10-K arquivado mais recentemente;
  - dívida total: maior valor entre o conceito de dívida total e a soma curto + longo prazo.

Ajustes manuais, aplicados no fim da coleta:
  dados/ajustes_manuais_sm.csv            S&M da Paycom (sem SellingAndMarketingExpense no XBRL)
  dados/ajustes_manuais_divida_juros.csv  dívida e juros sem conceito padrão, com a fonte de cada valor

Saídas: dados/dados_financeiros_brutos.csv e dados/diagnostico_divida.csv
(todos os conceitos de dívida divulgados por empresa-ano, para conferência).
Requer internet.
"""

import re
import time
from datetime import date

import pandas as pd
import requests

from config import AMOSTRA_CANDIDATAS, DADOS_BRUTOS, AJUSTES_MANUAIS_SM, AJUSTES_MANUAIS_DIVIDA_JUROS, ANOS

HEADERS = {"User-Agent": "Gabriel Rezende gabriel.rezende.tcc@gmail.com"}  # exigido pela SEC

CONCEITOS = {
    "receita":    ["RevenueFromContractWithCustomerExcludingAssessedTax",
                   "Revenues", "RevenueFromContractWithCustomerIncludingAssessedTax",
                   "SalesRevenueNet"],
    "sm_expense": ["SellingAndMarketingExpense"],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "ebit":       ["OperatingIncomeLoss"],
    "imposto":    ["IncomeTaxExpenseBenefit"],
    "ebt":        ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                   "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "pl":         ["StockholdersEquity",
                   "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "divida_total_tag": ["LongTermDebt", "DebtLongtermAndShorttermCombinedAmount",
                         "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
                         "ConvertibleDebt", "ConvertibleNotesPayable", "SeniorNotes", "DebtInstrumentCarryingAmount"],
    "divida_lp":  ["LongTermDebtNoncurrent", "ConvertibleDebtNoncurrent",
                   "ConvertibleLongTermNotesPayable", "LongTermNotesPayable", "SeniorLongTermNotes",
                   "LongTermDebtAndCapitalLeaseObligations", "LongTermLineOfCredit",
                   "UnsecuredLongTermDebt", "SecuredLongTermDebt"],
    "divida_cp":  ["LongTermDebtCurrent", "ConvertibleDebtCurrent", "ConvertibleNotesPayableCurrent",
                   "DebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent", "NotesPayableCurrent",
                   "ShortTermBorrowings", "LineOfCredit", "UnsecuredDebtCurrent", "SecuredDebtCurrent"],
    "caixa":      ["CashAndCashEquivalentsAtCarryingValue",
                   "CashCashEquivalentsAndShortTermInvestments"],
    "juros":      ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"],
    "ativo_total": ["Assets"],
    "dda":        ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"],
}


def buscar_company_facts(cik):
    """Baixa todos os fatos XBRL de uma empresa."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
    r = requests.get(url, headers=HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else None


VARIAVEIS_FLUXO = {"receita", "sm_expense", "rd_expense", "ebit", "imposto", "ebt", "juros", "dda"}


def _dias(inicio, fim):
    return (date.fromisoformat(fim) - date.fromisoformat(inicio)).days


def ano_fiscal(fim):
    """Ano do exercício; exercícios de 52/53 semanas encerrados até 7 de janeiro contam no ano anterior."""
    ano = int(fim[:4])
    if fim[5:7] == "01" and int(fim[8:10]) <= 7:
        ano -= 1
    return ano


def extrair_valor_anual(facts, conceito, ano, fluxo, fim_exercicio=None):
    """Valor do conceito no exercício que termina em `ano`. Retorna (valor, data_fim) ou (None, None)."""
    try:
        dados = facts["facts"]["us-gaap"][conceito]["units"]["USD"]
    except (KeyError, TypeError):
        return None, None

    dados = [d for d in dados if d.get("form") == "10-K" and d.get("end") and ano_fiscal(d["end"]) == ano]
    if fluxo:
        candidatos = [d for d in dados if d.get("start") and 330 <= _dias(d["start"], d["end"]) <= 400]
    else:
        instantes = [d for d in dados if not d.get("start")]
        candidatos = [d for d in instantes if d["end"] == fim_exercicio] if fim_exercicio else []
        if not candidatos and instantes:
            ultima = max(d["end"] for d in instantes)
            candidatos = [d for d in instantes if d["end"] == ultima]
    if not candidatos:
        return None, None
    escolhido = sorted(candidatos, key=lambda x: x.get("filed", ""), reverse=True)[0]
    return escolhido.get("val"), escolhido.get("end")


PADRAO_DIVIDA = re.compile(r"(Debt|Notes|Convertible|Borrowing|LineOfCredit)")
EXCLUIR_DIVIDA = re.compile(r"(Proceeds|Repayment|Payment|Issuance|Amortization|Interest|FairValue|Unamortized|"
                            r"Discount|Premium|Covenant|Percentage|Rate|Maturit|Extinguishment|Conversion|Receivable|"
                            r"Increase|Decrease|Expense|Gain|Loss|Securities|Investment)")
diagnostico = []


def registrar_diagnostico(ticker, ano, facts, fim_exercicio):
    """Guarda os saldos de dívida divulgados no 10-K na data de encerramento do exercício."""
    if not fim_exercicio:
        return
    for conceito, dados in facts.get("facts", {}).get("us-gaap", {}).items():
        if not PADRAO_DIVIDA.search(conceito) or EXCLUIR_DIVIDA.search(conceito):
            continue
        for d in dados.get("units", {}).get("USD", []):
            if d.get("form") == "10-K" and not d.get("start") and d.get("end") == fim_exercicio:
                diagnostico.append({"ticker": ticker, "ano": ano, "conceito": conceito, "valor": d.get("val"),
                                    "filed": d.get("filed")})
                break


def coletar_empresa(row):
    """Coleta os dados de uma empresa para 2015-2024."""
    ticker, cik, nome, perfil = row["ticker"], row["cik"], row["nome"], row["perfil_ism_esperado"]
    print(f"\n  {ticker:6s} ({nome[:40]})")

    facts = buscar_company_facts(cik)
    if facts is None:
        print("         sem resposta da API")
        return []

    registros = []
    for ano in ANOS:
        rec = {"ticker": ticker, "nome": nome, "cik": cik, "perfil_ism_esperado": perfil, "ano": ano}
        fim_exercicio = None
        # contas de resultado primeiro, para identificar a data de encerramento do exercício
        ordem = sorted(CONCEITOS, key=lambda v: v not in VARIAVEIS_FLUXO)
        for var in ordem:
            valor, conceito_usado = None, None
            for conceito in CONCEITOS[var]:
                valor, fim = extrair_valor_anual(facts, conceito, ano, var in VARIAVEIS_FLUXO, fim_exercicio)
                if valor is not None:
                    conceito_usado = conceito
                    if var in ("receita", "ebit") and fim_exercicio is None:
                        fim_exercicio = fim
                    break
            rec[var] = valor
            rec[f"{var}_conceito_xbrl"] = conceito_usado
        rec["fim_exercicio"] = fim_exercicio
        soma = (rec["divida_lp"] or 0) + (rec["divida_cp"] or 0)
        total_tag = rec["divida_total_tag"] or 0
        rec["divida_total"] = max(total_tag, soma)
        rec["divida_total_origem"] = ("conceito de dívida total" if total_tag >= soma and total_tag > 0 else
                                      "soma longo + curto prazo" if soma > 0 else "sem dívida divulgada")
        registrar_diagnostico(ticker, ano, facts, fim_exercicio)

        if rec["receita"] is not None or rec["ebit"] is not None:
            vars_chave = ["receita", "sm_expense", "ebit", "pl", "caixa"]
            n_ok = sum(1 for v in vars_chave if rec[v] is not None)
            rec["completude"] = f"{n_ok}/{len(vars_chave)}"
            print(f"         {ano}: completude {rec['completude']}")
            registros.append(rec)
    return registros


df_amostra = pd.read_csv(AMOSTRA_CANDIDATAS)
df_amostra = df_amostra[df_amostra["incluir"] == "sim"].reset_index(drop=True)

print(f"Empresas na amostra: {len(df_amostra)}")
print("Período: 2015–2024\n")

todos = []
for _, row in df_amostra.iterrows():
    todos.extend(coletar_empresa(row))
    time.sleep(0.5)

df_raw = pd.DataFrame(todos).sort_values(["ticker", "ano"]).reset_index(drop=True)

# Ajuste manual: S&M da Paycom (PAYC)
aj = pd.read_csv(AJUSTES_MANUAIS_SM)
for _, a in aj.iterrows():
    m = (df_raw["ticker"] == a["ticker"]) & (df_raw["ano"] == a["ano"])
    df_raw.loc[m, "sm_expense"] = a["sm_expense"]
    df_raw.loc[m, "sm_expense_conceito_xbrl"] = "SellingAndMarketingExpense_ManualExtraction_10K"

# Ajuste manual: dívida e juros sem conceito padrão
ajd = pd.read_csv(AJUSTES_MANUAIS_DIVIDA_JUROS)
for _, a in ajd.iterrows():
    m = (df_raw["ticker"] == a["ticker"]) & (df_raw["ano"] == a["ano"])
    df_raw.loc[m, a["variavel"]] = a["valor"]
    if a["variavel"] == "divida_total":
        df_raw.loc[m, "divida_total_origem"] = "ajuste manual (balanço do 10-K)"
    else:
        df_raw.loc[m, "juros_conceito_xbrl"] = "ajuste manual (10-K)"

# Colunas em milhões de USD
for col in ["receita", "sm_expense", "rd_expense", "ebit", "imposto", "ebt", "pl",
            "divida_total_tag", "divida_lp", "divida_cp", "divida_total", "caixa", "juros", "ativo_total", "dda"]:
    df_raw[f"{col}_M"] = df_raw[col] / 1_000_000

df_raw.to_csv(DADOS_BRUTOS, index=False, encoding="utf-8-sig")
pd.DataFrame(diagnostico).to_csv(DADOS_BRUTOS.parent / "diagnostico_divida.csv", index=False, encoding="utf-8-sig")

alerta = df_raw[(df_raw["divida_total"] == 0) & (df_raw["juros"].fillna(0) > 0)]
print(f"\n  Empresa-ano com juros > 0 e dívida = 0: {len(alerta)}")
if len(alerta):
    print("   ", ", ".join(f"{t} ({n})" for t, n in alerta["ticker"].value_counts().items()))
alerta2 = df_raw[(df_raw["divida_total"] > 0) & df_raw["juros"].isna()]
print(f"  Empresa-ano com dívida > 0 e juros ausentes: {len(alerta2)}")
if len(alerta2):
    print("   ", ", ".join(f"{t} {a}" for t, a in zip(alerta2["ticker"], alerta2["ano"])))

print(f"\n  Empresas processadas:   {df_amostra['ticker'].nunique()}")
print(f"  Observações coletadas:  {len(df_raw)}")
print(f"  Arquivo salvo: {DADOS_BRUTOS}")
