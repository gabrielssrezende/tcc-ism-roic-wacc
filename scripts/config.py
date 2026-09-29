"""Caminhos e parâmetros usados pelos scripts. Os caminhos partem da raiz do repositório."""

from pathlib import Path

RAIZ        = Path(__file__).resolve().parent.parent
DADOS       = RAIZ / "dados"
RESULTADOS  = RAIZ / "resultados"
TABELAS     = RESULTADOS / "tabelas"
FIGURAS     = RESULTADOS / "figuras"

for pasta in (DADOS, RESULTADOS, TABELAS, FIGURAS):
    pasta.mkdir(parents=True, exist_ok=True)

# Arquivos de dados
AMOSTRA_CANDIDATAS  = DADOS / "amostra_candidatas_expandida.csv"   # saída do script 01 (+ revisão manual)
DADOS_BRUTOS        = DADOS / "dados_financeiros_brutos.csv"       # saída do script 02
AJUSTES_MANUAIS_SM  = DADOS / "ajustes_manuais_sm.csv"             # S&M extraído manualmente (PAYC)
AJUSTES_MANUAIS_DIVIDA_JUROS = DADOS / "ajustes_manuais_divida_juros.csv"  # dívida/juros sem tag padrão
PARAMETROS          = DADOS / "parametros_damodaran.csv"           # Rf, ERP e beta desalavancado por ano
DADOS_VARIAVEIS     = DADOS / "dados_variaveis.csv"                # saída do script 03
DADOS_CLUSTER       = DADOS / "dados_com_cluster.csv"              # saída do script 04

# Parâmetros metodológicos (ver seção Metodologia do TCC)
ANOS                     = list(range(2015, 2025))
ALIQ_ESTATUTARIA_ATE_2017 = 0.35   # alíquota federal dos EUA antes da Tax Cuts and Jobs Act
ALIQ_ESTATUTARIA_DESDE_2018 = 0.21 # alíquota federal dos EUA a partir de 2018 (TCJA)
LIMITES_ALIQ_EFETIVA     = (0.0, 1.0)   # winsorização em 0 e 1 (Dyreng et al., 2008; 2017)
K_PRINCIPAL              = 2        # número de grupos adotado na análise principal
K_ROBUSTEZ               = 3        # estratificação alternativa (teste de robustez)
K_TESTADOS               = range(2, 6)
KMEANS_N_INIT            = 200
KMEANS_SEED              = 42
ALFA                     = 0.05

# Robustez de M&A: aquisições abaixo de USD 5 bi, mas relevantes frente à receita
# (PTC-ServiceMax 2023; BLKB-EVERFI 2021; PRGS-ShareFile 2024)
ROBUSTEZ_EXCLUIR_MA      = ["PTC", "BLKB", "PRGS"]
