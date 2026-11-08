"""Interface do Livro de visitas.

Este arquivo roda DENTRO do navegador (Brython: Python no navegador), por isso
o sistema funciona abrindo o Livro_de_Visitas.html com dois cliques, sem
instalar nada. Ele:

  - guarda os dados no navegador (localStorage) e na cópia de segurança;
  - desenha as 4 abas: Recepção, Histórico, Gráficos e Pessoas;
  - liga os cliques e formulários às regras de logica.py e estado.py.

As regras (validação, busca, estatísticas, exportação) ficam em logica.py;
aqui só há apresentação e armazenamento.
"""
import json
from datetime import date, datetime, timedelta

from browser import document, timer, window

import dados_demo
import estado
import logica

CHAVE = "livro_de_visitas_v1"
CHAVE_COPIA = CHAVE + "_ultima_copia"
MODO_DEMO = "demo" in str(window.location.search)
MAXIMO_LINHAS = 1000                # linhas mostradas no histórico (o Excel leva tudo)
CAMPOS_TEXTO = ("nome", "detalhe", "origem", "tipo_outro", "observacao")

ESTADO = estado.novo_estado()       # todos os dados do sistema
ABA = "recepcao"
FORM = None                         # o que está digitado no formulário de registro
FILTRO_HIST = {}
FILTRO_GRAF = {}
FLASH = []                          # mensagens mostradas uma única vez
AVISOS = []                         # avisos permanentes (armazenamento)


# ------------------------------------------------------------ utilidades

