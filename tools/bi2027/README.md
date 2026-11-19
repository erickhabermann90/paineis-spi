# BI 2027 — painel do RC (em desenho)

Protótipos com dados reais do Gabriel (e do Lucas no roteiro), dados de 19/11/2026. **Nada disto está publicado**: fica fora de `site/`.

## Telas aprovadas até agora
- `prototipos/inicio.html` — tela inicial (modelo 2, versão limpa)
  - Volume geral / Plano Performance em toneladas, checkpoints 80% · 100% · 105% com gap em t por checkpoint, ranking embutido.
  - KPIs com cor e sombra: Faturamento (verde, cifrão), Fórmula Natural (azul claro, logo), Origens (azul royal, logo), Pet Care (rosa — cor ainda a definir). FN e Origens em toneladas. Objetivo ao lado do %.
  - Positivação e Mix em barras verticais.
  - Barra inferior: Mês atual · Performance · Campanhas · Roteiro · Clientes.
  - Faturamento, FN, Origens e Pet Care por RC e os objetivos são **exemplo** (falta achar no BI por RC).
- `prototipos/mes_atual.html` — lista de clientes ativos: razão social, objetivo, faturado, carteira, gap, dias sem compra; filtros Todos / Faltam / Sem pedido / Batidos.
- `prototipos/roteiro.html` — roteiro sugerido de 4 semanas (Gabriel e Lucas).

## Regras decididas
- Objetivo por cliente (a partir de jan/2027): curva por tamanho de 5% (maior) a 40% (menor), calibrada para a soma = Plano Performance + 10% de folga; cliente novo = 150 kg; sem recuperação de gap por enquanto (rever após o 1º trimestre). Base final: média dos últimos 3 meses fechados (na prévia: média 2026).
- Roteiro: A semanal, B quinzenal, C mensal (curva de volume 80/15/5); mix em terços (flag "foco mix"); máximo 8 visitas/dia — se passar, o menor cliente do dia perde frequência; dia fixo por cliente, ordem pelo menor deslocamento (30 km/h + 10 min/parada). Tempo de visita só no cálculo (15 min a 3h), não aparece na tela. Todos presenciais. Sexta dos pequenos (C + menores B) para Maria, Yuri, Lucas e Thiago (pedido na quinta → entrega na terça). RCs são PJ: tom de "rota sugerida".

## Pendências
- Cor do Pet Care; KPIs por RC (Faturamento, FN, Origens, Pet Care) e objetivos de Positivação e Mix.
- Roteiro dos demais RCs: geocodificar os endereços (já extraídos do BI: Curva ABC, dims CÓD RC, CÓD CLIENTE, ENDEREÇO COMPLETO, CIDADE). 33 de 225 endereços ficaram aproximados (bairro/cidade).
- Dias que misturam cidades (ex.: Gabriel sexta S1) — avaliar separar por cidade.
- Mix do mês por cliente exige extração dos itens do mês (~3 min).

## Fontes
- `fontes/*.tpl.html` + `dados/*.json` geram os protótipos (`/*DATA*/` e `@@FN@@`/`@@OR@@` substituídos pelos dados e logos).
- `fontes/roteiro.py <pasta com rot_cli.json e geo.json>` gera `roteiro.json`.
