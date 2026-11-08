"""Dados do sistema, SEM banco de dados.

Tudo fica em um único dicionário (o "estado") com duas listas:

    {"versao": 1,
     "proximo_id_pessoa": 12, "proximo_id_visita": 80,
     "pessoas": [{"id", "nome", "cargo", "frequente", "ativo"}, ...],
     "visitas": [{"id", "tipo", "nome", "entrada_em", "saida_em", ...}, ...]}

Python puro, sem navegador: este módulo só mexe no dicionário. Quem guarda o
dicionário no navegador (e na cópia de segurança) é o interface.py.
"""
import logica

VERSAO = 1

CAMPOS_VISITA = ("id", "tipo", "tipo_outro", "nome", "detalhe", "origem",
                 "observacao", "atendente_outro", "atendentes_cadastrados",
                 "controla_saida", "entrada_em", "saida_em", "status_saida")


def novo_estado():
    return {"versao": VERSAO, "proximo_id_pessoa": 1, "proximo_id_visita": 1,
            "pessoas": [], "visitas": []}


def estrutura_valida(obj):
    """Confere se um objeto lido de uma cópia de segurança parece um estado
    do sistema. Evita que um arquivo qualquer apague os dados atuais."""
    if not isinstance(obj, dict):
        return False
    if not isinstance(obj.get("pessoas"), list) or not isinstance(obj.get("visitas"), list):
        return False
    for chave in ("proximo_id_pessoa", "proximo_id_visita"):
        if not isinstance(obj.get(chave), int):
            return False
    for p in obj["pessoas"]:
        if not (isinstance(p, dict) and isinstance(p.get("id"), int)
                and isinstance(p.get("nome"), str) and isinstance(p.get("cargo"), str)):
            return False
    for v in obj["visitas"]:
        if not (isinstance(v, dict) and isinstance(v.get("id"), int)
                and v.get("tipo") in logica.CAMPOS_POR_TIPO
                and isinstance(v.get("nome"), str)
                and isinstance(v.get("entrada_em"), str)
                and len(v["entrada_em"]) == 16):
            return False
    return True


# ---------------------------------------------------------------- pessoas

def listar_pessoas(estado, somente_ativas=False):
    """Frequentes primeiro, depois ordem alfabética (sem considerar acento)."""
    pessoas = [p for p in estado["pessoas"] if p["ativo"] or not somente_ativas]
    return sorted(pessoas, key=lambda p: (-p["ativo"], -p["frequente"],
                                          logica.normalizar_busca(p["nome"])))


def criar_pessoa(estado, nome, cargo, frequente=False):
    """Devolve True se criou, False se já existe alguém com esse nome
    (ignorando maiúsculas e acentos)."""
    chave = logica.normalizar_busca(nome)
    for p in estado["pessoas"]:
        if logica.normalizar_busca(p["nome"]) == chave:
            return False
    estado["pessoas"].append({
        "id": estado["proximo_id_pessoa"], "nome": nome, "cargo": cargo,
        "frequente": 1 if frequente else 0, "ativo": 1})
    estado["proximo_id_pessoa"] += 1
    return True


def alternar_pessoa(estado, pessoa_id, campo):
    """Inverte 'ativo' ou 'frequente'. Pessoas nunca são apagadas: o histórico
    continua mostrando o nome delas."""
    if campo not in ("ativo", "frequente"):
        raise ValueError("campo inválido")
    for p in estado["pessoas"]:
        if p["id"] == pessoa_id:
            p[campo] = 1 - p[campo]
            return True
    return False


# ---------------------------------------------------------------- visitas

def inserir_visita(estado, dados):
    """Grava uma visita já validada (saída de logica.validar_registro).
    Guarda o NOME das pessoas, para o histórico não depender do cadastro."""
    nomes = []
    for pessoa in estado["pessoas"]:
        if pessoa["id"] in dados["atendentes_ids"]:
            nomes.append(pessoa["nome"])
    visita = {
        "id": estado["proximo_id_visita"],
        "tipo": dados["tipo"],
        "tipo_outro": dados["tipo_outro"],
        "nome": dados["nome"],
        "detalhe": dados["detalhe"],
        "origem": dados["origem"],
        "observacao": dados["observacao"],
        "atendente_outro": dados["atendente_outro"],
        "atendentes_cadastrados": sorted(nomes, key=logica.normalizar_busca),
        "controla_saida": dados["controla_saida"],
        "entrada_em": dados["entrada_em"],
        "saida_em": None,
        "status_saida": None,
    }
    estado["visitas"].append(visita)
    estado["proximo_id_visita"] += 1
    return visita["id"]


def buscar_visita(estado, visita_id):
    for v in estado["visitas"]:
        if v["id"] == visita_id:
            return v
    return None


def buscar_visitas(estado, de, ate, tipo=None):
    """Visitas cuja chegada está entre as datas `de` e `ate` (inclusive),
    da mais recente para a mais antiga."""
    inicio = de.isoformat() + " 00:00"
    fim = (ate + logica.timedelta(days=1)).isoformat() + " 00:00"
    achadas = [v for v in estado["visitas"]
               if inicio <= v["entrada_em"] < fim and (not tipo or v["tipo"] == tipo)]
    return sorted(achadas, key=lambda v: (v["entrada_em"], v["id"]), reverse=True)


def visitas_abertas(estado):
    """Visitas com controle de saída que ainda não tiveram a saída tratada."""
    return [v for v in estado["visitas"]
            if v["controla_saida"] and not v["saida_em"] and not v["status_saida"]]


def registrar_saida(estado, visita_id, saida_em):
    """Devolve True se a visita estava aberta e foi fechada."""
    v = buscar_visita(estado, visita_id)
    if v is None or not v["controla_saida"] or v["saida_em"] or v["status_saida"]:
        return False
    v["saida_em"] = saida_em
    return True


def marcar_sem_registro_de_saida(estado, visita_id):
    v = buscar_visita(estado, visita_id)
    if v is None or not v["controla_saida"] or v["saida_em"] or v["status_saida"]:
        return False
    v["status_saida"] = "nao_registrada"
    return True