def esc(texto):
    """Escapa texto para colocar dentro de HTML (evita que um nome com < ou &
    quebre a página)."""
    return (str(texto).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def agora():
    return datetime.now()


def hoje():
    return agora().date()


def dmy(dia):
    return f"{dia.day:02d}/{dia.month:02d}/{dia.year}"


def plural(n, singular, plural_):
    return singular if n == 1 else plural_


def atributo(elemento, nome):
    try:
        valor = elemento.getAttribute(nome)
    except Exception:
        return ""
    return valor if isinstance(valor, str) else ""


def acima(elemento, seletor):
    try:
        return elemento.closest(seletor)
    except Exception:
        return None


def ler_form(form):
    """Lê um formulário: texto vira texto; caixas marcadas viram listas."""
    lido = {}
    for campo in form.select("input, select, textarea"):
        nome = campo.name
        if not nome:
            continue
        if campo.type == "checkbox":
            if campo.checked:
                lido.setdefault(nome, []).append(campo.value)
        else:
            lido[nome] = campo.value
    return lido


# ----------------------------------------------------------- armazenamento

def ler_armazenamento(chave):
    """Devolve (texto ou None, se o navegador permite guardar dados)."""
    try:
        valor = window.localStorage.getItem(chave)
    except Exception:
        return None, False
    return (valor if isinstance(valor, str) else None), True


def gravar_armazenamento(chave, texto):
    try:
        window.localStorage.setItem(chave, texto)
        return True
    except Exception:
        return False


def carregar():
    global ESTADO
    if MODO_DEMO:
        ESTADO = dados_demo.criar_estado_demo(agora())
        return
    texto, funciona = ler_armazenamento(CHAVE)
    if not funciona:
        AVISOS.append(("erro", "Este navegador não deixa guardar dados (janela anônima ou "
                               "bloqueio). Dá para usar, mas os registros somem ao fechar a "
                               "página. Salve uma cópia de segurança antes de fechar."))
        return
    if texto is None:
        return
    try:
        lido = json.loads(texto)
        if not estado.estrutura_valida(lido):
            raise ValueError("estrutura")
        ESTADO = lido
    except Exception:
        carimbo = agora().strftime("%Y%m%d%H%M%S")
        gravar_armazenamento(f"{CHAVE}_ilegivel_{carimbo}", texto)
        AVISOS.append(("erro", "Não consegui ler os dados salvos. O conteúdo antigo foi guardado "
                               "à parte e o sistema começou vazio. Peça ajuda a quem montou o sistema."))


def salvar():
    if MODO_DEMO:
        return
    if not gravar_armazenamento(CHAVE, json.dumps(ESTADO, ensure_ascii=False)):
        flash("erro", "Não foi possível salvar neste navegador. Salve uma cópia de segurança agora.")


def dias_desde_a_copia():
    texto, _ = ler_armazenamento(CHAVE_COPIA)
    if not texto:
        return None
    try:
        ano, mes, dia = [int(parte) for parte in texto.split("-")]
        return (hoje() - date(ano, mes, dia)).days
    except Exception:
        return None


def baixar(nome, texto, mime, com_bom=False):
    """Faz o navegador baixar um arquivo de texto. O BOM faz o Excel
    reconhecer os acentos (UTF-8) ao abrir um .csv."""
    conteudo = ("﻿" + texto) if com_bom else texto
    arquivo = window.Blob.new([conteudo], {"type": mime})
    endereco = window.URL.createObjectURL(arquivo)
    link = document.createElement("a")
    link.href = endereco
    link.download = nome
    document <= link
    link.click()
    link.remove()
    timer.set_timeout(lambda: window.URL.revokeObjectURL(endereco), 2000)


# --------------------------------------------------------------- mensagens

def flash(categoria, texto):
    FLASH.append((categoria, texto))


def html_flash():
    partes = []
    for categoria, texto in FLASH:
        papel = "alert" if categoria == "erro" else "status"
        partes.append(f'<p class="aviso-curto {categoria}" role="{papel}">{esc(texto)}</p>')
    del FLASH[:]
    return "".join(partes)


def html_faixa():
    partes = []
    if MODO_DEMO:
        partes.append('<p class="aviso-curto demo"><span><strong>Demonstração:</strong> '
                      'dados fictícios, nada daqui é salvo.</span>'
                      '<button class="btn" type="button" data-acao="demo_sair">'
                      'Sair da demonstração</button></p>')
    for categoria, texto in AVISOS:
        partes.append(f'<p class="aviso-curto {categoria}" role="alert"><span>{esc(texto)}</span></p>')
    if not MODO_DEMO and ESTADO["visitas"]:
        dias = dias_desde_a_copia()
        if dias is None or dias >= 7:
            if dias is None:
                msg = "Você ainda não salvou nenhuma cópia de segurança."
            else:
                msg = f"Faz {dias} dias que você não salva uma cópia de segurança."
            partes.append(f'<p class="aviso-curto demo"><span>{msg} Os registros ficam só '
                          'neste navegador: se ele for limpo, eles se perdem.</span>'
                          '<button class="btn" type="button" data-acao="backup">'
                          'Salvar cópia agora</button></p>')
    return "".join(partes)


def html_rodape():
    if MODO_DEMO:
        return "<p>Dados fictícios, só para apresentar o trabalho.</p>"
    dias = dias_desde_a_copia()
    if dias is None:
        ultima = "Nenhuma cópia de segurança salva ainda."
    elif dias == 0:
        ultima = "Última cópia de segurança: hoje."
    else:
        ultima = f"Última cópia de segurança: há {dias} {plural(dias, 'dia', 'dias')}."
    return ('<p>Os registros ficam salvos só neste navegador, neste computador. '
            + ultima + '</p>'
            '<button class="btn" type="button" data-acao="backup">Salvar cópia de segurança</button>'
            '<button class="btn" type="button" data-acao="restaurar">Restaurar cópia</button>'
            '<button class="link-quieto" type="button" data-acao="demo_entrar">Ver demonstração</button>'
            '<input type="file" id="arquivo-restaurar" accept=".json,application/json">')


# ------------------------------------------------------------ aba Recepção

def form_inicial():
    return {"tipo": "cliente", "valores": {}, "atendentes": [], "atendente_outro": "",
            "entrada": "", "controla_saida": True, "erros": {}}


def capturar_form(formulario, erros=None):
    lido = ler_form(formulario)
    tipo = lido.get("tipo", "cliente")
    return {
        "tipo": tipo if tipo in logica.CAMPOS_POR_TIPO else "cliente",
        "valores": {campo: lido.get(campo, "") for campo in CAMPOS_TEXTO},
        "atendentes": [int(i) for i in lido.get("atendentes", []) if str(i).isdigit()],
        "atendente_outro": lido.get("atendente_outro", ""),
        "entrada": lido.get("entrada", ""),
        "controla_saida": bool(lido.get("controla_saida")),
        "erros": erros or {},
    }


def html_campo(nome, rotulo, exemplo, valor, erro, opcional):
    limite = logica.LIMITE_OBSERVACAO if nome == "observacao" else logica.LIMITE_TEXTO
    classe = " tem-erro" if erro else ""
    mensagem = f'<p class="erro">{esc(erro)}</p>' if erro else ""
    sufixo = " (opcional)" if opcional else ""
    return (f'<label class="campo{classe}"><span>{esc(rotulo)}{sufixo}</span>'
            f'<input type="text" name="{nome}" maxlength="{limite}" autocomplete="off" '
            f'placeholder="{esc(exemplo)}" value="{esc(valor)}">{mensagem}</label>')


def html_chip(pessoa, marcados):
    marcado = " checked" if pessoa["id"] in marcados else ""
    return ('<label class="chip"><input type="checkbox" name="atendentes" '
            f'value="{pessoa["id"]}"{marcado}><span>{esc(pessoa["nome"])}</span></label>')


def dica_de_saida(tipo, controla_marcado):
    config = logica.CAMPOS_POR_TIPO[tipo]
    controla = controla_marcado if tipo == "outro" else config["controla_saida"]
    if controla:
        return 'Fica em "No escritório agora" até você registrar a saída.'
    return "Registro único: não precisa registrar saída."


def html_form_registro(f, pessoas):
    erros = f["erros"]
    tipo = f["tipo"]
    config = logica.CAMPOS_POR_TIPO[tipo]
    opcoes = "".join(
        f'<option value="{chave}"{" selected" if chave == tipo else ""}>{esc(cfg["rotulo"])}</option>'
        for chave, cfg in logica.CAMPOS_POR_TIPO.items())
    campos = "".join(
        html_campo(c["nome"], c["rotulo"], c["exemplo"], f["valores"].get(c["nome"], ""),
                   erros.get(c["nome"]), not c["obrigatorio"])
        for c in config["campos"])
    campos += html_campo("observacao", "Observação", "Indicado por Dra. Camila",
                         f["valores"].get("observacao", ""), erros.get("observacao"), True)

    controla = ""
    if tipo == "outro":
        marcado = " checked" if f["controla_saida"] else ""
        controla = ('<label class="campo campo-caixa"><input type="checkbox" name="controla_saida" '
                    f'value="1" id="controla-saida"{marcado}>'
                    '<span>A pessoa fica no escritório (controlar a saída)</span></label>')

    frequentes = [p for p in pessoas if p["frequente"]]
    outras = [p for p in pessoas if not p["frequente"]]
    chips = ""
    if frequentes:
        chips = '<div class="chips">' + "".join(html_chip(p, f["atendentes"]) for p in frequentes) + "</div>"
    mais = ""
    if outras:
        grupos = ""
        for cargo in logica.CARGOS:
            do_cargo = [p for p in outras if p["cargo"] == cargo]
            if do_cargo:
                grupos += (f'<p class="cargo">{esc(cargo)}</p><div class="chips">'
                           + "".join(html_chip(p, f["atendentes"]) for p in do_cargo) + "</div>")
        aberto = " open" if (erros.get("atendentes") or any(p["id"] in f["atendentes"] for p in outras)) else ""
        titulo = "Outras pessoas" if frequentes else "Pessoas"
        mais = f'<details class="mais-pessoas"{aberto}><summary>{titulo} ({len(outras)})</summary>{grupos}</details>'
    erro_atendente = f'<p class="erro">{esc(erros["atendentes"])}</p>' if erros.get("atendentes") else ""

    erro_entrada = f'<p class="erro">{esc(erros["entrada"])}</p>' if erros.get("entrada") else ""
    entrada_aberta = " open" if (erros.get("entrada") or f["entrada"]) else ""
    geral = '<p class="erro-geral" role="alert">Confira os campos marcados abaixo.</p>' if erros else ""

    return f"""{geral}
<form data-form="registro" novalidate>
  <label class="campo"><span>Tipo de registro</span>
    <select name="tipo" id="tipo">{opcoes}</select></label>
  <div id="campos-dinamicos">{campos}</div>
  {controla}
  <p class="dica" id="dica-saida">{dica_de_saida(tipo, f["controla_saida"])}</p>
  <fieldset class="campo">
    <legend>{esc(config["rotulo_atendente"])}</legend>
    {chips}{mais}
    <input type="text" name="atendente_outro" maxlength="120" autocomplete="off"
           placeholder="Outra pessoa: digite o nome" value="{esc(f["atendente_outro"])}"
           aria-label="Outra pessoa, digite o nome">
    {erro_atendente}
  </fieldset>
  <details class="campo"{entrada_aberta}>
    <summary>Registrar outro horário de chegada</summary>
    <p class="dica">Deixe em branco para usar o horário de agora.</p>
    <input type="datetime-local" name="entrada" value="{esc(f["entrada"])}" aria-label="Data e hora da chegada">
    {erro_entrada}
  </details>
  <button class="btn btn-primario" type="submit">Registrar</button>
</form>"""


def html_pendencias(pendentes):
    if not pendentes:
        return ""
    itens = ""
    for v in pendentes:
        itens += f"""<li data-id="{v["id"]}">
  <div><strong>{esc(v["nome"])}</strong>
    <span class="mudo">{esc(v["tipo_txt"])}, {esc(v["rotulo_data"])} às {v["hora_entrada"]}, com {esc(v["atendentes_txt"])}</span></div>
  <div class="linha-form">
    <label>Saiu às <input type="time" name="hora"></label>
    <button class="btn" type="button" data-acao="pend_informar" data-id="{v["id"]}">Informar saída</button>
    <button class="btn btn-quieto" type="button" data-acao="pend_sem" data-id="{v["id"]}">Sem registro de saída</button>
  </div>
</li>"""
    n = len(pendentes)
    return f"""<section class="aviso" aria-labelledby="t-pendentes">
  <h2 id="t-pendentes">{n} {plural(n, "visita", "visitas")} de dias anteriores sem saída</h2>
  <p>Informe a hora em que saíram ou marque como sem registro. Enquanto isso não for feito, elas contam como abertas.</p>
  <ul class="lista-pendencias">{itens}</ul>
</section>"""


def html_presentes(presentes):
    if not presentes:
        return ('<p class="vazio">Ninguém no escritório agora. Clientes e prestadores aparecem '
                'aqui até você registrar a saída.</p>')
    linhas = ""
    for v in presentes:
        detalhe = f": {esc(v['detalhe'])}" if v["detalhe"] else ""
        linhas += f"""<li class="linha">
  <time class="margem">{v["hora_entrada"]}</time>
  <div class="conteudo"><p class="nome">{esc(v["nome"])}</p>
    <p class="mudo">{esc(v["tipo_txt"])}{detalhe}</p>
    <p class="mudo">Com {esc(v["atendentes_txt"])}</p></div>
  <div class="acao"><button class="btn" type="button" data-acao="saida" data-id="{v["id"]}">Registrar saída</button></div>
</li>"""
    return f'<ol class="livro">{linhas}</ol>'


def html_registros_de_hoje(registros):
    if not registros:
        return ('<p class="vazio">Nenhum registro hoje. O primeiro aparece aqui assim que '
                'você registrar.</p>')
    linhas = ""
    for v in registros:
        linhas += f"""<li class="linha">
  <time class="margem">{v["hora_entrada"]}</time>
  <div class="conteudo"><p class="nome">{esc(v["nome"])}</p>
    <p class="mudo">{esc(v["tipo_txt"])}, com {esc(v["atendentes_txt"])}</p></div>
  <p class="situacao situacao-{v["situacao"]}">{esc(v["situacao_txt"])}</p>
</li>"""
    return f'<ol class="livro livro-compacto">{linhas}</ol>'


def pagina_recepcao():
    pessoas = estado.listar_pessoas(ESTADO, somente_ativas=True)
    dia = hoje()
    presentes, pendentes = logica.separar_abertas(estado.visitas_abertas(ESTADO), dia)
    de_hoje = [logica.preparar_visita(v, dia) for v in estado.buscar_visitas(ESTADO, dia, dia)]
    if pessoas:
        formulario = html_form_registro(FORM, pessoas)
    else:
        formulario = ('<p class="vazio">Ninguém está cadastrado para atender ainda. '
                      '<button class="link-quieto" type="button" data-acao="ir" data-aba="pessoas">'
                      'Cadastre as pessoas do escritório</button> para começar.</p>')
    return f"""<h1 class="sr-only">Recepção</h1>
{html_pendencias(pendentes)}
<div class="duas-colunas">
  <section class="painel" aria-labelledby="t-novo">
    <h2 id="t-novo">Novo registro</h2>
    {formulario}
  </section>
  <div class="coluna-direita">
    <section class="painel" aria-labelledby="t-presentes">
      <div class="cabeca"><h2 id="t-presentes">No escritório agora</h2>
        <span class="contador" aria-label="{len(presentes)} no escritório">{len(presentes)}</span></div>
      {html_presentes(presentes)}
    </section>
    <section class="painel" aria-labelledby="t-hoje">
      <div class="cabeca"><h2 id="t-hoje">Registros de hoje</h2>
        <span class="contador" aria-label="{len(de_hoje)} registros">{len(de_hoje)}</span></div>
      {html_registros_de_hoje(de_hoje)}
    </section>
  </div>
</div>"""


def enviar_registro(formulario):
    global FORM
    lido = ler_form(formulario)
    ativos = estado.listar_pessoas(ESTADO, somente_ativas=True)
    ids_validos = {p["id"] for p in ativos}
    form = {chave: valor for chave, valor in lido.items()}
    form["atendentes"] = lido.get("atendentes", [])
    dados, erros = logica.validar_registro(form, agora(), ids_validos)
    if erros:
        FORM = capturar_form(formulario, erros)
        render()
        return
    estado.inserir_visita(ESTADO, dados)
    salvar()
    rotulo = logica.CAMPOS_POR_TIPO[dados["tipo"]]["rotulo"]
    flash("ok", f"Registrado: {rotulo}, {dados['nome']}")
    FORM = form_inicial()
    render()


def registrar_saida_agora(visita_id):
    quando = agora().replace(second=0, microsecond=0)
    texto = f"{quando.year:04d}-{quando.month:02d}-{quando.day:02d} {quando.hour:02d}:{quando.minute:02d}"
    if estado.registrar_saida(ESTADO, visita_id, texto):
        salvar()
        flash("ok", "Saída registrada")
    else:
        flash("erro", "Essa visita não está mais aberta")
    render()


def resolver_pendencia(botao, visita_id, acao):
    visita = estado.buscar_visita(ESTADO, visita_id)
    if visita is None:
        flash("erro", "Visita não encontrada")
    elif acao == "pend_sem":
        if estado.marcar_sem_registro_de_saida(ESTADO, visita_id):
            salvar()
            flash("ok", "Marcada como saída não registrada")
    else:
        item = acima(botao, "li")
        campo = item.select_one("input[name=hora]")
        saida_em, erro = logica.montar_saida(visita["entrada_em"], campo.value)
        if erro:
            flash("erro", erro)
        elif estado.registrar_saida(ESTADO, visita_id, saida_em):
            salvar()
            flash("ok", "Saída informada")
    render()


# ----------------------------------------------------------- aba Histórico

def consultar_historico():
    dia = hoje()
    tipo = FILTRO_HIST["tipo"] if FILTRO_HIST["tipo"] in logica.CAMPOS_POR_TIPO else ""
    de, ate, erro = logica.validar_periodo(FILTRO_HIST["de"], FILTRO_HIST["ate"], dia)
    preparadas = [logica.preparar_visita(v, dia)
                  for v in estado.buscar_visitas(ESTADO, de, ate, tipo or None)]
    return {"visitas": logica.filtrar_por_texto(preparadas, FILTRO_HIST["q"]),
            "de": de, "ate": ate, "erro": erro}


def html_resultado_historico(consulta):
    visitas = consulta["visitas"]
    n = len(visitas)
    titulo = (f'{n} {plural(n, "registro", "registros")} de {dmy(consulta["de"])} '
              f'a {dmy(consulta["ate"])}')
    erro = ""
    if consulta["erro"]:
        erro = f'<p class="erro-geral" role="alert">{esc(consulta["erro"])}. Mostrando os últimos 30 dias.</p>'
    if not visitas:
        corpo = ('<p class="vazio">Nenhum registro encontrado. Amplie o período ou confira '
                 'a grafia do nome.</p>')
    else:
        linhas = ""
        for v in visitas[:MAXIMO_LINHAS]:
            extra = ""
            if v["detalhe"]:
                extra += f'<span class="mudo bloco">{esc(v["detalhe"])}</span>'
            if v["origem"]:
                extra += f'<span class="mudo bloco">Por parte de {esc(v["origem"])}</span>'
            if v["observacao"]:
                extra += f'<span class="mudo bloco">{esc(v["observacao"])}</span>'
            permanencia = (f'<span class="mudo bloco">{esc(v["permanencia_txt"])} no escritório</span>'
                           if v["permanencia_txt"] else "")
            linhas += f"""<tr>
  <td>{esc(v["rotulo_data"])}</td>
  <td class="hora">{v["hora_entrada"]}</td>
  <td class="hora">{v["hora_saida"] or "-"}</td>
  <td>{esc(v["tipo_txt"])}</td>
  <td><strong>{esc(v["nome"])}</strong>{extra}</td>
  <td>{esc(v["atendentes_txt"])}</td>
  <td><span class="situacao situacao-{v["situacao"]}">{esc(v["situacao_txt"])}</span>{permanencia}</td>
</tr>"""
        limite = ""
        if n > MAXIMO_LINHAS:
            limite = (f'<p class="dica">Mostrando os {MAXIMO_LINHAS} mais recentes de {n}. '
                      'Refine o filtro; a planilha exportada leva todos.</p>')
        corpo = f"""{limite}<div class="tabela-rolagem"><table class="tabela">
  <thead><tr><th scope="col">Data</th><th scope="col">Entrada</th><th scope="col">Saída</th>
    <th scope="col">Tipo</th><th scope="col">Nome ou empresa</th><th scope="col">Quem atendeu</th>
    <th scope="col">Situação</th></tr></thead>
  <tbody>{linhas}</tbody></table></div>"""
    return f'{erro}<div class="cabeca"><h2 id="t-resultado">{titulo}</h2></div>{corpo}'


def pagina_historico():
    f = FILTRO_HIST
    opcoes = '<option value="">Todos</option>' + "".join(
        f'<option value="{chave}"{" selected" if chave == f["tipo"] else ""}>{esc(cfg["rotulo"])}</option>'
        for chave, cfg in logica.CAMPOS_POR_TIPO.items())
    return f"""<h1 class="sr-only">Histórico de visitas</h1>
<section class="painel" aria-labelledby="t-filtro">
  <h2 id="t-filtro">Buscar no histórico</h2>
  <form data-form="filtro" class="filtros">
    <label class="campo campo-largo"><span>Nome, empresa, serviço ou observação</span>
      <input type="search" id="f-q" data-filtro="historico" value="{esc(f["q"])}" placeholder="Marcos Tavares" autocomplete="off"></label>
    <label class="campo"><span>Tipo</span><select id="f-tipo" data-filtro="historico">{opcoes}</select></label>
    <label class="campo"><span>De</span><input type="date" id="f-de" data-filtro="historico" value="{esc(f["de"])}"></label>
    <label class="campo"><span>Até</span><input type="date" id="f-ate" data-filtro="historico" value="{esc(f["ate"])}"></label>
    <div class="botoes-filtro"><button class="btn" type="button" data-acao="exportar">Exportar para Excel</button></div>
  </form>
</section>
<section class="painel" id="resultado-historico" aria-labelledby="t-resultado">
  {html_resultado_historico(consultar_historico())}
</section>"""


def atualizar_historico():
    FILTRO_HIST["q"] = document["f-q"].value
    FILTRO_HIST["tipo"] = document["f-tipo"].value
    FILTRO_HIST["de"] = document["f-de"].value
    FILTRO_HIST["ate"] = document["f-ate"].value
    document["resultado-historico"].html = html_resultado_historico(consultar_historico())


def exportar_excel():
    consulta = consultar_historico()
    if consulta["erro"]:
        flash("erro", consulta["erro"])
        render()
        return
    nome = f"visitas_{consulta['de'].isoformat()}_a_{consulta['ate'].isoformat()}.csv"
    baixar(nome, logica.gerar_csv(consulta["visitas"]), "text/csv;charset=utf-8", com_bom=True)


# ------------------------------------------------------------ aba Gráficos

def montar_graficos():
    dia = hoje()
    de, ate, erro = logica.validar_periodo(FILTRO_GRAF["de"], FILTRO_GRAF["ate"], dia)
    preparadas = [logica.preparar_visita(v, dia) for v in estado.buscar_visitas(ESTADO, de, ate)]
    return logica.estatisticas(preparadas, de, ate), de, ate, erro


def html_resultado_graficos(dados, de, ate, erro):
    aviso = ""
    if erro:
        aviso = f'<p class="erro-geral" role="alert">{esc(erro)}. Mostrando os últimos 30 dias.</p>'
    if dados["total"] == 0:
        return (aviso + '<section class="painel"><p class="vazio">Nenhum registro entre '
                f'{dmy(de)} e {dmy(ate)}. Escolha outro período para ver os gráficos.</p></section>')
    media = f'{dados["permanencia_media_min"]} min' if dados["permanencia_media_min"] is not None else "-"
    taxa = f'{dados["taxa_saida_registrada"]}%' if dados["taxa_saida_registrada"] is not None else "-"
    titulo_dia = "Registros por semana" if dados["por_dia"]["semanal"] else "Registros por dia"
    return f"""{aviso}
<section class="indicadores" aria-label="Resumo do período">
  <div class="painel indicador"><p class="numero">{dados["total"]}</p><p class="mudo">registros no período</p></div>
  <div class="painel indicador"><p class="numero">{dados["visitantes_distintos"]}</p>
    <p class="mudo">visitantes diferentes (clientes, prestadores e outros)</p></div>
  <div class="painel indicador"><p class="numero">{media}</p><p class="mudo">permanência média por visita</p></div>
  <div class="painel indicador"><p class="numero">{taxa}</p><p class="mudo">das saídas foram registradas</p></div>
</section>
<div class="grade-graficos">
  <section class="painel painel-largo" aria-labelledby="g-dia">
    <h2 id="g-dia">{titulo_dia}</h2>
    <p class="mudo">Todos os tipos de registro, empilhados por tipo.</p>
    <div class="grafico"><canvas id="grafico-dia" role="img" aria-label="Registros por dia, empilhados por tipo"></canvas></div>
  </section>
  <section class="painel" aria-labelledby="g-frequentes">
    <h2 id="g-frequentes">Quem mais veio ao escritório</h2>
    <p class="mudo">Número de visitas. Considera clientes, prestadores e outros que ficam no escritório.</p>
    <div class="grafico"><canvas id="grafico-frequentes" role="img" aria-label="Visitantes mais frequentes"></canvas></div>
  </section>
  <section class="painel" aria-labelledby="g-tempo">
    <h2 id="g-tempo">Quem ficou mais tempo</h2>
    <p class="mudo">Soma dos minutos no escritório. Só entram visitas com saída registrada: {dados["visitas_com_saida"]} de {dados["visitas_presenciais"]}.</p>
    <div class="grafico"><canvas id="grafico-tempo" role="img" aria-label="Visitantes com maior tempo no escritório"></canvas></div>
  </section>
  <section class="painel" aria-labelledby="g-horas">
    <h2 id="g-horas">Horários de maior movimento</h2>
    <p class="mudo">Registros por hora de chegada, somando todos os dias do período.</p>
    <div class="grafico"><canvas id="grafico-horas" role="img" aria-label="Registros por hora do dia"></canvas></div>
  </section>
  <section class="painel" aria-labelledby="g-atendem">
    <h2 id="g-atendem">Quem mais recebeu visitas</h2>
    <p class="mudo">Número de registros em que a pessoa foi citada.</p>
    <div class="grafico"><canvas id="grafico-atendem" role="img" aria-label="Pessoas que mais receberam visitas"></canvas></div>
  </section>
  <section class="painel painel-largo" aria-labelledby="g-saidas">
    <h2 id="g-saidas">Qualidade do registro de saída</h2>
    <p class="mudo">O caderno nunca registrou saídas. Aqui aparece quantas foram registradas pelo sistema.</p>
    <div class="grafico grafico-baixo"><canvas id="grafico-saidas" role="img" aria-label="Situação das saídas"></canvas></div>
  </section>
</div>"""


def desenhar_graficos(dados):
    if dados["total"]:
        window.desenharGraficos(json.dumps(dados, ensure_ascii=False))


def pagina_graficos():
    dia = hoje()
    atalhos = [("Últimos 7 dias", dia - timedelta(days=6)),
               ("Últimos 30 dias", dia - timedelta(days=30)),
               ("Este mês", dia.replace(day=1))]
    botoes = "".join(
        f'<button class="btn btn-quieto" type="button" data-acao="grafico_periodo" '
        f'data-de="{inicio.isoformat()}" data-ate="{dia.isoformat()}">{rotulo}</button>'
        for rotulo, inicio in atalhos)
    dados, de, ate, erro = montar_graficos()
    pagina_graficos.dados = dados
    return f"""<h1 class="sr-only">Gráficos do período</h1>
<section class="painel" aria-labelledby="t-periodo">
  <h2 id="t-periodo">Período analisado</h2>
  <form data-form="filtro" class="filtros">
    <label class="campo"><span>De</span><input type="date" id="g-de" data-filtro="graficos" value="{esc(FILTRO_GRAF["de"])}"></label>
    <label class="campo"><span>Até</span><input type="date" id="g-ate" data-filtro="graficos" value="{esc(FILTRO_GRAF["ate"])}"></label>
    <div class="botoes-filtro">{botoes}</div>
  </form>
</section>
<div id="resultado-graficos">{html_resultado_graficos(dados, de, ate, erro)}</div>"""


def atualizar_graficos():
    FILTRO_GRAF["de"] = document["g-de"].value
    FILTRO_GRAF["ate"] = document["g-ate"].value
    dados, de, ate, erro = montar_graficos()
    document["resultado-graficos"].html = html_resultado_graficos(dados, de, ate, erro)
    desenhar_graficos(dados)


# -------------------------------------------------------------- aba Pessoas

def pagina_pessoas():
    pessoas = estado.listar_pessoas(ESTADO)
    cargos = "".join(f"<option>{esc(c)}</option>" for c in logica.CARGOS)
    if pessoas:
        itens = ""
        for p in pessoas:
            marcas = ""
            if p["frequente"]:
                marcas += ", frequente"
            if not p["ativo"]:
                marcas += ", inativa"
            classe = "" if p["ativo"] else ' class="inativa"'
            itens += f"""<li{classe}>
  <div><strong>{esc(p["nome"])}</strong><span class="mudo bloco">{esc(p["cargo"])}{marcas}</span></div>
  <div class="linha-form">
    <button class="btn btn-quieto" type="button" data-acao="pessoa_alternar" data-id="{p["id"]}" data-campo="frequente">{"Tirar destaque" if p["frequente"] else "Destacar"}</button>
    <button class="btn btn-quieto" type="button" data-acao="pessoa_alternar" data-id="{p["id"]}" data-campo="ativo">{"Desativar" if p["ativo"] else "Reativar"}</button>
  </div>
</li>"""
        lista = (f'<ul class="lista-pessoas">{itens}</ul><p class="dica">Pessoas desativadas saem '
                 'da recepção, mas continuam no histórico.</p>')
    else:
        lista = ('<p class="vazio">Nenhuma pessoa cadastrada. Comece por quem recebe visitas '
                 'com mais frequência.</p>')
    return f"""<h1 class="sr-only">Pessoas do escritório</h1>
<div class="duas-colunas">
  <section class="painel" aria-labelledby="t-nova">
    <h2 id="t-nova">Cadastrar pessoas</h2>
    <form data-form="pessoas">
      <label class="campo"><span>Nome (um por linha, para cadastrar várias de uma vez)</span>
        <textarea name="nome" rows="4" maxlength="2000" placeholder="Dra. Helena Duarte"></textarea></label>
      <label class="campo"><span>Cargo (vale para todas as linhas)</span>
        <select name="cargo">{cargos}</select></label>
      <label class="campo campo-caixa"><input type="checkbox" name="frequente" value="1">
        <span>Recebem visitas com frequência (aparecem em destaque na recepção)</span></label>
      <button class="btn btn-primario" type="submit">Cadastrar</button>
    </form>
  </section>
  <section class="painel" aria-labelledby="t-lista">
    <div class="cabeca"><h2 id="t-lista">Quem atende</h2>
      <span class="contador" aria-label="{len(pessoas)} pessoas">{len(pessoas)}</span></div>
    {lista}
  </section>
</div>"""


def cadastrar_pessoas(formulario):
    lido = ler_form(formulario)
    cargo = lido.get("cargo", "")
    nomes = [logica.limpar_texto(linha) for linha in str(lido.get("nome", "")).splitlines()]
    nomes = [n for n in nomes if n]
    if not nomes:
        flash("erro", "Digite o nome da pessoa")
    elif cargo not in logica.CARGOS:
        flash("erro", "Escolha o cargo")
    elif any(len(n) > logica.LIMITE_TEXTO for n in nomes):
        flash("erro", f"Use até {logica.LIMITE_TEXTO} caracteres em cada nome")
    else:
        criadas, repetidas = 0, []
        for nome in nomes:
            if estado.criar_pessoa(ESTADO, nome, cargo, bool(lido.get("frequente"))):
                criadas += 1
            else:
                repetidas.append(nome)
        if criadas:
            salvar()
            flash("ok", f"{criadas} {plural(criadas, 'pessoa cadastrada', 'pessoas cadastradas')}")
        if repetidas:
            flash("erro", "Já estavam cadastradas: " + ", ".join(repetidas))
    render()


# ------------------------------------------------------------ desenho geral

PAGINAS = {"recepcao": pagina_recepcao, "historico": pagina_historico,
           "graficos": pagina_graficos, "pessoas": pagina_pessoas}


def render(foco=True):
    for botao in document.select("nav button"):
        if atributo(botao, "data-aba") == ABA:
            botao.setAttribute("aria-current", "page")
        else:
            botao.removeAttribute("aria-current")
    document["data-hoje"].text = logica.data_por_extenso(hoje())
    document["faixa-avisos"].html = html_faixa()
    document["pagina"].html = html_flash() + PAGINAS[ABA]()
    document["rodape"].html = html_rodape()
    if ABA == "graficos":
        desenhar_graficos(pagina_graficos.dados)
    elif ABA == "recepcao" and foco:
        alvo = document.select_one(".tem-erro input") or document.select_one("#campos-dinamicos input")
        if alvo:
            alvo.focus()


def ir_para(aba):
    global ABA
    ABA = aba
    render()


# ----------------------------------------------------------------- eventos

def ao_clicar(ev):
    botao = acima(ev.target, "[data-acao]")
    if botao is None:
        return
    acao = atributo(botao, "data-acao")
    if not acao:
        return
    ident = atributo(botao, "data-id")
    numero = int(ident) if ident.isdigit() else 0
    if acao == "ir":
        ir_para(atributo(botao, "data-aba"))
    elif acao == "saida":
        registrar_saida_agora(numero)
    elif acao in ("pend_informar", "pend_sem"):
        resolver_pendencia(botao, numero, acao)
    elif acao == "pessoa_alternar":
        estado.alternar_pessoa(ESTADO, numero, atributo(botao, "data-campo"))
        salvar()
        render()
    elif acao == "exportar":
        exportar_excel()
    elif acao == "grafico_periodo":
        FILTRO_GRAF["de"] = atributo(botao, "data-de")
        FILTRO_GRAF["ate"] = atributo(botao, "data-ate")
        render()
    elif acao == "backup":
        fazer_copia_de_seguranca()
    elif acao == "restaurar":
        document["arquivo-restaurar"].click()
    elif acao == "demo_entrar":
        window.location.search = "?demo"
    elif acao == "demo_sair":
        window.location.href = str(window.location.href).split("?")[0].split("#")[0]


def ao_enviar(ev):
    ev.preventDefault()
    tipo = atributo(ev.target, "data-form")
    if tipo == "registro":
        enviar_registro(ev.target)
    elif tipo == "pessoas":
        cadastrar_pessoas(ev.target)


def ao_mudar(ev):
    global FORM
    alvo = ev.target
    ident = alvo.id
    if ident == "tipo":
        FORM = capturar_form(acima(alvo, "form"))
        render()
        document.select_one("#campos-dinamicos input").focus()
    elif ident == "controla-saida":
        tipo = document["tipo"].value
        document["dica-saida"].text = dica_de_saida(tipo, alvo.checked)
    elif ident == "arquivo-restaurar":
        escolher_arquivo(alvo)
    else:
        filtro = atributo(alvo, "data-filtro")
        if filtro == "historico":
            atualizar_historico()
        elif filtro == "graficos":
            atualizar_graficos()


# ------------------------------------------------- cópia de segurança

def fazer_copia_de_seguranca():
    texto = json.dumps(ESTADO, ensure_ascii=False, indent=1)
    dia = hoje()
    baixar(f"livro_de_visitas_copia_{dia.isoformat()}.json", texto, "application/json;charset=utf-8")
    gravar_armazenamento(CHAVE_COPIA, dia.isoformat())
    flash("ok", "Cópia de segurança gerada. Procure o arquivo na pasta Downloads e guarde "
                "em um lugar seguro (por exemplo, um pen drive).")
    render(foco=False)


def escolher_arquivo(campo):
    arquivo = campo.files.item(0)
    if not arquivo:
        return
    leitor = window.FileReader.new()

    def ao_terminar(_ev):
        restaurar_de_texto(str(leitor.result))

    leitor.onload = ao_terminar
    leitor.readAsText(arquivo)
    campo.value = ""


def restaurar_de_texto(texto):
    global ESTADO
    try:
        lido = json.loads(texto.lstrip("﻿"))
    except Exception:
        lido = None
    if not estado.estrutura_valida(lido):
        flash("erro", "Esse arquivo não parece uma cópia de segurança do Livro de visitas. "
                      "Nada foi alterado.")
        render(foco=False)
        return
    resumo = (f"{len(lido['visitas'])} {plural(len(lido['visitas']), 'registro', 'registros')} e "
              f"{len(lido['pessoas'])} {plural(len(lido['pessoas']), 'pessoa', 'pessoas')}")
    if not window.confirm(f"Substituir os dados de agora por esta cópia ({resumo})? "
                          "Os dados de agora serão perdidos."):
        return
    ESTADO = lido
    salvar()
    flash("ok", f"Cópia restaurada: {resumo}.")
    render(foco=False)


# -------------------------------------------------------------- início

def iniciar():
    global FORM
    carregar()
    dia = hoje()
    FORM = form_inicial()
    FILTRO_HIST.update({"q": "", "tipo": "", "de": (dia - timedelta(days=30)).isoformat(),
                        "ate": dia.isoformat()})
    FILTRO_GRAF.update({"de": (dia - timedelta(days=30)).isoformat(), "ate": dia.isoformat()})
    document.bind("click", ao_clicar)
    document.bind("submit", ao_enviar)
    document.bind("change", ao_mudar)
    document.bind("input", ao_mudar)
    render()


try:
    iniciar()
except Exception as erro:
    document["pagina"].html = ('<p class="aviso-curto erro" role="alert">O sistema não conseguiu '
                               'iniciar: ' + esc(repr(erro)) + '</p>')
    raise
