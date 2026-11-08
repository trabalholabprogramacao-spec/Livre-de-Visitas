from datetime import date, datetime

import pytest

import logica

AGORA = datetime(2026, 10, 5, 11, 30)
HOJE = AGORA.date()


def form(**campos):
    base = {"tipo": "cliente", "nome": "Marcos Tavares",
            "atendentes": ["1"], "atendente_outro": ""}
    base.update(campos)
    return base


# ------------------------------------------------------------ validação

def test_cliente_valido_usa_agora_e_controla_saida():
    dados, erros = logica.validar_registro(form(), AGORA, {1, 2})
    assert erros == {}
    assert dados["entrada_em"] == "2026-10-05 11:30"
    assert dados["controla_saida"] == 1
    assert dados["atendentes_ids"] == [1]


def test_limpa_espacos_do_nome():
    dados, _ = logica.validar_registro(form(nome="  Marcos   Tavares "), AGORA, {1})
    assert dados["nome"] == "Marcos Tavares"


@pytest.mark.parametrize("tipo, faltando", [
    ("cliente", "nome"),
    ("prestador", "detalhe"),
    ("envelope", "origem"),
    ("entrega", "detalhe"),
    ("outro", "tipo_outro"),
])
def test_campo_obrigatorio_de_cada_tipo(tipo, faltando):
    preenchido = {c["nome"]: "x" for c in logica.CAMPOS_POR_TIPO[tipo]["campos"]}
    preenchido.pop(faltando)
    _, erros = logica.validar_registro(
        {"tipo": tipo, "atendentes": ["1"], **preenchido}, AGORA, {1})
    assert faltando in erros


def test_envelope_e_entrega_nao_controlam_saida():
    for tipo in ("envelope", "entrega"):
        campos = {c["nome"]: "x" for c in logica.CAMPOS_POR_TIPO[tipo]["campos"]}
        dados, erros = logica.validar_registro(
            {"tipo": tipo, "atendentes": ["1"], **campos}, AGORA, {1})
        assert erros == {}
        assert dados["controla_saida"] == 0


def test_tipo_outro_decide_se_controla_saida():
    base = {"tipo": "outro", "tipo_outro": "Correio", "nome": "Agência",
            "atendentes": ["1"]}
    sem, _ = logica.validar_registro(base, AGORA, {1})
    com, _ = logica.validar_registro({**base, "controla_saida": "1"}, AGORA, {1})
    assert sem["controla_saida"] == 0
    assert com["controla_saida"] == 1


def test_tipo_desconhecido_e_recusado():
    dados, erros = logica.validar_registro({"tipo": "visitante"}, AGORA, {1})
    assert dados is None and "tipo" in erros


def test_exige_ao_menos_um_atendente():
    _, erros = logica.validar_registro(form(atendentes=[]), AGORA, {1})
    assert erros["atendentes"] == "Informe: quem atende"


def test_atendente_digitado_basta():
    dados, erros = logica.validar_registro(
        form(atendentes=[], atendente_outro="Dra. Camila"), AGORA, {1})
    assert erros == {}
    assert dados["atendente_outro"] == "Dra. Camila"


def test_ignora_ids_invalidos_e_repetidos():
    dados, _ = logica.validar_registro(
        form(atendentes=["1", "1", "99", "abc"]), AGORA, {1, 2})
    assert dados["atendentes_ids"] == [1]


def test_chegada_em_horario_informado():
    dados, erros = logica.validar_registro(
        form(entrada="2026-10-05T09:15"), AGORA, {1})
    assert erros == {}
    assert dados["entrada_em"] == "2026-10-05 09:15"


def test_chegada_no_futuro_e_recusada():
    _, erros = logica.validar_registro(form(entrada="2026-10-05T18:00"), AGORA, {1})
    assert "entrada" in erros


def test_chegada_invalida_e_recusada():
    _, erros = logica.validar_registro(form(entrada="ontem"), AGORA, {1})
    assert erros["entrada"] == "Data e hora inválidas"


# ---------------------------------------------------------------- busca

def visita(**campos):
    base = {"nome": "", "detalhe": "", "origem": "", "tipo_txt": "Cliente",
            "observacao": "", "atendentes_txt": ""}
    base.update(campos)
    return base


def test_busca_ignora_acento_e_maiuscula():
    visitas = [visita(nome="José Álvares"), visita(nome="Ana Souza")]
    assert logica.filtrar_por_texto(visitas, "jose alvares") == [visitas[0]]


def test_busca_com_varias_palavras_em_qualquer_ordem():
    visitas = [visita(nome="Marcos Tavares"), visita(nome="Marcos Lima")]
    assert logica.filtrar_por_texto(visitas, "tavares marcos") == [visitas[0]]


def test_busca_olha_servico_origem_e_atendente():
    visitas = [visita(nome="Moto Ágil", origem="Banco Delta"),
               visita(nome="Alfa", detalhe="Purificador"),
               visita(nome="Pedro", atendentes_txt="Dra. Helena")]
    assert logica.filtrar_por_texto(visitas, "delta") == [visitas[0]]
    assert logica.filtrar_por_texto(visitas, "purificador") == [visitas[1]]
    assert logica.filtrar_por_texto(visitas, "helena") == [visitas[2]]


