"""
01 - Filtros automáticos das empresas candidatas (SEC Submissions API)

Para cada ticker da lista inicial, verifica:
  (i)   SIC 7372, 7371 ou 7374
  (ii)  listagem na NYSE ou na Nasdaq
  (iii) pelo menos 5 formulários 10-K arquivados entre 2015 e 2024

A contagem de 10-K usa o histórico completo de submissões: além do bloco
`filings.recent` (cerca de 1.000 submissões), lê as páginas antigas em `filings.files`.

Saídas:
  dados/filtro_automatico_todas.csv   resultado de cada filtro, para todas as empresas
  dados/candidatas_para_revisao.csv   empresas aprovadas, para a revisão manual (script 01b)

Requer internet (3 a 6 minutos).
"""

import time

import pandas as pd
import requests

from config import DADOS

# A SEC exige um User-Agent com nome e e-mail de contato
HEADERS = {"User-Agent": "Gabriel Rezende gabriel.rezende.tcc@gmail.com"}
PAUSA = 0.15                     # limite da SEC: até 10 requisições por segundo
SIC_VALIDOS = {"7372", "7371", "7374"}
BOLSAS_VALIDAS = {"NYSE", "NASDAQ"}
ANO_INI, ANO_FIM, MIN_10K = 2015, 2024, 5

SAIDA_TODAS = DADOS / "filtro_automatico_todas.csv"
SAIDA_REVISAO = DADOS / "candidatas_para_revisao.csv"

TICKERS_CANDIDATOS = [
    # IS&M esperado alto (S&M > 40% da receita)
    "HUBS", "DDOG", "ZS",   "CRWD", "GTLB", "BRZE", "SMAR", "ASAN",
    "NCNO", "BILL", "ESTC", "MDB",  "CFLT", "FROG", "DOCN", "APPN",
    "EVBG", "OKTA", "S",    "CYBR", "VRNS", "RPD",  "DT",

    # IS&M esperado médio (20% a 40%)
    "NOW",  "WDAY", "VEEV", "PCTY", "PAYC", "CDAY", "TOST", "JAMF",
    "SPSC", "PCOR", "TENB", "NET",  "ZI",   "MNDY", "GWRE", "FIVN",
    "NICE", "PANW", "FTNT",

    # IS&M esperado baixo (< 20%)
    "CRM",  "ADBE", "SNPS", "CDNS", "INTU", "PTC",  "PRGS", "ANSS",
    "FICO", "BLKB", "BSY",  "AZPN", "DUOL", "QLYS",

    # outras candidatas
    "EPAM", "LPSN", "MANH", "ORCL", "DOMO", "FSLY", "MSFT",
]

# Empresas deslistadas ou renomeadas não constam do catálogo atual de tickers da SEC
CIK_MANUAL = {
    "SMAR": "0001366561",   # Smartsheet — capital fechado em jan/2025
    "EVBG": "0001437352",   # Everbridge — capital fechado em jul/2024
    "CDAY": "0001725057",   # Ceridian HCM, renomeada Dayforce (ticker DAY) em 2024
    "ANSS": "0001013462",   # Ansys — adquirida pela Synopsys em 2025
    "AZPN": "0001897982",   # "nova" Aspen Technology, criada na combinação com a Emerson em 2022
    "LPSN": "0001102993",   # LivePerson
}


def get_json(url, tentativas=4):
    """GET com novas tentativas em caso de erro 429 ou 5xx."""
    for i in range(tentativas):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            time.sleep(2 * (i + 1))
        except requests.RequestException:
            time.sleep(2 * (i + 1))
    return None


def formularios(bloco):
    """Converte um bloco de submissões (formato colunar) em lista de dicionários."""
    forms = bloco.get("form", [])
    datas = bloco.get("filingDate", [])
    periodos = bloco.get("reportDate", [""] * len(forms))
    return [{"form": f, "filingDate": d, "reportDate": p} for f, d, p in zip(forms, datas, periodos)]


def historico_completo(sub):
    """Junta o bloco `recent` com todas as páginas antigas listadas em `files`."""
    todos = formularios(sub.get("filings", {}).get("recent", {}))
    paginas = sub.get("filings", {}).get("files", [])
    for pag in paginas:
        dados = get_json(f"https://data.sec.gov/submissions/{pag['name']}")
        time.sleep(PAUSA)
        if dados:
            todos.extend(formularios(dados))
    return todos, len(paginas)


