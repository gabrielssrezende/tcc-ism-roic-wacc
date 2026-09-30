"""
06 - Tabelas e figuras

Gera as Tabelas 2, 3, 5 e 6 (CSV) e as Figuras 1 a 3 (PNG, 300 dpi).
A Tabela 4 é o próprio resultados/testes_estatisticos.csv.

As Figuras 2 e 3 seguem os critérios de formatação de gráficos do Manual de
Normas do MBA USP/Esalq: sem linhas de grade, sem borda, sem preenchimento e sem
título do gráfico; eixos em linha preta de 1,5 pt; títulos dos eixos em Arial
(ou Liberation Sans, métrica idêntica) tamanho 11 ou menor, na cor preta; figuras
com mais de um painel identificadas por letra maiúscula (A, B) no canto superior
esquerdo de cada painel.

Entradas: dados/amostra_candidatas_expandida.csv, dados/dados_com_cluster.csv,
          resultados/validacao_kmeans.csv, resultados/tendencia_por_empresa.csv
Saídas:   resultados/tabelas/*.csv, resultados/figuras/*.png
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch, Rectangle
import pandas as pd

from config import AMOSTRA_CANDIDATAS, DADOS_CLUSTER, RESULTADOS, TABELAS, FIGURAS

AZUL, LARANJA, CINZA, TINTA, SUAVE, PRETO = "#2a78d6", "#eb6834", "#9a9893", "#0b0b0b", "#52514e", "#000000"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
                     "font.size": 9, "text.color": PRETO, "axes.labelcolor": PRETO,
                     # eixos em linha preta de 1,5 pt (Manual de Normas, Tabela 8)
                     "axes.edgecolor": PRETO, "axes.linewidth": 1.5,
                     "xtick.color": PRETO, "ytick.color": PRETO,
                     "xtick.major.width": 1.5, "ytick.major.width": 1.5,
                     # sem borda, sem preenchimento e sem linhas de grade
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.facecolor": "none", "figure.facecolor": "white", "axes.grid": False})
fmt = lambda x, dec=0: f"{x:.{dec}f}".replace(".", ",").replace("-", "−")

df = pd.read_csv(DADOS_CLUSTER)
v = df[df["spread"].notna()]
A, B = v[v["grupo"] == "Alto"], v[v["grupo"] == "Baixo"]

# Tabela 2
linhas = []
for g in ["Alto", "Baixo"]:
    col = df[df["grupo"] == g]
    linhas.append({"grupo": f"{g} IS&M", "empresas": ", ".join(sorted(col["ticker"].unique())),
                   "n_empresas": col["ticker"].nunique(),
                   "ism_medio": col.groupby("ticker")["ism"].mean().mean(),
                   "obs_coletadas": len(col), "obs_validas": col["spread"].notna().sum()})
pd.DataFrame(linhas).to_csv(TABELAS / "tabela2_composicao_grupos.csv", index=False, encoding="utf-8-sig")

# Tabela 3
def descr(x):
    return {"n_obs": len(x), "ism_media": x["ism"].mean(), "ism_mediana": x["ism"].median(), "ism_dp": x["ism"].std(),
            "roic_media": x["roic"].mean(), "roic_mediana": x["roic"].median(), "roic_dp": x["roic"].std(),
            "wacc_media": x["wacc"].mean(), "spread_media": x["spread"].mean(),
            "spread_mediana": x["spread"].median(), "spread_dp": x["spread"].std(),
            "pct_spread_positivo": (x["spread"] > 0).mean()}
pd.DataFrame({"Alto IS&M": descr(A), "Baixo IS&M": descr(B)}).to_csv(
    TABELAS / "tabela3_estatisticas_descritivas.csv", encoding="utf-8-sig")

# Tabela 5
t5 = v.groupby(["ano", "grupo"])["spread"].agg(["mean", "median", "count"]).unstack("grupo")
t5.columns = [f"{g.lower()}_{m}" for m, g in t5.columns]
t5 = t5[["alto_mean", "alto_median", "alto_count", "baixo_mean", "baixo_median", "baixo_count"]]
t5.to_csv(TABELAS / "tabela5_spread_por_ano.csv", encoding="utf-8-sig")

# Tabela 6
tend = pd.read_csv(RESULTADOS / "tendencia_por_empresa.csv").set_index("ticker")
t6 = df.groupby(["grupo", "ticker"]).agg(obs_coletadas=("ano", "count"), obs_validas=("spread", "count"),
                                         ism_medio=("ism", "mean")).reset_index()
t6 = t6.join(v.groupby("ticker")["spread"].agg(spread_medio="mean",
                                               anos_spread_positivo=lambda s: int((s > 0).sum())), on="ticker")
t6 = t6.join(tend[["rho_ano_spread", "p_valor"]], on="ticker")
t6.sort_values(["grupo", "ism_medio"], ascending=[True, False]).to_csv(
    TABELAS / "tabela6_perfil_empresas.csv", index=False, encoding="utf-8-sig")

# Figura 1 (Sankey — fluxograma do processo de seleção, não é gráfico de dados)
cand = pd.read_csv(AMOSTRA_CANDIDATAS)
exc = cand[cand["incluir"] == "nao"]["motivo"].fillna("")
n_assin = exc.str.contains("assinatura").sum()
n_ma = exc.str.contains("M&A").sum()
n_cap = exc.str.contains("Market cap").sum()
n_sm = exc.str.contains("S&M").sum()
n_cand, n_final = len(cand), (cand["incluir"] == "sim").sum()
n_obs, n_val = len(df), len(v)
n_ci = (df["motivo_exclusao"] == "capital investido <= 0").sum()
n_ins = n_obs - n_val - n_ci

fig, ax = plt.subplots(figsize=(6.3, 4.0)); ax.set_xlim(0, 100); ax.set_ylim(-2, 96); ax.axis("off")
def no(x, y, h, c): ax.add_patch(Rectangle((x, y), 1.8, h, color=c, lw=0))
def fluxo(x0, y0, x1, y1, h, c, a=.35):
    xm = (x0 + x1) / 2
    verts = [(x0, y0), (xm, y0), (xm, y1), (x1, y1), (x1, y1 + h), (xm, y1 + h), (xm, y0 + h), (x0, y0 + h), (x0, y0)]
    codes = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO,
             MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), fc=c, ec="none", alpha=a))
S, X0, X1, X2, y0 = 1.3, 14, 46, 78, 16
h_c = n_cand * S; no(X0, y0, h_c, TINTA)
ax.text(X0 - 1.5, y0 + h_c / 2, f"{n_cand} empresas\ncandidatas\n(SIC, bolsa e\n≥ 5 formulários 10-K)",
        ha="right", va="center", fontsize=8, color=TINTA)
h_f = n_final * S; fluxo(X0 + 1.8, y0, X1, y0, h_f, AZUL, .30); no(X1, y0, h_f, AZUL)
ax.text(X1 + 0.9, y0 - 1.5, f"{n_final} empresas\n{n_obs} obs.", ha="center", va="top", fontsize=8, color=TINTA)
ys, ye = y0 + h_f, y0 + h_f + 3
for n, rot in [(n_sm, "S&M não divulgado separadamente (IS&M incalculável)"),
               (n_cap, "Capitalização de mercado < USD 500 milhões"),
               (n_ma, "Aquisição ≥ USD 5 bi sem 5 exercícios completos"),
               (n_assin, "Receita por assinatura < 60% da receita total")]:
    h = n * S; fluxo(X0 + 1.8, ys, X1, ye, h, CINZA); no(X1, ye, h, CINZA)
    ax.text(X1 + 3, ye + h / 2, f"−{n} empresas: {rot}", va="center", fontsize=7.3, color=SUAVE)
    ys += h; ye += h + 3
esc = h_f / n_obs
assert n_assin + n_ma + n_cap + n_sm == n_cand - n_final, "motivo de exclusão não classificado"
h_v, h_ci, h_in = n_val * esc, n_ci * esc, n_ins * esc
fluxo(X1 + 1.8, y0 + h_f - h_v, X2, y0 + h_f - h_v - 2, h_v, AZUL, .30); no(X2, y0 + h_f - h_v - 2, h_v, AZUL)
ax.text(X2 + 3, y0 + h_f - h_v / 2 - 2, f"{n_val} obs. com spread\ncalculável (amostra\nde análise)",
        va="center", fontsize=7.6, color=TINTA)
fluxo(X1 + 1.8, y0 + h_in, X2, 6.5, h_ci, CINZA); no(X2, 6.5, h_ci, CINZA)
ax.text(X2 + 3, 6.5 + h_ci / 2, f"−{n_ci} obs.: capital investido ≤ 0", va="center", fontsize=7.3, color=SUAVE)
fluxo(X1 + 1.8, y0, X2, 0, h_in, CINZA); no(X2, 0, h_in, CINZA)
ax.text(X2 + 3, h_in / 2, f"−{n_ins} obs.: dados insuficientes", va="center", fontsize=7.3, color=SUAVE)
plt.savefig(FIGURAS / "figura1_selecao_amostra.png", dpi=300, bbox_inches="tight", facecolor="white"); plt.close()

# Figura 2 (silhueta e cotovelo) — painéis A e B, sem título e sem grade
val = pd.read_csv(RESULTADOS / "validacao_kmeans.csv")
fig, axs = plt.subplots(1, 2, figsize=(6.3, 2.4))
for a, col, rot, dec, letra in [(axs[0], "silhueta", "Índice de silhueta", 2, "A"),
                                (axs[1], "inercia", "Inércia", 3, "B")]:
    a.plot(val["k"], val[col], color=AZUL, lw=2, marker="o", ms=6, mec="white", mew=1.5, zorder=3)
    a.plot([val["k"].iloc[0]], [val[col].iloc[0]], "o", color=LARANJA, ms=8, mec="white", mew=1.5, zorder=4)
    for k, y in zip(val["k"], val[col]):
        a.annotate(fmt(y, dec), (k, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
    a.set_xticks(val["k"]); a.set_xlim(val["k"].min() - .4, val["k"].max() + .4)
    a.set_xlabel("Número de grupos (k)", fontsize=9); a.set_ylabel(rot, fontsize=9)
    a.margins(y=.22)
    a.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p, dec=dec: fmt(x, dec)))
    a.text(-0.28, 1.04, letra, transform=a.transAxes, fontsize=11, fontweight="bold", va="bottom", ha="left")
axs[0].axhline(.5, color=CINZA, lw=1, ls="--", zorder=1)
axs[0].text(2.1, .505, "limiar 0,50", fontsize=7.5, color=SUAVE, ha="left", va="bottom")
plt.tight_layout(w_pad=2.5)
plt.savefig(FIGURAS / "figura2_validacao_kmeans.png", dpi=300); plt.close()

# Figura 3 (trajetória) — sem grade, eixos pretos de 1,5 pt, título do eixo x
fig, ax = plt.subplots(figsize=(6.3, 3.4))
for t, x in v.groupby("ticker"):
    x = x.sort_values("ano")
    ax.plot(x["ano"], x["spread"] * 100, color=LARANJA if x["grupo"].iloc[0] == "Alto" else AZUL, lw=.8, alpha=.25)
med = v.groupby(["grupo", "ano"])["spread"].median().unstack(0) * 100
for g, c in [("Alto", LARANJA), ("Baixo", AZUL)]:
    ax.plot(med.index, med[g], color=c, lw=2.4, marker="o", ms=5, mec="white", mew=1.2, label=f"{g} IS&M (mediana)")
ax.axhline(0, color=SUAVE, lw=.8)
ax.set_ylim(-160, 100); ax.set_xticks(range(2015, 2025)); ax.set_xlim(2014.6, 2024.4)
ax.set_xlabel("Ano", fontsize=9); ax.set_ylabel("Spread ROIC–WACC (%)", fontsize=9)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: fmt(x)))
ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
plt.tight_layout(); plt.savefig(FIGURAS / "figura3_trajetoria_spread.png", dpi=300); plt.close()

print(f"Tabelas salvas em: {TABELAS}")
print(f"Figuras salvas em: {FIGURAS}")
fora = v[v["spread"] < -1.6][["ticker", "ano", "spread"]]
if len(fora):
    print("\nObservações fora da escala da Figura 3 :")
    print(fora.to_string(index=False))
