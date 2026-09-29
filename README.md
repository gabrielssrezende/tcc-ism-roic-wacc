# Crescimento e criação de valor em empresas com alto investimento em aquisição de clientes

Código e dados do TCC do MBA em Finanças e Controladoria (USP/Esalq).
Autor: Gabriel dos Santos Silva Rezende. Orientador: Carlos Simão Struckas Filho.

O trabalho compara a intensidade de Sales & Marketing (IS&M = despesa de S&M / receita) com o spread ROIC-WACC de 26 empresas de software B2B por assinatura listadas nos EUA, de 2015 a 2024. Os dados vêm dos formulários 10-K (SEC/EDGAR) e os parâmetros de custo de capital, do site do Damodaran.

## Scripts

| Script | O que faz |
|---|---|
| `01_selecao_amostra.py` | Filtros automáticos (SIC, bolsa, número de 10-K) na Submissions API da SEC |
| `01b_aplicar_revisao.py` | Registra a decisão de incluir ou excluir cada candidata, com o motivo |
| `02_coleta_financeiros.py` | Extrai os dados anuais dos 10-Ks pela XBRL API e aplica os ajustes manuais |
| `03_calculo_variaveis.py` | IS&M, NOPAT, capital investido, ROIC, WACC e spread |
| `04_estratificacao_kmeans.py` | Grupos por k-means (silhueta e cotovelo) |
| `05_testes_estatisticos.py` | Hipóteses H1 a H3 e testes de robustez |
| `06_tabelas_figuras.py` | Tabelas e figuras do trabalho |

Os scripts 01 e 02 precisam de internet. Os demais rodam só com os arquivos de `dados/`:

```bash
pip install -r requirements.txt
cd scripts
python 03_calculo_variaveis.py
python 04_estratificacao_kmeans.py
python 05_testes_estatisticos.py
python 06_tabelas_figuras.py
```

## Dados

- `amostra_candidatas_expandida.csv`: as 42 candidatas aprovadas nos filtros, com a decisão e o motivo de cada exclusão
- `dados_financeiros_brutos.csv`: 243 observações empresa-ano extraídas da SEC
- `ajustes_manuais_sm.csv`: despesa de S&M da Paycom, lançada a partir dos 10-Ks
- `ajustes_manuais_divida_juros.csv`: dívida e juros que não têm conceito XBRL padrão, com a fonte de cada valor
- `diagnostico_divida.csv`: todos os conceitos de dívida divulgados por empresa-ano, para conferência
- `parametros_damodaran.csv`: taxa livre de risco, prêmio de risco e beta desalavancado do setor, por ano

Os resultados ficam em `resultados/` (testes, tendência por empresa, tabelas e figuras).

## Principais escolhas

- **Amostra.** SIC 7372, 7371 ou 7374; NYSE ou Nasdaq; pelo menos 5 formulários 10-K entre 2015 e 2024. Na revisão manual foram excluídas empresas com receita por assinatura e manutenção abaixo de 60%, aquisição de USD 5 bi ou mais sem 5 exercícios completos no período, market cap abaixo de USD 500 mi ou sem S&M divulgado separadamente. Das 42 candidatas, ficaram 26.
- **Coleta.** Contas de resultado só com períodos de 12 meses; contas de balanço na data de encerramento; exercícios de 52/53 semanas encerrados no início de janeiro contam no ano anterior. A dívida inclui empréstimos, notas sênior e debêntures conversíveis.
- **Alíquota.** Efetiva, limitada a [0, 1]; com EBT negativo ou nulo, 35% até 2017 e 21% a partir de 2018.
- **ROIC e WACC.** Capital investido = PL + dívida - caixa, e o ROIC só é calculado com capital investido positivo. O WACC usa CAPM com beta setorial realavancado (Hamada) e pesos contábeis. Com PL negativo, WACC = Ke.
- **Grupos e testes.** k-means sobre o IS&M médio de cada empresa (k = 2; k = 3 como robustez). Os testes são Mann-Whitney e Spearman, bilaterais, a 5%.

Das 243 observações, 209 entram nos testes: 27 saem por capital investido não positivo e 7 por falta do saldo de caixa.

## Fontes

- SEC, EDGAR APIs: <https://www.sec.gov/search-filings/edgar-application-programming-interfaces>
- Damodaran Online: <https://pages.stern.nyu.edu/~adamodar/>
