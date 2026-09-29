"""
05 - Testes de hipóteses e de robustez (bilaterais, alfa = 5%)

  H1: Mann-Whitney, spread do grupo Alto vs. Baixo
  H2: Spearman, IS&M x spread (amostra completa)
  H3: Spearman, ano x spread (grupo Alto)

Robustez: Pearson; IS&M_t x spread em t+1 a t+3; IS&M x ROIC antes de S&M;
k = 3 (Kruskal-Wallis e Mann-Whitney com Bonferroni); amostra sem PTC, BLKB e PRGS;
ano x spread centrado na mediana de cada empresa. Também calcula a tendência do
IS&M do grupo Alto e o Spearman ano x spread por empresa (>= 5 observações válidas).

Entrada: dados/dados_com_cluster.csv
Saídas:  resultados/testes_estatisticos.csv, resultados/tendencia_por_empresa.csv
"""

import pandas as pd
from scipy import stats

from config import DADOS_CLUSTER, RESULTADOS, ALFA, ROBUSTEZ_EXCLUIR_MA

df = pd.read_csv(DADOS_CLUSTER)
v = df[df["spread"].notna()].copy()   # base de análise
A = v[v["grupo"] == "Alto"]; B = v[v["grupo"] == "Baixo"]

linhas = []
def registra(bloco, teste, n, estat_nome, estat, p, obs=""):
    linhas.append({"bloco": bloco, "teste": teste, "n": n, "estatistica": estat_nome,
                   "valor": round(float(estat), 4), "p_valor": float(p),
                   "resultado": "Rejeita H0" if p < ALFA else "Não rejeita H0", "observacao": obs})

# Pressupostos
for nome, serie in [("spread", v["spread"]), ("IS&M", v["ism"])]:
    w, p = stats.shapiro(serie)
    registra("Pressuposto", f"Shapiro-Wilk ({nome})", len(serie), "W", w, p, "H0: normalidade")

# H1
mw = stats.mannwhitneyu(A["spread"], B["spread"], alternative="two-sided")
rrb = 1 - 2 * mw.statistic / (len(A) * len(B))
registra("H1", "Mann-Whitney: Alto vs. Baixo IS&M", f"{len(A)} / {len(B)}", "U", mw.statistic, mw.pvalue,
         f"mediana Alto = {A['spread'].median():.4f}; mediana Baixo = {B['spread'].median():.4f}; "
         f"correlação bisserial de postos = {abs(rrb):.3f}")

# H2
s = stats.spearmanr(v["ism"], v["spread"])
registra("H2", "Spearman: IS&M × spread (amostra completa)", len(v), "rho", s.statistic, s.pvalue)

# H3
s = stats.spearmanr(A["ano"], A["spread"])
registra("H3", "Spearman: ano × spread (Alto IS&M)", len(A), "rho", s.statistic, s.pvalue)

# Complementares por grupo
for g, x in [("Alto", A), ("Baixo", B)]:
    s = stats.spearmanr(x["ism"], x["spread"])
    registra("Por grupo", f"Spearman: IS&M × spread ({g} IS&M)", len(x), "rho", s.statistic, s.pvalue)
s = stats.spearmanr(B["ano"], B["spread"])
registra("Por grupo", "Spearman: ano × spread (Baixo IS&M)", len(B), "rho", s.statistic, s.pvalue)

# Robustez: Pearson
r = stats.pearsonr(v["ism"], v["spread"])
registra("Robustez", "Pearson: IS&M × spread", len(v), "r", r.statistic, r.pvalue)

# Robustez: defasagens (observações seguintes da mesma empresa)
vs = v.sort_values(["ticker", "ano"]).copy()
for L in (1, 2, 3):
    x = vs.assign(spread_fut=vs.groupby("ticker")["spread"].shift(-L)).dropna(subset=["spread_fut"])
    s = stats.spearmanr(x["ism"], x["spread_fut"])
    registra("Robustez", f"Spearman: IS&M_t × spread_t+{L}", len(x), "rho", s.statistic, s.pvalue)

# Robustez: efeito contábil da despesa de S&M
vs["roic_antes_sm"] = (vs["ebit"] + vs["sm_expense"]) * (1 - vs["tax_rate"]) / vs["capital_investido"]
s = stats.spearmanr(vs["ism"], vs["roic_antes_sm"])
med = vs.groupby("grupo")["roic_antes_sm"].median()
registra("Robustez", "Spearman: IS&M × ROIC antes de S&M", len(vs), "rho", s.statistic, s.pvalue,
         f"mediana Alto = {med['Alto']:.4f}; mediana Baixo = {med['Baixo']:.4f}")