def test_busca_vazia_devolve_tudo():
    visitas = [visita(nome="A"), visita(nome="B")]
    assert logica.filtrar_por_texto(visitas, "   ") == visitas


# ------------------------------------------------- situação e pendências

def aberta(entrada_em, **extra):
    base = {"controla_saida": 1, "entrada_em": entrada_em,
            "saida_em": None, "status_saida": None}
    base.update(extra)
    return base


def test_situacoes():
    assert logica.situacao(aberta("2026-10-05 10:00", controla_saida=0), HOJE) == "unica"
    assert logica.situacao(aberta("2026-10-05 10:00", saida_em="2026-10-05 10:30"), HOJE) == "saiu"
    assert logica.situacao(aberta("2026-10-05 10:00"), HOJE) == "presente"
    assert logica.situacao(aberta("2026-10-02 10:00"), HOJE) == "pendente"
    assert logica.situacao(
        aberta("2026-10-02 10:00", status_saida="nao_registrada"), HOJE) == "nao_registrada"


def completa(entrada_em, **extra):
    base = {"id": 1, "tipo": "cliente", "tipo_outro": "", "nome": "X", "detalhe": "",
            "origem": "", "observacao": "", "atendente_outro": "",
            "atendentes_cadastrados": ["Dr. A"]}
    base.update(aberta(entrada_em, **extra))
    return base


def test_separa_presentes_de_pendentes_em_ordem():
    visitas = [completa("2026-10-05 11:00"), completa("2026-10-05 09:00"),
               completa("2026-10-02 15:00"), completa("2026-10-03 10:00"),
               completa("2026-10-05 08:00", saida_em="2026-10-05 08:20")]
    presentes, pendentes = logica.separar_abertas(visitas, HOJE)
    assert [v["hora_entrada"] for v in presentes] == ["09:00", "11:00"]
    assert [v["entrada_em"] for v in pendentes] == ["2026-10-02 15:00", "2026-10-03 10:00"]


def test_atendente_nao_cadastrado_vem_marcado():
    v = logica.preparar_visita(completa("2026-10-05 09:00", atendente_outro="Dra. Camila"), HOJE)
    assert v["atendentes"] == ["Dr. A", "Dra. Camila (não cadastrada)"]


# --------------------------------------------------- permanência e datas

def test_permanencia():
    assert logica.minutos_permanencia("2026-10-05 10:00", "2026-10-05 10:45") == 45
    assert logica.minutos_permanencia("2026-10-05 10:00", None) is None
    assert logica.formatar_permanencia(45) == "45 min"
    assert logica.formatar_permanencia(65) == "1h05"
    assert logica.formatar_permanencia(None) == ""


def test_montar_saida():
    assert logica.montar_saida("2026-10-02 10:00", "10:40") == ("2026-10-02 10:40", None)
    assert logica.montar_saida("2026-10-02 10:00", "09:00")[1] == "A saída não pode ser antes da chegada"
    assert logica.montar_saida("2026-10-02 10:00", "")[1] == "Informe a hora de saída"
    assert logica.montar_saida("2026-10-02 10:00", "25:99")[1] == "Hora inválida"


def test_periodo_padrao_e_limites():
    assert logica.validar_periodo("", "", HOJE) == (date(2026, 9, 5), HOJE, None)
    assert logica.validar_periodo("2026-09-15", "2026-09-15", HOJE) == (date(2026, 9, 15), date(2026, 9, 15), None)


def test_periodo_invalido_volta_ao_padrao_com_erro():
    de, ate, erro = logica.validar_periodo("2026-09-30", "2026-09-01", HOJE)
    assert (de, ate) == (date(2026, 9, 5), HOJE) and erro
    assert logica.validar_periodo("abc", "", HOJE)[2]


def test_rotulos_de_data():
    assert logica.rotulo_data(HOJE, HOJE) == "hoje"
    assert logica.rotulo_data(date(2026, 10, 4), HOJE) == "ontem"
    assert logica.rotulo_data(date(2026, 9, 15), HOJE) == "15/09/2026 (ter)"
    assert logica.data_por_extenso(HOJE) == "segunda-feira, 5 de outubro"


# ------------------------------------------------------------ estatísticas

def prep(entrada, **extra):
    return logica.preparar_visita(completa(entrada, **extra), HOJE)


def test_estatisticas_por_dia_empilhado_por_tipo():
    visitas = [prep("2026-10-05 10:00", tipo="cliente"),
               prep("2026-10-05 11:00", tipo="envelope", controla_saida=0),
               prep("2026-10-07 09:00", tipo="cliente")]
    r = logica.estatisticas(visitas, date(2026, 10, 5), date(2026, 10, 7))
    assert r["por_dia"]["rotulos"] == ["seg 05/10", "ter 06/10", "qua 07/10"]
    series = {s["tipo"]: s["valores"] for s in r["por_dia"]["series"]}
    assert series == {"cliente": [1, 0, 1], "envelope": [1, 0, 0]}
    assert r["total"] == 3


