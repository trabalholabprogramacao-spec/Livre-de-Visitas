"""Dados 100% FICTÍCIOS para demonstração e prints.

Nenhum nome daqui é de pessoa ou empresa real. Abra o Livro_de_Visitas.html
com `?demo` no endereço (ou use o link "Ver demonstração" no rodapé).
"""
from datetime import datetime, time, timedelta

import estado as dados
import logica

PESSOAS = [
    ("Dra. Helena Duarte", "Advogado(a)", True),
    ("Dr. Rui Matos", "Advogado(a)", True),
    ("Dra. Paula Serrano", "Advogado(a)", True),
    ("Dr. Lucas Moreira", "Advogado(a)", False),
    ("Dra. Teresa Campos", "Advogado(a)", False),
    ("Dr. Henrique Salles", "Sócio(a)", False),
    ("Cecília", "Secretária", False),
    ("Rita", "Secretária", False),
    ("Joana", "Secretária", False),
    ("Silvia", "Demais", False),
    ("Mauro", "Demais", False),
]
CLIENTES = ["Marcos Tavares", "Ana Ribeiro", "Paulo Siqueira", "Larissa Monteiro",
            "Eduardo Furtado", "Camila Barreto", "Rogério Alencar", "Beatriz Cordeiro",
            "Tiago Valente", "Sônia Pacheco", "Henrique Dantas", "Marina Queiroz"]
PRESTADORES = [("Refrigeração Alfa", "Manutenção da máquina de café"),
               ("Águas Claras Manutenção", "Manutenção do purificador de água"),
               ("TecnoLimp", "Limpeza do ar-condicionado")]
ENVELOPES = [("Moto Ágil", "Banco Delta"), ("Entrega Rápida", "Cartório Central"),
             ("Moto Ágil", "Construtora Horizonte")]
ENTREGAS = [("Distribuidora Sul", "Papel toalha"), ("Café Brasa", "Café e copos"),
            ("Distribuidora Sul", "Chá e copos")]


class Sorteio:
    """Gerador de números pseudoaleatórios simples e determinístico: a
    demonstração sai igual em qualquer navegador."""

    def __init__(self, semente):
        self.valor = semente

    def proximo(self):
        self.valor = (self.valor * 1103515245 + 12345) % 2147483648
        return self.valor

    def entre(self, minimo, maximo):
        return minimo + (self.proximo() >> 8) % (maximo - minimo + 1)

    def escolher(self, lista):
        return lista[self.entre(0, len(lista) - 1)]

    def amostra(self, lista, quantidade):
        restantes = list(lista)
        escolhidos = []
        for _ in range(quantidade):
            escolhidos.append(restantes.pop(self.entre(0, len(restantes) - 1)))
        return escolhidos

    def tipo_do_dia(self):
        # 60% clientes, 8% prestadores, 14% envelopes, 10% entregas, 8% outros
        n = self.entre(1, 100)
        for limite, tipo in ((60, "cliente"), (68, "prestador"), (82, "envelope"),
                             (92, "entrega"), (100, "outro")):
            if n <= limite:
                return tipo


def _dados(tipo, nome, entrada, ids, **extra):
    base = {"tipo": tipo, "tipo_outro": "", "nome": nome, "detalhe": "",
            "origem": "", "observacao": "", "atendente_outro": "",
            "controla_saida": 1 if logica.CAMPOS_POR_TIPO[tipo]["controla_saida"] else 0,
            "entrada_em": f"{entrada.year:04d}-{entrada.month:02d}-{entrada.day:02d} "
                          f"{entrada.hour:02d}:{entrada.minute:02d}",
            "atendentes_ids": ids}
    base.update(extra)
    return base


def _saida(entrada_em, minutos):
    entrada = logica.converter_data_hora(entrada_em) + timedelta(minutes=minutos)
    return (f"{entrada.year:04d}-{entrada.month:02d}-{entrada.day:02d} "
            f"{entrada.hour:02d}:{entrada.minute:02d}")


def criar_estado_demo(agora):
    """Cria pessoas e cerca de 30 dias de visitas, incluindo duas visitas de
    ontem sem saída (para mostrar o alerta) e algumas de hoje."""
    estado = dados.novo_estado()
    for nome, cargo, frequente in PESSOAS:
        dados.criar_pessoa(estado, nome, cargo, frequente)
    pessoas = dados.listar_pessoas(estado)       # os frequentes vêm primeiro
    advogados = [p["id"] for p in pessoas if p["cargo"] in ("Advogado(a)", "Sócio(a)")]
    secretarias = [p["id"] for p in pessoas if p["cargo"] == "Secretária"]
    sorteio = Sorteio(42)
    hoje = agora.date()

    def uma_visita(dia):
        entrada = datetime.combine(dia, time(sorteio.entre(9, 17), sorteio.entre(0, 59)))
        tipo = sorteio.tipo_do_dia()
        if tipo == "cliente":
            quantos = 2 if sorteio.entre(1, 4) == 4 else 1
            return _dados(tipo, sorteio.escolher(CLIENTES), entrada,
                          sorteio.amostra(advogados, quantos))
        if tipo == "prestador":
            empresa, servico = sorteio.escolher(PRESTADORES)
            return _dados(tipo, empresa, entrada, [secretarias[0]], detalhe=servico)
        if tipo == "envelope":
            empresa, origem = sorteio.escolher(ENVELOPES)
            return _dados(tipo, empresa, entrada, [sorteio.escolher(advogados)], origem=origem)
        if tipo == "entrega":
            empresa, material = sorteio.escolher(ENTREGAS)
            return _dados(tipo, empresa, entrada, [secretarias[1]], detalhe=material)
        return _dados("outro", "Fernanda Lopes", entrada, [secretarias[2]],
                      tipo_outro="Candidato a vaga")

    for atras in range(30, 1, -1):
        dia = hoje - timedelta(days=atras)
        if dia.weekday() >= 5:
            continue
        for _ in range(sorteio.entre(3, 12)):
            visita = uma_visita(dia)
            visita_id = dados.inserir_visita(estado, visita)
            if visita["controla_saida"]:
                if sorteio.entre(1, 10) == 1:
                    dados.marcar_sem_registro_de_saida(estado, visita_id)
                else:
                    dados.registrar_saida(estado, visita_id,
                                          _saida(visita["entrada_em"], sorteio.entre(5, 70)))

    ontem = hoje - timedelta(days=1)
    for hora, nome, quem in ((10, "Ana Ribeiro", advogados[1]), (15, "Paulo Siqueira", advogados[0])):
        dados.inserir_visita(estado, _dados("cliente", nome,
                                            datetime.combine(ontem, time(hora, 20)), [quem]))

    inicio_do_dia = datetime.combine(hoje, time(0, 0))
    base = agora.replace(second=0, microsecond=0)
    for minutos, tipo, nome, quem, extra in (
        (200, "envelope", "Moto Ágil", [advogados[2]], {"origem": "Banco Delta"}),
        (95, "cliente", "Marcos Tavares", [advogados[0]], {}),
        (50, "cliente", "Larissa Monteiro", [advogados[1], advogados[2]], {}),
        (25, "prestador", "Águas Claras Manutenção", [secretarias[0]],
         {"detalhe": "Manutenção do purificador de água"}),
        (10, "entrega", "Café Brasa", [secretarias[1]], {"detalhe": "Café e copos"}),
    ):
        entrada = max(inicio_do_dia, base - timedelta(minutes=minutos))
        dados.inserir_visita(estado, _dados(tipo, nome, entrada, quem, **extra))
    return estado
