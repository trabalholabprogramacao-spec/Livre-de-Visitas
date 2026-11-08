"""Regras de negócio do Livro de visitas: O ALGORITMO.

Python puro: este módulo não conhece o navegador nem arquivo nenhum. Ele
recebe e devolve dicionários e listas, então roda igual no navegador (dentro
do Livro_de_Visitas.html, via Brython) e no Python do computador, onde é
testado com pytest (veja testes/).
"""
import re
from datetime import date, datetime, timedelta

FORMATO_BANCO = "%Y-%m-%d %H:%M"
FORMATOS_ENTRADA_FORM = ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S")
LIMITE_TEXTO = 120
LIMITE_OBSERVACAO = 300

CARGOS = ["Advogado(a)", "Sócio(a)", "Secretária", "Demais"]
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
DIAS_SEMANA_EXTENSO = ["segunda-feira", "terça-feira", "quarta-feira",
                       "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _campo(nome, rotulo, obrigatorio, exemplo):
    return {"nome": nome, "rotulo": rotulo,
            "obrigatorio": obrigatorio, "exemplo": exemplo}


# Fonte única de verdade dos tipos de registro. A tela monta o formulário a
# partir deste dicionário, e a validação usa o mesmo dicionário: para criar um
# tipo novo basta adicionar uma entrada aqui.
CAMPOS_POR_TIPO = {
    "cliente": {
        "rotulo": "Cliente",
        "controla_saida": True,
        "rotulo_atendente": "Quem atende",
        "campos": [
            _campo("nome", "Nome e sobrenome", True, "Marcos Tavares"),
        ],
    },
    "prestador": {
        "rotulo": "Prestador de serviço",
        "controla_saida": True,
        "rotulo_atendente": "Quem recebe",
        "campos": [
            _campo("nome", "Empresa", True, "Refrigeração Alfa"),
            _campo("detalhe", "Serviço", True, "Manutenção do purificador"),
        ],
    },
    "envelope": {
        "rotulo": "Envelope",
        "controla_saida": False,
        "rotulo_atendente": "Para quem",
        "campos": [
            _campo("nome", "Empresa de motoboy", True, "Moto Ágil"),
            _campo("origem", "Por parte de", True, "Banco Delta"),
        ],
    },
    "entrega": {
        "rotulo": "Entrega de material",
        "controla_saida": False,
        "rotulo_atendente": "Quem recebe",
        "campos": [
            _campo("nome", "Empresa", True, "Distribuidora Sul"),
            _campo("detalhe", "Material", True, "Papel toalha, café e copos"),
        ],
    },
    "outro": {
        "rotulo": "Outro",
        "controla_saida": True,
        "rotulo_atendente": "Quem atende",
        "campos": [
            _campo("tipo_outro", "Qual tipo de registro?", True,
                   "Candidato a vaga"),
            _campo("nome", "Nome", True, "Fernanda Lopes"),
        ],
    },
}


# ---------------------------------------------------------------- textos

def limpar_texto(texto):
    """Remove espaços nas pontas e junta espaços repetidos."""
    return re.sub(r"\s+", " ", texto or "").strip()


_SEM_ACENTO = str.maketrans(
    "áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ",
    "aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN")


def normalizar_busca(texto):
    """Minúsculas e sem acento, para que 'Jose' encontre 'José'."""
    return (texto or "").translate(_SEM_ACENTO).lower()


# ---------------------------------------------------------------- datas

def converter_data_hora(texto):
    return datetime.strptime(texto, FORMATO_BANCO)


def rotulo_data(dia, hoje):
    if dia == hoje:
        return "hoje"
    if dia == hoje - timedelta(days=1):
        return "ontem"
    return f"{dia:%d/%m/%Y} ({DIAS_SEMANA[dia.weekday()]})"


def data_por_extenso(dia):
    return (f"{DIAS_SEMANA_EXTENSO[dia.weekday()]}, "
            f"{dia.day} de {MESES[dia.month - 1]}")


def validar_periodo(de_txt, ate_txt, hoje, dias_padrao=30):
    """Lê as datas do filtro. Devolve (de, ate, erro).

    Campo vazio usa o padrão (últimos 30 dias até hoje). Se algo estiver
    inválido, devolve o padrão e a mensagem de erro para a tela.
    """
    padrao_de = hoje - timedelta(days=dias_padrao)
    padrao_ate = hoje

    def ler(texto, padrao):
        texto = (texto or "").strip()
        if not texto:
            return padrao, None
        try:
            return datetime.strptime(texto, "%Y-%m-%d").date(), None
        except ValueError:
            return padrao, "Data inválida"

    de, erro_de = ler(de_txt, padrao_de)
    ate, erro_ate = ler(ate_txt, padrao_ate)
    if erro_de or erro_ate:
        return padrao_de, padrao_ate, "Confira as datas do filtro"
    if de > ate:
        return padrao_de, padrao_ate, "A data inicial é depois da final"
    return de, ate, None


def minutos_permanencia(entrada_em, saida_em):
    if not saida_em:
        return None
    segundos = (converter_data_hora(saida_em)
                - converter_data_hora(entrada_em)).total_seconds()
    return max(0, int(segundos // 60))


def formatar_permanencia(minutos):
    if minutos is None:
        return ""
    if minutos < 60:
        return f"{minutos} min"
    return f"{minutos // 60}h{minutos % 60:02d}"


def montar_saida(entrada_em, hora_txt):
    """Combina o dia da chegada com a hora informada. Devolve (saida, erro)."""
    hora_txt = (hora_txt or "").strip()
    if not hora_txt:
        return None, "Informe a hora de saída"
    try:
        hora = datetime.strptime(hora_txt, "%H:%M").time()
    except ValueError:
        return None, "Hora inválida"
    entrada = converter_data_hora(entrada_em)
    saida = datetime.combine(entrada.date(), hora)
    if saida < entrada:
        return None, "A saída não pode ser antes da chegada"
    return saida.strftime(FORMATO_BANCO), None


# ------------------------------------------------------------- validação

def validar_registro(form, agora, ids_validos):
    """Valida um novo registro. Devolve (dados, erros).

    form: dicionário simples com tipo, campos do tipo, observacao,
          atendentes (lista de ids em texto), atendente_outro, entrada e
          controla_saida.
    ids_validos: ids de pessoas ativas (ignora qualquer outro id enviado).
    Se houver erros, dados vem None e erros mapeia campo -> mensagem.
    """
    tipo = form.get("tipo", "")
    config = CAMPOS_POR_TIPO.get(tipo)
    if config is None:
        return None, {"tipo": "Escolha o tipo de registro"}

    erros = {}
    dados = {"tipo": tipo, "nome": "", "detalhe": "", "origem": "",
             "tipo_outro": ""}

    for campo in config["campos"]:
        valor = limpar_texto(form.get(campo["nome"]))
        if not valor and campo["obrigatorio"]:
            erros[campo["nome"]] = f"Preencha: {campo['rotulo'].lower()}"
        elif len(valor) > LIMITE_TEXTO:
            erros[campo["nome"]] = f"Use até {LIMITE_TEXTO} caracteres"
        dados[campo["nome"]] = valor

    dados["observacao"] = limpar_texto(form.get("observacao"))
    if len(dados["observacao"]) > LIMITE_OBSERVACAO:
        erros["observacao"] = f"Use até {LIMITE_OBSERVACAO} caracteres"

    ids = []
    for bruto in form.get("atendentes", []):
        try:
            numero = int(bruto)
        except (TypeError, ValueError):
            continue
        if numero in ids_validos and numero not in ids:
            ids.append(numero)
    atendente_outro = limpar_texto(form.get("atendente_outro"))
    if len(atendente_outro) > LIMITE_TEXTO:
        erros["atendentes"] = f"Use até {LIMITE_TEXTO} caracteres no nome"
    elif not ids and not atendente_outro:
        erros["atendentes"] = f"Informe: {config['rotulo_atendente'].lower()}"
    dados["atendentes_ids"] = ids
    dados["atendente_outro"] = atendente_outro

    bruto = (form.get("entrada") or "").strip()
    entrada = agora.replace(second=0, microsecond=0)
    if bruto:
        entrada = None
        for formato in FORMATOS_ENTRADA_FORM:
            try:
                entrada = datetime.strptime(bruto, formato)
                break
            except ValueError:
                continue
        if entrada is None:
            erros["entrada"] = "Data e hora inválidas"
        elif entrada > agora + timedelta(minutes=1):
            erros["entrada"] = "A chegada não pode ser no futuro"
    if entrada is not None:
        dados["entrada_em"] = entrada.strftime(FORMATO_BANCO)

    if tipo == "outro":
        dados["controla_saida"] = 1 if form.get("controla_saida") else 0
    else:
        dados["controla_saida"] = 1 if config["controla_saida"] else 0

    if erros:
        return None, erros
    return dados, {}


# --------------------------------------------- situação de cada visita

def situacao(visita, hoje):
    """Classifica a visita em um destes códigos:

    unica           registro sem controle de saída (envelope, entrega)
    saiu            saída registrada
    nao_registrada  alguém marcou que a saída não foi anotada
    presente        chegou hoje e ainda não saiu
    pendente        chegou em dia anterior e a saída nunca foi tratada
    """
    if not visita["controla_saida"]:
        return "unica"
    if visita.get("saida_em"):
        return "saiu"
    if visita.get("status_saida") == "nao_registrada":
        return "nao_registrada"
    if visita["entrada_em"][:10] == hoje.strftime("%Y-%m-%d"):
        return "presente"
    return "pendente"


def lista_atendentes(visita):
    nomes = list(visita.get("atendentes_cadastrados") or [])
    if visita.get("atendente_outro"):
        nomes.append(f"{visita['atendente_outro']} (não cadastrada)")
    return nomes


def preparar_visita(visita, hoje):
    """Devolve uma cópia da visita com os campos prontos para exibir."""
    v = dict(visita)
    entrada = converter_data_hora(v["entrada_em"])
    v["data_entrada"] = entrada.date()
    v["rotulo_data"] = rotulo_data(entrada.date(), hoje)
    v["hora_entrada"] = entrada.strftime("%H:%M")
    v["hora_saida"] = (converter_data_hora(v["saida_em"]).strftime("%H:%M")
                       if v.get("saida_em") else "")
    v["situacao"] = situacao(v, hoje)
    v["situacao_txt"] = {
        "unica": "Registro único",
        "saiu": f"Saiu às {v['hora_saida']}",
        "nao_registrada": "Saída não registrada",
        "presente": "No escritório",
        "pendente": "Saída pendente",
    }[v["situacao"]]
    v["permanencia_min"] = minutos_permanencia(v["entrada_em"], v.get("saida_em"))
    v["permanencia_txt"] = formatar_permanencia(v["permanencia_min"])
    config = CAMPOS_POR_TIPO.get(v["tipo"], {})
    if v["tipo"] == "outro" and v.get("tipo_outro"):
        v["tipo_txt"] = f"Outro: {v['tipo_outro']}"
    else:
        v["tipo_txt"] = config.get("rotulo", v["tipo"])
    v["atendentes"] = lista_atendentes(v)
    v["atendentes_txt"] = ", ".join(v["atendentes"])
    return v


def separar_abertas(visitas, hoje):
    """Separa visitas abertas em (presentes hoje, pendentes de dias antes)."""
    presentes, pendentes = [], []
    for visita in visitas:
        v = preparar_visita(visita, hoje)
        if v["situacao"] == "presente":
            presentes.append(v)
        elif v["situacao"] == "pendente":
            pendentes.append(v)
    presentes.sort(key=lambda v: v["entrada_em"])
    pendentes.sort(key=lambda v: v["entrada_em"])
    return presentes, pendentes


def filtrar_por_texto(visitas, texto):
    """Mantém as visitas que contêm TODAS as palavras digitadas.

    A busca ignora acento e maiúsculas e olha nome, serviço, material,
    origem, tipo, observação e quem atendeu. 'tavares marcos' encontra
    'Marcos Tavares'.
    """
    palavras = normalizar_busca(texto).split()
    if not palavras:
        return list(visitas)
    resultado = []
    for v in visitas:
        palheiro = normalizar_busca(" ".join([
            v["nome"], v["detalhe"], v["origem"], v["tipo_txt"],
            v["observacao"], v["atendentes_txt"],
        ]))
        if all(palavra in palheiro for palavra in palavras):
            resultado.append(v)
    return resultado


# --------------------------------------------------- estatísticas (gráficos)

LIMITE_RANKING = 8
SUFIXO_NAO_CADASTRADA = " (não cadastrada)"


def _blocos_do_periodo(de, ate):
    """Divide o período em dias (até 45 dias) ou semanas (períodos maiores),
    para o gráfico de barras não ficar com centenas de colunas."""
    semanal = (ate - de).days + 1 > 45

    def inicio(dia):
        return dia - timedelta(days=dia.weekday()) if semanal else dia

    blocos, cursor = [], inicio(de)
    while cursor <= ate:
        blocos.append(cursor)
        cursor += timedelta(days=7 if semanal else 1)
    if semanal:
        rotulos = [f"Sem. {b:%d/%m}" for b in blocos]
    else:
        rotulos = [f"{DIAS_SEMANA[b.weekday()]} {b:%d/%m}" for b in blocos]
    return blocos, rotulos, inicio


def estatisticas(visitas, de, ate):
    """Resume as visitas de um período para os gráficos.

    visitas: lista de visitas já preparadas (preparar_visita).
    Devolve só números e textos (serializável em JSON).
    """
    blocos, rotulos, inicio_do_bloco = _blocos_do_periodo(de, ate)
    posicao = {bloco: i for i, bloco in enumerate(blocos)}
    por_tipo = {tipo: [0] * len(blocos) for tipo in CAMPOS_POR_TIPO}
    horas = {}
    atendimentos = {}
    visitantes = {}
    saiu = sem_saida = ainda = 0

    for v in visitas:
        por_tipo[v["tipo"]][posicao[inicio_do_bloco(v["data_entrada"])]] += 1

        hora = int(v["entrada_em"][11:13])
        horas[hora] = horas.get(hora, 0) + 1

        for nome in v["atendentes"]:
            atendimentos[nome] = atendimentos.get(nome, 0) + 1

        if v["controla_saida"]:
            chave = normalizar_busca(v["nome"])
            item = visitantes.setdefault(
                chave, {"nome": v["nome"], "visitas": 0, "minutos": 0, "com_saida": 0})
            item["visitas"] += 1
            if v["permanencia_min"] is not None:
                item["minutos"] += v["permanencia_min"]
                item["com_saida"] += 1

        if v["situacao"] == "saiu":
            saiu += 1
        elif v["situacao"] in ("nao_registrada", "pendente"):
            sem_saida += 1
        elif v["situacao"] == "presente":
            ainda += 1

    itens = list(visitantes.values())
    mais_frequentes = sorted(
        itens, key=lambda i: (-i["visitas"], normalizar_busca(i["nome"])))[:LIMITE_RANKING]
    maior_tempo = sorted(
        (i for i in itens if i["com_saida"]),
        key=lambda i: (-i["minutos"], normalizar_busca(i["nome"])))[:LIMITE_RANKING]
    mais_atenderam = sorted(
        atendimentos.items(), key=lambda p: (-p[1], normalizar_busca(p[0])))[:LIMITE_RANKING]

    if horas:
        primeira, ultima = min(8, min(horas)), max(18, max(horas))
    else:
        primeira, ultima = 8, 18
    faixa = range(primeira, ultima + 1)

    com_saida = sum(i["com_saida"] for i in itens)
    total_minutos = sum(i["minutos"] for i in itens)
    base_saida = saiu + sem_saida
    return {
        "total": len(visitas),
        "visitantes_distintos": len(itens),
        "permanencia_media_min": round(total_minutos / com_saida) if com_saida else None,
        "taxa_saida_registrada": round(100 * saiu / base_saida) if base_saida else None,
        "visitas_presenciais": saiu + sem_saida + ainda,
        "visitas_com_saida": com_saida,
        "por_dia": {
            "rotulos": rotulos,
            "semanal": (ate - de).days + 1 > 45,
            "series": [{"tipo": tipo, "rotulo": CAMPOS_POR_TIPO[tipo]["rotulo"], "valores": valores}
                       for tipo, valores in por_tipo.items() if any(valores)],
        },
        "mais_frequentes": [{"nome": i["nome"], "visitas": i["visitas"]} for i in mais_frequentes],
        "maior_tempo": [{"nome": i["nome"], "minutos": i["minutos"], "visitas": i["com_saida"],
                         "media": round(i["minutos"] / i["com_saida"])} for i in maior_tempo],
        "horarios": {"rotulos": [f"{h:02d}h" for h in faixa],
                     "valores": [horas.get(h, 0) for h in faixa]},
        "mais_atenderam": [{"nome": n, "visitas": q} for n, q in mais_atenderam],
        "saidas": {"registrada": saiu, "sem_registro": sem_saida, "no_escritorio": ainda},
    }


# ------------------------------------------------------ exportação (Excel)

COLUNAS_CSV = ["Data", "Entrada", "Saída", "Permanência", "Situação", "Tipo",
               "Nome / empresa", "Serviço / material", "Por parte de",
               "Quem atendeu", "Observação"]


def _celula_csv(valor):
    """Prepara um valor para uma célula: aspas quando necessário e proteção
    contra textos que o Excel trataria como fórmula (começam com = + - @)."""
    texto = "" if valor is None else str(valor)
    if texto[:1] in ("=", "+", "-", "@"):
        texto = "'" + texto
    if ";" in texto or '"' in texto or "\n" in texto or "\r" in texto:
        texto = '"' + texto.replace('"', '""') + '"'
    return texto


def gerar_csv(visitas_preparadas):
    """Gera o texto da planilha (separador ';', que o Excel em português abre
    direto). Recebe visitas já preparadas (preparar_visita), em ordem
    cronológica."""
    linhas = [";".join(COLUNAS_CSV)]
    for v in sorted(visitas_preparadas, key=lambda x: (x["entrada_em"], x["id"])):
        dia = v["data_entrada"]
        campos = [
            f"{dia.day:02d}/{dia.month:02d}/{dia.year}",
            v["hora_entrada"],
            v["hora_saida"],
            v["permanencia_txt"],
            "Saiu" if v.get("saida_em") else v["situacao_txt"],
            v["tipo_txt"],
            v["nome"],
            v["detalhe"],
            v["origem"],
            v["atendentes_txt"],
            v["observacao"],
        ]
        linhas.append(";".join(_celula_csv(c) for c in campos))
    return "\r\n".join(linhas) + "\r\n"
