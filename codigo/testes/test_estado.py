from datetime import date

import estado as dados
import logica


def com_pessoas():
    e = dados.novo_estado()
    dados.criar_pessoa(e, "Dra. Helena", "Advogado(a)", True)
    dados.criar_pessoa(e, "Dr. Rui", "Advogado(a)")
    return e


def registro(e, **extra):
    base = {"tipo": "cliente", "tipo_outro": "", "nome": "Marcos Tavares", "detalhe": "",
            "origem": "", "observacao": "", "atendente_outro": "", "controla_saida": 1,
            "entrada_em": "2026-10-05 10:00", "atendentes_ids": [e["pessoas"][0]["id"]]}
    base.update(extra)
    return dados.inserir_visita(e, base)


def test_pessoa_duplicada_ignora_maiuscula_e_acento():
    e = dados.novo_estado()
    assert dados.criar_pessoa(e, "Cecília", "Secretária") is True
    assert dados.criar_pessoa(e, "cecilia", "Secretária") is False
    assert len(e["pessoas"]) == 1


def test_listar_pessoas_frequentes_primeiro_e_ativas():
    e = com_pessoas()
    assert [p["nome"] for p in dados.listar_pessoas(e)] == ["Dra. Helena", "Dr. Rui"]
    rui = e["pessoas"][1]["id"]
    dados.alternar_pessoa(e, rui, "ativo")
    assert [p["nome"] for p in dados.listar_pessoas(e, somente_ativas=True)] == ["Dra. Helena"]
    assert len(dados.listar_pessoas(e)) == 2          # desativada continua no cadastro


def test_alternar_campo_invalido():
    e = com_pessoas()
    try:
        dados.alternar_pessoa(e, 1, "cargo")
        assert False
    except ValueError:
        pass


def test_inserir_visita_guarda_nomes_e_ids_crescem():
    e = com_pessoas()
    a = registro(e, atendentes_ids=[e["pessoas"][0]["id"], e["pessoas"][1]["id"]])
    b = registro(e)
    assert (a, b) == (1, 2)
    assert e["visitas"][0]["atendentes_cadastrados"] == ["Dr. Rui", "Dra. Helena"]
    assert e["proximo_id_visita"] == 3


def test_saida_fecha_visita_aberta_uma_vez():
    e = com_pessoas()
    vid = registro(e)
    assert len(dados.visitas_abertas(e)) == 1
    assert dados.registrar_saida(e, vid, "2026-10-05 10:30") is True
    assert dados.registrar_saida(e, vid, "2026-10-05 11:00") is False
    assert dados.visitas_abertas(e) == []


def test_envelope_nao_fica_aberto_nem_aceita_saida():
    e = com_pessoas()
    vid = registro(e, tipo="envelope", controla_saida=0)
    assert dados.visitas_abertas(e) == []
    assert dados.registrar_saida(e, vid, "2026-10-05 10:30") is False


def test_marcar_sem_registro_tira_das_abertas():
    e = com_pessoas()
    vid = registro(e)
    assert dados.marcar_sem_registro_de_saida(e, vid) is True
    assert dados.visitas_abertas(e) == []
    assert dados.marcar_sem_registro_de_saida(e, vid) is False


def test_periodo_inclui_dia_final_inteiro_e_ordena_do_mais_recente():
    e = com_pessoas()
    registro(e, entrada_em="2026-10-03 23:59")
    registro(e, entrada_em="2026-10-03 08:00")
    registro(e, entrada_em="2026-10-04 00:00")
    achadas = dados.buscar_visitas(e, date(2026, 10, 3), date(2026, 10, 3))
    assert [v["entrada_em"] for v in achadas] == ["2026-10-03 23:59", "2026-10-03 08:00"]
    assert dados.buscar_visitas(e, date(2026, 10, 5), date(2026, 10, 6)) == []


def test_filtro_por_tipo():
    e = com_pessoas()
    registro(e)
    registro(e, tipo="envelope", controla_saida=0)
    achadas = dados.buscar_visitas(e, date(2026, 10, 5), date(2026, 10, 5), "envelope")
    assert [v["tipo"] for v in achadas] == ["envelope"]


def test_estrutura_valida_aceita_estado_real_e_recusa_lixo():
    e = com_pessoas()
    registro(e)
    assert dados.estrutura_valida(e) is True
    assert dados.estrutura_valida({}) is False
    assert dados.estrutura_valida([1, 2]) is False
    e["visitas"][0]["tipo"] = "visitante"
    assert dados.estrutura_valida(e) is False


def test_fluxo_completo_com_validacao():
    e = com_pessoas()
    ids = {p["id"] for p in dados.listar_pessoas(e, somente_ativas=True)}
    from datetime import datetime
    form = {"tipo": "cliente", "nome": "  Ana   Souza ", "atendentes": [str(e["pessoas"][0]["id"])]}
    reg, erros = logica.validar_registro(form, datetime(2026, 10, 5, 11, 30), ids)
    assert erros == {}
    dados.inserir_visita(e, reg)
    assert e["visitas"][0]["nome"] == "Ana Souza"
    assert e["visitas"][0]["entrada_em"] == "2026-10-05 11:30"
