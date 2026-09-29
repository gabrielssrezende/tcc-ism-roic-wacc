"""
03 - Cálculo das variáveis

Equações (numeração do TCC):
  (1) IS&M  = SM / R
  (2) S     = ROIC - WACC
  (3) ROIC  = NOPAT / CI
  (4) NOPAT = EBIT x (1 - t)
  (5) CI    = PL + D - C
  (6) WACC  = E/(E+D) x Ke + D/(E+D) x Kd x (1 - t)
  (7) Ke    = Rf + bL x ERP
  (8) bL    = bU x [1 + (1 - t) x D/E]   (Hamada, 1972)
  (9) Kd    = J / D

Tratamentos:
  - t: alíquota efetiva (imposto / EBT) winsorizada em [0, 1]; com EBT <= 0 ou ausente,
    alíquota federal de 35% até 2017 e 21% a partir de 2018;
  - D ausente = 0; se D > 0 e J ausente, a observação fica sem WACC;
  - pesos do WACC a valores contábeis; com PL <= 0, D/E = 0 e WACC = Ke;
  - ROIC e spread só com CI > 0; o spread também exige IS&M.

Entradas: dados/dados_financeiros_brutos.csv, dados/parametros_damodaran.csv
Saída:    dados/dados_variaveis.csv
"""

import numpy as np
import pandas as pd

from config import (DADOS_BRUTOS, PARAMETROS, DADOS_VARIAVEIS,
                    ALIQ_ESTATUTARIA_ATE_2017, ALIQ_ESTATUTARIA_DESDE_2018,
                    LIMITES_ALIQ_EFETIVA)

df = pd.read_csv(DADOS_BRUTOS)
par = pd.read_csv(PARAMETROS)
df = df.merge(par, on="ano", how="left")

# (1) IS&M
df["ism"] = df["sm_expense"] / df["receita"]

# Alíquota de imposto
aliq_efetiva = df["imposto"] / df["ebt"]
usa_estatutaria = ~((df["ebt"] > 0) & aliq_efetiva.notna())
aliq_estatutaria = np.where(df["ano"] <= 2017, ALIQ_ESTATUTARIA_ATE_2017, ALIQ_ESTATUTARIA_DESDE_2018)
df["tax_rate"] = np.where(usa_estatutaria, aliq_estatutaria, aliq_efetiva.clip(*LIMITES_ALIQ_EFETIVA))
df["tax_rate_origem"] = np.where(usa_estatutaria, "estatutaria",
                                 np.where((aliq_efetiva < LIMITES_ALIQ_EFETIVA[0]) | (aliq_efetiva > LIMITES_ALIQ_EFETIVA[1]),
                                          "efetiva_limitada", "efetiva"))

# (4) NOPAT e (5) capital investido
df["nopat"] = df["ebit"] * (1 - df["tax_rate"])
df["divida_total"] = df["divida_total"].fillna(0)
df["capital_investido"] = df["pl"] + df["divida_total"] - df["caixa"]

# (3) ROIC, só com capital investido positivo
ci_valido = df["capital_investido"] > 0
df["roic"] = np.where(ci_valido, df["nopat"] / df["capital_investido"], np.nan)

# (8) beta realavancado
df["de_ratio"] = np.where(df["pl"] > 0, df["divida_total"] / df["pl"], 0.0)
df["beta_levered"] = df["beta_unlevered"] * (1 + (1 - df["tax_rate"]) * df["de_ratio"])

# (7) custo do capital próprio
df["ke"] = df["rf"] + df["beta_levered"] * df["erp"]

# (9) custo da dívida
kd = (df["juros"] / df["divida_total"]).clip(lower=0)
df["kd_pretax"] = np.where(df["divida_total"] > 0, kd, 0.0)
df["kd"] = df["kd_pretax"] * (1 - df["tax_rate"])

# (6) WACC a valores contábeis
# com PL <= 0, D/E = 0 no beta e, pela mesma razão, peso de 100% para o capital próprio
df["valor_total"] = df["pl"] + df["divida_total"]
pl_pos = df["pl"] > 0
df["peso_e"] = np.where(pl_pos, df["pl"] / df["valor_total"], 1.0)
df["peso_d"] = np.where(pl_pos, df["divida_total"] / df["valor_total"], 0.0)
df["wacc"] = df["peso_e"] * df["ke"] + df["peso_d"] * df["kd"]

# (2) spread, só quando o IS&M também existe
df["spread"] = np.where(df["ism"].notna(), df["roic"] - df["wacc"], np.nan)

# Motivo de exclusão da base de análise
def motivo(r):
    if pd.isna(r["ism"]):
        return "dados insuficientes: S&M ausente"
    if pd.isna(r["capital_investido"]):
        return "dados insuficientes: caixa ausente"
    if r["capital_investido"] <= 0:
        return "capital investido <= 0"
    if pd.isna(r["wacc"]):
        return "dados insuficientes: juros ausentes com divida > 0"
    return ""
df["motivo_exclusao"] = df.apply(motivo, axis=1)

df.to_csv(DADOS_VARIAVEIS, index=False, encoding="utf-8-sig")

print(f"Observações empresa-ano:          {len(df)}")
print(f"Com spread calculável:            {df['spread'].notna().sum()}")
print(f"Alíquota estatutária aplicada:    {usa_estatutaria.sum()}")
print(f"Alíquota efetiva limitada:        {(df['tax_rate_origem'] == 'efetiva_limitada').sum()}")
print("\nExclusões:")
print(df.loc[df["motivo_exclusao"] != "", "motivo_exclusao"].value_counts().to_string())
print(f"\nArquivo salvo: {DADOS_VARIAVEIS}")
