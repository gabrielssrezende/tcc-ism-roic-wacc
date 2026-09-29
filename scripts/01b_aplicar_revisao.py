"""
01b - Revisão manual das candidatas

Registra a decisão de inclusão ou exclusão de cada empresa aprovada nos filtros
automáticos (script 01), com o motivo e, quando houver, a evidência consultada.
Critérios de exclusão: receita por assinatura e manutenção < 60%; aquisição de
USD 5 bi ou mais sem 5 exercícios completos no período; market cap < USD 500 mi;
despesa de S&M não divulgada separadamente em pelo menos 5 exercícios.

Entrada: dados/candidatas_para_revisao.csv
Saída:   dados/amostra_candidatas_expandida.csv
"""

import pandas as pd

from config import DADOS, AMOSTRA_CANDIDATAS

ENTRADA = DADOS / "candidatas_para_revisao.csv"

# ticker: (IS&M esperado, incluir, motivo da exclusão, evidência / observação)
REVISAO = {
    # incluídas
    "ADBE": ("medio", "sim", "", ""),
    "APPN": ("alto", "sim", "", ""),
    "BLKB": ("baixo", "sim", "", ""),
    "CDNS": ("baixo", "sim", "", ""),
    "CRWD": ("alto", "sim", "",
             "Assinatura > 90% da receita; aquisições de pequeno porte"),
    "DDOG": ("alto", "sim", "",
             "10-K: 'substantially all of our revenue is from subscription software sales'"),
    "DT":   ("medio", "sim", "", ""),
    "ESTC": ("alto", "sim", "", ""),
    "FIVN": ("medio", "sim", "", ""),
    "HUBS": ("alto", "sim", "", ""),
    "MDB":  ("alto", "sim", "", ""),
    "NET":  ("medio", "sim", "",
             "10-K: receita 'primarily from subscriptions'; componente variável restrito a banda excedente"),
    "NOW":  ("medio", "sim", "",
             "Assinatura > 90% da receita; sem M&A relevante; market cap > USD 500 mi em todo o período"),
    "PAYC": ("medio", "sim", "", ""),
    "PCTY": ("baixo", "sim", "", ""),
    "PRGS": ("baixo", "sim", "", ""),
    "PTC":  ("medio", "sim", "", ""),
    "QLYS": ("baixo", "sim", "", ""),
    "RPD":  ("alto", "sim", "", ""),
    "SMAR": ("alto", "sim", "",
             "Assinatura de 94% da receita no FY2024; capital fechado em jan/2025, após o período"),
    "SNPS": ("baixo", "sim", "",
             "Time-based 57,9% + manutenção 17,6% = 75,5% da receita (FY2023); aquisição da Ansys concluída em jul/2025, fora do período"),
    "SPSC": ("medio", "sim", "", ""),
    "TENB": ("medio", "sim", "", ""),
    "VEEV": ("baixo", "sim", "", ""),
    "WDAY": ("medio", "sim", "", ""),
    "ZS":   ("alto", "sim", "", ""),
    # excluídas
    "ANSS": ("baixo", "nao", "Despesa de S&M não divulgada separadamente (DRE apresenta SG&A agregado), inviabilizando o cálculo do IS&M",
             "DRE GAAP, FY2023"),
    "BILL": ("medio", "nao", "Receita assinatura < 60%: receitas de transação/pagamento representam ~70-75% do total",
             ""),
    "CDAY": ("medio", "nao", "Despesa de S&M divulgada separadamente apenas a partir de 2021 (4 exercícios); até 2020 a DRE apresenta SG&A agregado, abaixo do mínimo de 5 anos com IS&M calculável",
             "DRE 2018-2019: linha única 'Selling, general and administrative'"),
    "CRM":  ("baixo", "nao", "M&A relevante sem 5 anos completos: aquisição da Slack concluída em jul/2021 (~USD 27,7 bi)",
             "Salesforce, comunicado de 21/07/2021"),
    "DOMO": ("alto", "nao", "Market cap < USD 500M: capitalização caiu para ~USD 200-400M em 2023-2024",
             ""),
    "EPAM": ("baixo", "nao", "Receita assinatura < 60%: empresa de serviços de TI (time-&-material)",
             ""),
    "EVBG": ("alto", "nao", "Market cap < USD 500M: capitalização no fim de 2016 (ano do IPO) abaixo do limiar",
             "ações em circulação x preço de fechamento em 30/12/2016"),
    "FSLY": ("medio", "nao", "Receita assinatura < 60%: modelo usage-based (cobrança por tráfego/consumo)",
             ""),
    "GWRE": ("medio", "nao", "Receita assinatura < 60%: modelo de licença perpetua predominante até 2021",
             ""),
    "INTU": ("medio", "nao", "M&A relevante sem 5 anos completos: Credit Karma set/2020 (~USD 7.1B) e Mailchimp nov/2021 (~USD 12B)",
             ""),
    "LPSN": ("alto", "nao", "Market cap < USD 500M: capitalização caiu para ~USD 50-100M após 2022",
             ""),
    "MANH": ("baixo", "nao", "Receita assinatura < 60%: cloud subscription ~37% + manutenção ~20% = ~57%",
             ""),
    "MSFT": ("baixo", "nao", "M&A relevante sem 5 anos completos: Activision Blizzard out/2023 (~USD 69B)",
             ""),
    "OKTA": ("alto", "nao", "M&A relevante sem 5 anos completos: aquisição Auth0 mai/2021 (~USD 6.5B)",
             ""),
    "ORCL": ("baixo", "nao", "M&A relevante sem 5 anos completos: aquisição Cerner jun/2022 (~USD 28B)",
             ""),
    "VRNS": ("medio", "nao", "Receita assinatura < 60%: modelo perpetual license vigente até 2021",
             ""),
}

df = pd.read_csv(ENTRADA)
sem_decisao = sorted(set(df["ticker"]) - set(REVISAO))
if sem_decisao:
    print("Candidatas sem decisão em REVISAO:", ", ".join(sem_decisao))
df = df[df["ticker"].isin(REVISAO)].copy()
df[["perfil_ism_esperado", "incluir", "motivo", "evidencia"]] = [list(REVISAO[t]) for t in df["ticker"]]

cols = ["ticker", "cik", "nome", "exchange", "sic", "sic_desc", "n_10k_2015_2024", "anos_10k",
        "perfil_ism_esperado", "incluir", "motivo", "evidencia"]
saida = df[cols].sort_values(["incluir", "ticker"], ascending=[False, True])
saida.to_csv(AMOSTRA_CANDIDATAS, index=False, encoding="utf-8-sig")

print(f"Candidatas: {len(saida)} | incluídas: {(saida['incluir'] == 'sim').sum()} | "
      f"excluídas: {(saida['incluir'] == 'nao').sum()}")
print(f"Arquivo salvo: {AMOSTRA_CANDIDATAS.name}")
