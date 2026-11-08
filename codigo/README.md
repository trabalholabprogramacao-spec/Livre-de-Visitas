# Livro de visitas: código

Projeto integrador de Engenharia de Software. O sistema inteiro é Python:
as regras e também a interface rodam no navegador por meio do Brython
(Python no navegador). O resultado é um único arquivo, `Livro_de_Visitas.html`,
que abre com dois cliques, sem internet, sem servidor e sem banco de dados.

## Arquivos

    logica.py       O ALGORITMO (Python puro): tipos de registro, validação,
                    presentes e pendentes, busca sem acento, permanência,
                    estatísticas dos gráficos, exportação CSV
    estado.py       Os dados (um dicionário com pessoas e visitas) e as
                    operações sobre ele: criar, buscar, registrar saída
    interface.py    As 4 abas (Recepção, Histórico, Gráficos, Pessoas),
                    armazenamento no navegador, cópia de segurança, demonstração
    dados_demo.py   Dados 100% fictícios
    estilo.css      Visual
    graficos.js     Desenha os gráficos (Chart.js) com números calculados em Python
    modelo.html     Esqueleto da página
    montar.py       Junta tudo em ../Livro_de_Visitas.html
    vendor/         Brython e Chart.js (cópias locais, sem internet)
    testes/         Testes automáticos (pytest)

## Fluxo de trabalho

    python -m pytest        roda os testes (regras e dados)
    python montar.py        gera o ../Livro_de_Visitas.html

Mudou qualquer `.py`, `.css` ou `.js`? Rode `python montar.py` de novo.

## Decisões de projeto

- **Sem banco de dados**: os dados são um dicionário guardado no `localStorage`
  do navegador, com cópia de segurança em arquivo JSON. Para o volume do
  escritório (3 a 16 visitas por dia) isso basta; o limite é que os dados
  ficam presos a um navegador, por isso o aviso semanal de cópia.
- **Tipos de registro em um dicionário** (`CAMPOS_POR_TIPO`): formulário e
  validação usam a mesma fonte; criar um tipo novo é adicionar uma entrada.
- **Controle de saída por visita**: cliente, prestador e "outro" (se marcado)
  ficam em "No escritório agora"; envelope e entrega são registros únicos.
- **Saída esquecida**: nunca se inventa horário; informa-se a hora real ou
  marca-se "saída não registrada".
- **Gráficos**: números calculados em Python; a permanência só considera
  visitas com saída registrada, e a tela informa quantas ficaram de fora.
- **Segurança básica**: todo texto digitado é escapado antes de ir para a página,
  e a planilha neutraliza textos que o Excel trataria como fórmula.

## Limitações

- O sistema só conhece o que foi registrado: ausência de registro pode ser
  "não veio" ou "esqueceu de anotar".
- Dados ficam no navegador: limpar os dados do navegador apaga tudo
  (por isso a cópia de segurança).
- Sem login próprio; uma pessoa por vez, em um único computador.
- Testado em Chromium abrindo o arquivo direto do disco. Não testado em
  Windows com Edge/Chrome reais.