# Robustez: k = 3
g3 = {g: x["spread"] for g, x in v.groupby("grupo_k3")}
kw = stats.kruskal(*g3.values())
registra("Robustez k=3", "Kruskal-Wallis (Alto / Médio / Baixo)",
         f"{len(g3['Alto'])} / {len(g3['Médio'])} / {len(g3['Baixo'])}", "H", kw.statistic, kw.pvalue)
for a, b in [("Alto", "Médio"), ("Alto", "Baixo"), ("Médio", "Baixo")]:
    r = stats.mannwhitneyu(g3[a], g3[b], alternative="two-sided")
    registra("Robustez k=3", f"Mann-Whitney: {a} vs. {b} (Bonferroni)", f"{len(g3[a])} / {len(g3[b])}",
             "U", r.statistic, min(1.0, r.pvalue * 3), f"p sem ajuste = {r.pvalue:.6f}")

# Robustez: sem as empresas com aquisições relevantes frente à receita
vr = v[~v["ticker"].isin(ROBUSTEZ_EXCLUIR_MA)]
Ar, Br = vr[vr["grupo"] == "Alto"], vr[vr["grupo"] == "Baixo"]
rot = "sem " + "/".join(ROBUSTEZ_EXCLUIR_MA)
r = stats.mannwhitneyu(Ar["spread"], Br["spread"], alternative="two-sided")
registra("Robustez M&A", f"H1 {rot}: Mann-Whitney Alto vs. Baixo", f"{len(Ar)} / {len(Br)}", "U", r.statistic, r.pvalue,
         f"mediana Alto = {Ar['spread'].median():.4f}; mediana Baixo = {Br['spread'].median():.4f}")
s2 = stats.spearmanr(vr["ism"], vr["spread"])
registra("Robustez M&A", f"H2 {rot}: Spearman IS&M × spread", len(vr), "rho", s2.statistic, s2.pvalue)
# H3 só muda se alguma dessas empresas for do grupo Alto
if set(ROBUSTEZ_EXCLUIR_MA) & set(A["ticker"]):
    s3 = stats.spearmanr(Ar["ano"], Ar["spread"])
    registra("Robustez M&A", f"H3 {rot}: Spearman ano × spread (Alto)", len(Ar), "rho", s3.statistic, s3.pvalue)

# Robustez: tendência intraempresa (spread centrado na mediana de cada empresa)
v["spread_centrado"] = v["spread"] - v.groupby("ticker")["spread"].transform("median")
for g in ("Alto", "Baixo"):
    x = v[v["grupo"] == g]
    s = stats.spearmanr(x["ano"], x["spread_centrado"])
    registra("Robustez intraempresa", f"Spearman: ano × spread centrado na empresa ({g} IS&M)", len(x), "rho",
             s.statistic, s.pvalue, "spread menos a mediana do spread da própria empresa")

# Tendência do IS&M do grupo Alto (todas as observações coletadas)
alto_todas = df[df["grupo"] == "Alto"]
s = stats.spearmanr(alto_todas["ano"], alto_todas["ism"])
registra("Complementar", "Spearman: ano × IS&M (Alto IS&M, obs. coletadas)", len(alto_todas), "rho", s.statistic, s.pvalue)

res = pd.DataFrame(linhas)
res.to_csv(RESULTADOS / "testes_estatisticos.csv", index=False, encoding="utf-8-sig")

# Tendência do spread por empresa
tend = []
for t, x in v.groupby("ticker"):
    if len(x) >= 5:
        s = stats.spearmanr(x["ano"], x["spread"])
        tend.append({"ticker": t, "grupo": x["grupo"].iloc[0], "n": len(x),
                     "rho_ano_spread": round(s.statistic, 4), "p_valor": round(s.pvalue, 4)})
pd.DataFrame(tend).to_csv(RESULTADOS / "tendencia_por_empresa.csv", index=False, encoding="utf-8-sig")

pd.set_option("display.width", 200)
print(res[["bloco", "teste", "n", "estatistica", "valor", "p_valor", "resultado"]].to_string(index=False))
print(f"\nArquivos salvos em: {RESULTADOS}")
