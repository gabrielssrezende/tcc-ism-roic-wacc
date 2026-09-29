"""
04 - Estratificação por k-means

Agrupa as empresas pelo IS&M médio no período (todas as observações coletadas),
testando k = 2 a 5 (n_init = 200, random_state = 42). A análise principal usa k = 2
(maior silhueta) e k = 3 entra como robustez. Os grupos são nomeados pela ordem do
IS&M médio: Baixo/Alto (k = 2) e Baixo/Médio/Alto (k = 3).

Entrada: dados/dados_variaveis.csv
Saídas:  dados/dados_com_cluster.csv, resultados/validacao_kmeans.csv
"""

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from config import (DADOS_VARIAVEIS, DADOS_CLUSTER, RESULTADOS,
                    K_PRINCIPAL, K_ROBUSTEZ, K_TESTADOS, KMEANS_N_INIT, KMEANS_SEED)

df = pd.read_csv(DADOS_VARIAVEIS)
empresas = df.groupby("ticker", as_index=False)["ism"].mean().rename(columns={"ism": "ism_medio"})
X = empresas[["ism_medio"]].values

NOMES = {2: ["Baixo", "Alto"], 3: ["Baixo", "Médio", "Alto"]}
validacao = []
for k in K_TESTADOS:
    km = KMeans(n_clusters=k, n_init=KMEANS_N_INIT, random_state=KMEANS_SEED).fit(X)
    validacao.append({"k": k, "silhueta": silhouette_score(X, km.labels_), "inercia": km.inertia_})
    if k in NOMES:
        ordem = empresas.assign(label=km.labels_).groupby("label")["ism_medio"].mean().sort_values().index
        mapa = dict(zip(ordem, NOMES[k]))
        empresas[f"grupo_k{k}"] = [mapa[l] for l in km.labels_]

val = pd.DataFrame(validacao)
val.to_csv(RESULTADOS / "validacao_kmeans.csv", index=False, encoding="utf-8-sig")

df = df.merge(empresas, on="ticker", how="left")
df["grupo"] = df[f"grupo_k{K_PRINCIPAL}"]   # análise principal
df.to_csv(DADOS_CLUSTER, index=False, encoding="utf-8-sig")

print(val.round(4).to_string(index=False))
print(f"\nk adotado: {K_PRINCIPAL} (maior índice de silhueta); k = {K_ROBUSTEZ} mantido como robustez\n")
print(empresas.sort_values("ism_medio").round(4).to_string(index=False))
print(f"\nArquivo salvo: {DADOS_CLUSTER}")