def avaliar(ticker, cik):
    sub = get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    time.sleep(PAUSA)
    if sub is None:
        return {"ticker": ticker, "cik": cik, "encontrada": False, "motivo_reprovacao": "CIK não encontrado na SEC"}

    hist, n_paginas = historico_completo(sub)
    tenks = sorted({h["filingDate"] for h in hist
                    if h["form"] == "10-K" and str(ANO_INI) <= h["filingDate"][:4] <= str(ANO_FIM)})
    anos_10k = [d[:4] for d in tenks]
    arquiva_20f = any(h["form"] == "20-F" for h in hist if h["filingDate"][:4] >= str(ANO_INI))

    exchanges = [e for e in (sub.get("exchanges") or []) if e]
    sic = str(sub.get("sic", ""))

    ok_sic = sic in SIC_VALIDOS
    # empresas deslistadas depois de 2024 não têm bolsa atual; a listagem no período é conferida na revisão manual
    deslistada = len(exchanges) == 0
    ok_bolsa = deslistada or any(e.upper() in BOLSAS_VALIDAS for e in exchanges)
    ok_10k = len(tenks) >= MIN_10K

    motivos = []
    if not ok_sic:
        motivos.append(f"SIC {sic or 'ausente'} fora de 7372/7371/7374")
    if not ok_bolsa:
        motivos.append(f"bolsa {'/'.join(exchanges)}")
    if not ok_10k:
        motivos.append(f"apenas {len(tenks)} 10-K entre {ANO_INI} e {ANO_FIM}"
                       + (" (arquiva 20-F, emissor estrangeiro)" if arquiva_20f else ""))

    return {
        "ticker": ticker, "cik": cik, "encontrada": True,
        "nome": sub.get("name", ""),
        "exchange": "/".join(exchanges) if exchanges else "sem listagem atual (verificar NYSE/Nasdaq no período)",
        "sic": sic,
        "sic_desc": sub.get("sicDescription", ""),
        "n_10k_2015_2024": len(tenks), "anos_10k": ", ".join(anos_10k),
        "paginas_antigas_lidas": n_paginas,
        "ok_sic": ok_sic, "ok_bolsa": ok_bolsa, "ok_10k": ok_10k,
        "aprovada_filtro_auto": ok_sic and ok_bolsa and ok_10k,
        "motivo_reprovacao": "; ".join(motivos),
    }


def main():
    tickers = list(dict.fromkeys(t.upper().strip() for t in TICKERS_CANDIDATOS))
    print(f"Tickers na lista: {len(tickers)}")

    cat = requests.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=30)
    cat.raise_for_status()
    df_cik = pd.DataFrame(cat.json()).T
    mapa = {str(t).upper(): str(c).zfill(10) for c, t in zip(df_cik["cik_str"], df_cik["ticker"])}
    mapa.update({k: str(v).zfill(10) for k, v in CIK_MANUAL.items()})

    linhas = []
    for i, t in enumerate(tickers, 1):
        cik = mapa.get(t)
        if cik is None:
            linhas.append({"ticker": t, "encontrada": False, "motivo_reprovacao": "ticker não encontrado no catálogo da SEC"})
            print(f"  {i:02d}/{len(tickers)} {t:6s} não encontrado (incluir em CIK_MANUAL)")
            continue
        r = avaliar(t, cik)
        linhas.append(r)
        if r["encontrada"]:
            status = "aprovada " if r["aprovada_filtro_auto"] else "reprovada"
            print(f"  {i:02d}/{len(tickers)} {t:6s} {status}  10-K: {r['n_10k_2015_2024']:2d}  SIC {r['sic']}  {r['nome'][:35]}")
        else:
            print(f"  {i:02d}/{len(tickers)} {t:6s} {r['motivo_reprovacao']}")

    todas = pd.DataFrame(linhas)
    todas.to_csv(SAIDA_TODAS, index=False, encoding="utf-8-sig")

    aprov = todas["aprovada_filtro_auto"].fillna(False).astype(bool)
    cols = ["ticker", "cik", "nome", "exchange", "sic", "sic_desc", "n_10k_2015_2024", "anos_10k"]
    todas.loc[aprov, cols].sort_values("ticker").to_csv(SAIDA_REVISAO, index=False, encoding="utf-8-sig")

    print(f"\nAprovadas nos filtros automáticos: {aprov.sum()} de {len(todas)}")
    nao = todas[todas["encontrada"] == False]
    if len(nao):
        print("Não encontradas:", ", ".join(nao["ticker"]))
    print(f"Arquivos salvos: {SAIDA_TODAS.name}, {SAIDA_REVISAO.name}")


if __name__ == "__main__":
    main()
