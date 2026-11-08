"""Gera o arquivo único ../Livro_de_Visitas.html.

Junta, dentro de um só .html: o CSS, o Brython (Python no navegador), os
módulos Python do sistema (logica, estado, dados_demo, interface), só as
partes da biblioteca padrão do Brython que o sistema usa, o Chart.js e o
desenho dos gráficos. Resultado: um arquivo que abre com dois cliques, sem
internet, sem instalar nada.

    python montar.py

Depois de mudar qualquer arquivo .py, .css ou .js desta pasta, rode de novo.
"""
import ast
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI.parent / "Livro_de_Visitas.html"
MODULOS = ["logica", "estado", "dados_demo", "interface"]
EMBUTIDOS = set()   # o que não existir na biblioteca (ex.: javascript) já é do próprio Brython


def ler(caminho):
    return (AQUI / caminho).read_text(encoding="utf-8")


def seguro_para_script(texto):
    """Impede que o texto feche a tag <script> ou abra um comentário HTML."""
    return texto.replace("</script", "<\\/script").replace("</SCRIPT", "<\\/SCRIPT") \
                .replace("<!--", "<\\u0021--")


def ler_biblioteca_padrao():
    texto = ler("vendor/brython_stdlib.js")
    inicio = texto.index("var scripts = ") + len("var scripts = ")
    fim = texto.rindex("__BRYTHON__.update_VFS(scripts)")
    return json.loads(texto[inicio:fim].rstrip().rstrip(";"))


def importados_por(fonte):
    achados = set()
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Import):
            achados.update(a.name for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            achados.add(no.module)
    return achados


def importados_da_entrada(entrada):
    """Lista de módulos que uma entrada da biblioteca importa (pode não ter)."""
    return (entrada[2] if len(entrada) > 2 else None) or []


def fechamento(nomes, biblioteca):
    """Todos os módulos da biblioteca padrão necessários, direta ou indiretamente."""
    precisa, fila = set(), list(nomes)
    while fila:
        nome = fila.pop()
        if nome in precisa or nome in EMBUTIDOS:
            continue
        pai = nome.split(".")[0]
        for candidato in {nome, pai}:
            if candidato in biblioteca and candidato not in precisa:
                precisa.add(candidato)
                fila.extend(importados_da_entrada(biblioteca[candidato]))
        # pacotes: levar também os submódulos citados
        for chave in biblioteca:
            if chave.startswith(pai + ".") and chave not in precisa:
                precisa.add(chave)
                fila.extend(importados_da_entrada(biblioteca[chave]))
    return precisa


def main():
    biblioteca = ler_biblioteca_padrao()
    proprios = {nome: ler(f"{nome}.py") for nome in MODULOS}

    usados = set()
    for fonte in proprios.values():
        usados |= {m for m in importados_por(fonte) if m.split(".")[0] not in proprios}
    necessarios = fechamento(usados, biblioteca)

    vfs = {"$timestamp": biblioteca.get("$timestamp", 0)}
    for nome in sorted(necessarios):
        vfs[nome] = biblioteca[nome]
    for nome, fonte in proprios.items():
        locais = sorted(m for m in importados_por(fonte) if m in proprios)
        externos = sorted(m for m in importados_por(fonte) if m not in proprios)
        vfs[nome] = [".py", fonte, externos + locais]

    modulos_js = ("(function () {\n__BRYTHON__.use_VFS = true;\nvar scripts = "
                  + json.dumps(vfs, ensure_ascii=False) + ";\n__BRYTHON__.update_VFS(scripts);\n})();")

    html = ler("modelo.html")
    pecas = {
        "@@CSS@@": ler("estilo.css"),
        "@@BRYTHON@@": seguro_para_script(ler("vendor/brython.min.js")),
        "@@MODULOS@@": seguro_para_script(modulos_js),
        "@@CHARTJS@@": seguro_para_script(ler("vendor/chart.umd.min.js")),
        "@@GRAFICOS@@": seguro_para_script(ler("graficos.js")),
    }
    for marca, conteudo in pecas.items():
        # str.replace com função evita que '\' no conteúdo seja interpretado
        html = html.replace(marca, conteudo)
    SAIDA.write_text(html, encoding="utf-8")

    print(f"Gerado: {SAIDA}  ({SAIDA.stat().st_size / 1024 / 1024:.1f} MB)")
    print("Biblioteca padrão incluída:", ", ".join(sorted(necessarios)))


if __name__ == "__main__":
    sys.exit(main())