def test_estatisticas_agrupa_por_semana_em_periodo_longo():
    r = logica.estatisticas([prep("2026-10-05 10:00")], date(2026, 7, 1), date(2026, 10, 5))
    assert r["por_dia"]["semanal"] is True
    assert r["por_dia"]["rotulos"][0].startswith("Sem. ")
    assert sum(sum(s["valores"]) for s in r["por_dia"]["series"]) == 1


def test_mais_frequentes_junta_grafias_com_acento_e_maiuscula():
    visitas = [prep("2026-10-05 10:00", nome="José Álvares"),
               prep("2026-10-04 10:00", nome="jose alvares"),
               prep("2026-10-03 10:00", nome="Ana Souza")]
    r = logica.estatisticas(visitas, date(2026, 10, 1), date(2026, 10, 5))
    assert r["mais_frequentes"][0] == {"nome": "José Álvares", "visitas": 2}
    assert r["visitantes_distintos"] == 2


def test_envelope_nao_conta_como_visitante():
    visitas = [prep("2026-10-05 10:00", nome="Moto Ágil", tipo="envelope", controla_saida=0)]
    r = logica.estatisticas(visitas, date(2026, 10, 5), date(2026, 10, 5))
    assert r["visitantes_distintos"] == 0 and r["mais_frequentes"] == []


def test_maior_tempo_so_conta_visitas_com_saida():
    visitas = [prep("2026-10-05 10:00", nome="Ana", saida_em="2026-10-05 10:40"),
               prep("2026-10-05 14:00", nome="Ana", saida_em="2026-10-05 14:20"),
               prep("2026-10-04 10:00", nome="Bruno", saida_em="2026-10-04 10:30"),
               prep("2026-10-03 10:00", nome="Carlos")]
    r = logica.estatisticas(visitas, date(2026, 10, 1), date(2026, 10, 5))
    assert r["maior_tempo"][0] == {"nome": "Ana", "minutos": 60, "visitas": 2, "media": 30}
    assert [i["nome"] for i in r["maior_tempo"]] == ["Ana", "Bruno"]
    assert r["permanencia_media_min"] == 30       # (40 + 20 + 30) / 3
    assert r["visitas_com_saida"] == 3 and r["visitas_presenciais"] == 4


def test_horarios_preenche_faixa_comercial_com_zeros():
    r = logica.estatisticas([prep("2026-10-05 10:15"), prep("2026-10-05 10:50")],
                            date(2026, 10, 5), date(2026, 10, 5))
    assert r["horarios"]["rotulos"][0] == "08h" and r["horarios"]["rotulos"][-1] == "18h"
    assert r["horarios"]["valores"][2] == 2
    assert sum(r["horarios"]["valores"]) == 2


def test_taxa_de_saida_registrada():
    visitas = [prep("2026-10-05 08:00", saida_em="2026-10-05 08:30"),
               prep("2026-10-02 10:00"),                       # pendente
               prep("2026-10-05 10:00")]                       # ainda presente
    r = logica.estatisticas(visitas, date(2026, 10, 1), date(2026, 10, 5))
    assert r["saidas"] == {"registrada": 1, "sem_registro": 1, "no_escritorio": 1}
    assert r["taxa_saida_registrada"] == 50


def test_estatisticas_sem_visitas_nao_quebra():
    r = logica.estatisticas([], date(2026, 10, 1), date(2026, 10, 5))
    assert r["total"] == 0
    assert r["taxa_saida_registrada"] is None and r["permanencia_media_min"] is None
    assert r["mais_frequentes"] == [] and r["por_dia"]["series"] == []


# ------------------------------------------------------ exportação (Excel)

def test_normalizar_busca_remove_acentos():
    assert logica.normalizar_busca("José Álvares Çatalão") == "jose alvares catalao"


def completa_para_csv(entrada_em, **extra):
    return logica.preparar_visita(completa(entrada_em, **extra), HOJE)


def test_csv_tem_cabecalho_e_ordem_cronologica():
    a = completa_para_csv("2026-10-05 11:00", id=2, nome="Depois", saida_em="2026-10-05 11:40")
    b = completa_para_csv("2026-10-05 09:00", id=1, nome="Antes")
    linhas = logica.gerar_csv([a, b]).split("\r\n")
    assert linhas[0].startswith("Data;Entrada;Saída;Permanência")
    assert linhas[1].startswith("05/10/2026;09:00;;;No escritório;Cliente;Antes;")
    assert linhas[2].startswith("05/10/2026;11:00;11:40;40 min;Saiu;Cliente;Depois;")
    assert linhas[3] == ""


def test_csv_protege_contra_formula_e_escapa_separador():
    v = completa_para_csv("2026-10-05 09:00", nome="=SOMA(1;1)", observacao='disse "oi"; tchau')
    linha = logica.gerar_csv([v]).split("\r\n")[1]
    assert ";'=SOMA(1;1);" not in linha          # o ';' interno obriga aspas
    assert '"\'=SOMA(1;1)"' in linha
    assert '"disse ""oi""; tchau"' in linha
