#!/usr/bin/python
# -*- coding: utf-8 -*- Line 2
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# Created Date: 13Jun2025
# version ='0.1'
# ---------------------------------------------------------------------------
""" This script plot data from NetCDF data generated From MONAN MODEL"""  
# ---------------------------------------------------------------------------
import os
import sys
import re
import glob
import difflib
#
#My functions
from .files_nc import file_open
from .show_func import cmd_show, show_legend
from .plot_func import plot_wind, plot_var, plot_var_3d, clear_plots,save_fig, plot_serie, plot_serie_mapa_3d
from .draw_func import draw_title, draw_mark, draw_map, draw_label
from .set_func import cmd_set
from .utils import mag, sem_mascara

_REF_VAR_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)(?:\.(\d+))?$')

def _arquivo_por_indice(setup, indice):
    """Retorna o registro (dict) do arquivo aberto com o indice informado,
    ou None se nenhum arquivo aberto tiver esse indice."""
    for info in setup.get("files", []) if isinstance(setup, dict) else []:
        if info["index"] == indice:
            return info
    return None

def _resolver_variavel(setup, token):
    """
    Resolve um token de variavel que pode trazer um sufixo opcional ".N"
    apontando para o N-esimo arquivo aberto na sessao (ex: "t2m.2"). Sem
    sufixo, assume o primeiro arquivo aberto (".1").

    Retorna (nome_base, indice, array). Se o arquivo nao estiver aberto ou
    a variavel nao existir nele, 'array' vem None e a mensagem de erro (com
    sugestoes, quando aplicavel) ja foi impressa.
    """
    m = _REF_VAR_RE.match(token)
    if not m:
        print("Referencia de variavel invalida: '{0}'".format(token))
        return token, None, None

    nome, indice_str = m.group(1), m.group(2)
    indice = int(indice_str) if indice_str else 1

    info = _arquivo_por_indice(setup, indice)
    if info is None:
        indices_abertos = [str(i["index"]) for i in setup.get("files", [])]
        if indices_abertos:
            print("Arquivo {0} nao esta aberto (arquivos abertos: {1}). Use 'show files' para conferir.".format(
                indice, ", ".join(indices_abertos)))
        else:
            print("Nenhum arquivo aberto.")
        return nome, indice, None

    variables = info["dataset"].variables
    if nome not in variables:
        print("Variavel '{0}' nao encontrada no arquivo {1} ({2})!".format(nome, indice, info["fileName"]))
        candidatos = difflib.get_close_matches(nome, list(variables.keys()), n=5, cutoff=0.4)
        if candidatos:
            sufixo = "" if indice == 1 else ".{0}".format(indice)
            print("Voce quis dizer: "+", ".join(c+sufixo for c in candidatos)+"?")
        else:
            print("Variaveis disponiveis no arquivo {0}: {1}".format(indice, ", ".join(sorted(variables.keys()))))
        return nome, indice, None

    return nome, indice, sem_mascara(variables[nome][:])

_TOKEN_REF_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.\d+)?')

def _avaliar_expressao(setup, expr):
    """
    Avalia uma expressao aritmetica (+ - * / ** e parenteses) sobre variaveis
    dos arquivos abertos, ex: "(t2m - 273.15)" ou "(t2m.1 - t2m.2)". Cada
    nome de variavel pode trazer o sufixo ".N" apontando para o N-esimo
    arquivo aberto (padrao: o primeiro). Retorna o array resultante, ou
    None se alguma variavel/arquivo referenciado nao foi encontrado (a
    mensagem de erro ja foi impressa por _resolver_variavel).
    """
    tokens = set(_TOKEN_REF_RE.findall(expr))
    namespace = {}
    expr_substituida = expr
    ok = True
    for tok in sorted(tokens, key=len, reverse=True):
        nome, indice, arr = _resolver_variavel(setup, tok)
        if arr is None:
            ok = False
            continue
        nome_seguro = "_v_{0}_{1}".format(indice if indice is not None else 0, nome)
        namespace[nome_seguro] = arr
        expr_substituida = re.sub(r'\b' + re.escape(tok) + r'\b', nome_seguro, expr_substituida)
    if not ok:
        return None
    return eval(expr_substituida, {"__builtins__": {}}, namespace)

def _resolver_variavel_serie(setup, info, token):
    """
    Como _resolver_variavel, mas para uso DENTRO do modo de serie temporal
    (loop por arquivo): um token SEM sufixo '.N' resolve para o arquivo do
    frame atual ('info'), em vez de sempre o arquivo 1 - assim "t2m-273.15"
    usa o t2m de cada arquivo da serie, nao so do primeiro. Um token COM
    sufixo '.N' continua fixo naquele arquivo especifico em todos os
    frames (uso avancado, ex: anomalia contra um arquivo de referencia).
    """
    m = _REF_VAR_RE.match(token)
    if not m:
        print("Referencia de variavel invalida: '{0}'".format(token))
        return token, None, None

    nome, indice_str = m.group(1), m.group(2)
    if indice_str:
        return _resolver_variavel(setup, token)

    variables = info["dataset"].variables
    if nome not in variables:
        print("Variavel '{0}' nao encontrada no arquivo {1} ({2})!".format(nome, info["index"], info["fileName"]))
        candidatos = difflib.get_close_matches(nome, list(variables.keys()), n=5, cutoff=0.4)
        if candidatos:
            print("Voce quis dizer: "+", ".join(candidatos)+"?")
        else:
            print("Variaveis disponiveis no arquivo {0}: {1}".format(info["index"], ", ".join(sorted(variables.keys()))))
        return nome, info["index"], None

    return nome, info["index"], sem_mascara(variables[nome][:])

def _avaliar_expressao_serie(setup, info, expr):
    """
    Como _avaliar_expressao, mas resolvendo os tokens sem sufixo pelo
    arquivo do frame atual ('info') - ver _resolver_variavel_serie.
    """
    tokens = set(_TOKEN_REF_RE.findall(expr))
    namespace = {}
    expr_substituida = expr
    ok = True
    for tok in sorted(tokens, key=len, reverse=True):
        nome, indice, arr = _resolver_variavel_serie(setup, info, tok)
        if arr is None:
            ok = False
            continue
        nome_seguro = "_v_{0}_{1}".format(indice if indice is not None else 0, nome)
        namespace[nome_seguro] = arr
        expr_substituida = re.sub(r'\b' + re.escape(tok) + r'\b', nome_seguro, expr_substituida)
    if not ok:
        return None
    return eval(expr_substituida, {"__builtins__": {}}, namespace)

def _dados_serie_temporal_expr(setup, expr):
    """
    Como _dados_serie_temporal, mas para uma EXPRESSAO aritmetica (ex:
    "t2m-273.15", "(t2m.1 - t2m.2)"), avaliada arquivo a arquivo dentro do
    intervalo de 'set t <arquivo_inicial> <arquivo_final>' - cada token sem
    sufixo '.N' usa o arquivo daquele frame (ver _avaliar_expressao_serie).
    """
    time_ini = setup.get("time_ini")
    time_fim = setup.get("time_fim")
    arquivos = setup.get("files") or []
    selecionados = sorted(
        (info for info in arquivos if time_ini <= info["index"] <= time_fim),
        key=lambda i: i["index"])

    if not selecionados:
        indices_abertos = [str(i["index"]) for i in arquivos]
        print("Nenhum arquivo aberto no intervalo {0}-{1} (arquivos abertos: {2}).".format(
            time_ini, time_fim, ", ".join(indices_abertos) if indices_abertos else "nenhum"))
        return None

    dados = []
    for info in selecionados:
        try:
            arr = _avaliar_expressao_serie(setup, info, expr)
        except Exception as e:
            print("Erro ao avaliar a expressao '{0}' no arquivo {1} ({2}): {3}".format(
                expr, info["index"], info["fileName"], e))
            return None
        if arr is None:
            return None
        dados.append({"index": info["index"], "DataDado": info.get("DataDado"), "array": arr})
    return dados

def _dados_serie_temporal(setup, nome_var):
    """
    Para o modo de serie temporal ('set t <arquivo_inicial> <arquivo_final>',
    com mais de um arquivo aberto): reune, para cada arquivo aberto dentro
    desse intervalo (em ordem de indice), o array bruto (ja sem mascara) da
    variavel 'nome_var'. Retorna None se o intervalo nao contiver nenhum
    arquivo aberto, ou se a variavel nao existir em algum dos arquivos
    selecionados (mensagens de erro, com sugestoes, ja impressas).
    """
    time_ini = setup.get("time_ini")
    time_fim = setup.get("time_fim")
    arquivos = setup.get("files") or []
    selecionados = sorted(
        (info for info in arquivos if time_ini <= info["index"] <= time_fim),
        key=lambda i: i["index"])

    if not selecionados:
        indices_abertos = [str(i["index"]) for i in arquivos]
        print("Nenhum arquivo aberto no intervalo {0}-{1} (arquivos abertos: {2}).".format(
            time_ini, time_fim, ", ".join(indices_abertos) if indices_abertos else "nenhum"))
        return None

    ok = True
    for info in selecionados:
        variables = info["dataset"].variables
        if nome_var not in variables:
            print("Variavel '{0}' nao encontrada no arquivo {1} ({2})!".format(nome_var, info["index"], info["fileName"]))
            candidatos = difflib.get_close_matches(nome_var, list(variables.keys()), n=5, cutoff=0.4)
            if candidatos:
                print("Voce quis dizer: "+", ".join(candidatos)+"?")
            ok = False
    if not ok:
        return None

    dados = []
    for info in selecionados:
        arr = sem_mascara(info["dataset"].variables[nome_var][:])
        dados.append({"index": info["index"], "DataDado": info.get("DataDado"), "array": arr})
    return dados

def _modo_serie_ativo(setup):
    """
    True quando o intervalo de arquivos ('set t <arquivo_inicial>
    <arquivo_final>') esta definido e ha mais de um arquivo aberto - a
    condicao para 'd'/'d3' entrarem no modo de serie temporal (grafico de
    linha, Hovmoller ou animacao, conforme a selecao de lat/lon/lev).
    """
    return (
        isinstance(setup, dict)
        and setup.get("time_ini") is not None
        and setup.get("time_fim") is not None
        and len(setup.get("files") or []) > 1
    )

def exec_cmd(cmd_user, cmd,cmd_split,setup, dataset, ax, cbar, setup_toml):

    if cmd == "!" or cmd == "exec":
        os.system(cmd_user[0:])
    elif cmd == "q" or cmd == "exit" or cmd == "quit":
        print("")
        print("Please, report bugs and other issues to luflarois@pm.me")
        print("----------------------------------------------------------------------------")
        print("bye o/ \n")        
        sys.exit()
    elif cmd == "run":
        setup, dataset, ax = run_file(cmd_split[1],setup, dataset, ax, cbar, setup_toml)
    elif cmd == "open":
        padrao = cmd_split[1]
        grid_file = cmd_split[2] if len(cmd_split) > 2 else None

        if any(c in padrao for c in "*?["):
            # Padrao com wildcard (ex: 'open SP_O_2022071400_20220714*.nc'):
            # abre, em sequencia (ordem alfabetica dos nomes de arquivo, que
            # normalmente corresponde a ordem cronologica), todos os
            # arquivos que baterem com o padrao - cada um vira o proximo
            # arquivo numerado (2, 3, ...), com a mesma validacao de grade
            # de um 'open' avulso.
            arquivos_padrao = sorted(glob.glob(padrao))
            if not arquivos_padrao:
                print("Nenhum arquivo encontrado para o padrao '{0}'.".format(padrao))
                return setup,dataset,ax,cbar
            print("Padrao '{0}': {1} arquivo(s) encontrado(s); abrindo em sequencia...".format(padrao, len(arquivos_padrao)))
            abertos = 0
            for caminho in arquivos_padrao:
                setup_anterior = setup if isinstance(setup, dict) and setup.get("openFile") else None
                novo_dataset, novo_setup = file_open(caminho, setup_toml, grid_file, setup_anterior)
                if novo_dataset is None:
                    print("Falha ao abrir '{0}'; mantendo os arquivos ja abertos ate aqui.".format(caminho))
                    continue
                dataset, setup = novo_dataset, novo_setup
                abertos += 1
            print("{0} de {1} arquivo(s) do padrao aberto(s) com sucesso.".format(abertos, len(arquivos_padrao)))
            return setup,dataset,ax,cbar

        setup_anterior = setup if isinstance(setup, dict) and setup.get("openFile") else None
        novo_dataset, novo_setup = file_open(padrao,setup_toml,grid_file,setup_anterior)
        if novo_dataset is None:
            print("Falha ao abrir o arquivo; configuracao anterior mantida.")
        else:
            dataset, setup = novo_dataset, novo_setup
    elif cmd == "reinit":
        # Fecha o(s) arquivo(s) aberto(s), apaga a configuracao do arquivo
        # anterior e volta ao estado inicial, pronto para um novo 'open'.
        arquivos_abertos = setup.get("files") if isinstance(setup, dict) else None
        if arquivos_abertos:
            for info in arquivos_abertos:
                ds = info.get("dataset")
                if hasattr(ds, "close"):
                    try:
                        ds.close()
                    except Exception:
                        pass
        elif hasattr(dataset, "close"):
            try:
                dataset.close()
            except Exception:
                pass
        dataset = {}
        setup = {"openFile": False}
        ax = 0
        cbar = 0
        clear_plots()
        print("Sessao reinicializada. Nenhum arquivo aberto.")
    else:
        if not setup["openFile"]:
            print("For use commands, please, open a file or run a script whith 'open' inside!")
            return setup,dataset,ax,cbar

        if cmd == "gxprint":
            save_fig(cmd_split[1],setup)
        if cmd == "show":
            cmd_show(setup, cmd_split)       
        elif cmd == "c":
            clear_plots(setup)
        elif cmd == "set":
            novo_setup = cmd_set(cmd_split, setup, cmd_user)
            if novo_setup is None:
                print("Comando 'set' invalido, configuracao anterior mantida.")
            else:
                setup = novo_setup
        elif cmd == "draw":
            if cmd_split[1] == "title":
                setup["title"] = cmd_user[11:]
                draw_title(setup)  
            if cmd_split[1] == "mark":
                draw_mark(cmd_split)
            if cmd_split[1] == "legend":
                show_legend()
            if cmd_split[1] == "map":
                if len(cmd_split) > 2 and cmd_split[2].lower() == "off":
                    # Desliga o mapa de fundo: para de ser redesenhado
                    # automaticamente nos plots seguintes (animados ou nao).
                    setup["draw_map_on"] = False
                    print("Mapa de fundo (draw map) desligado.")
                else:
                    # Liga o mapa e ja desenha no grafico atual; a partir
                    # daqui, fica marcado no 'setup' e e redesenhado
                    # automaticamente em todo plot seguinte (d/d3, animado
                    # ou nao) ate um 'draw map off' - ver plot_var/
                    # plot_var_3d/plot_wind em plot_func.py.
                    setup["draw_map_on"] = True
                    draw_map(setup,ax)
            if cmd_split[1] == "label":
                lbl = cmd_user[11:]
                # Guarda o texto/estilo no setup para que seja reaplicado
                # automaticamente toda vez que uma nova barra de cores for
                # criada (ex: a cada quadro da animacao de mapa, onde a
                # colorbar antiga e removida e recriada - ver
                # plot_serie_mapa/plot_var em plot_func.py), em vez de se
                # perder apos o primeiro quadro.
                setup["cbar_label"] = lbl
                draw_label(setup,cbar,lbl)
        elif cmd == "d3":
            if len(cmd_split) < 2:
                print("Uso: d3 <variavel>")
                return setup,dataset,ax, cbar

            if _modo_serie_ativo(setup):
                nome_var = re.sub(r'\.\d+$', '', cmd_split[1])
                if nome_var != cmd_split[1]:
                    print("Aviso: sufixo de arquivo ('.N') ignorado no modo de serie temporal - usa o intervalo de 'set t'.")
                dados = _dados_serie_temporal(setup, nome_var)
                if dados is None:
                    return setup,dataset,ax, cbar
                plot_serie_mapa_3d(setup, nome_var, dados)
                return setup,dataset,ax, cbar

            _, _, var = _resolver_variavel(setup, cmd_split[1])
            if var is None:
                return setup,dataset,ax, cbar
            plot_var_3d(setup, var)
        elif cmd == "display" or cmd == "d":
            if len(cmd_split) < 2:
                print("Uso: d <variavel>  |  d mag(<var_u>,<var_v>)  |  d <var_u>;<var_v>")
                return setup,dataset,ax, cbar

            resto = cmd_user.split(None, 1)[1]

            # Aceita tanto "d mag u v" (forma antiga) quanto "d mag(u,v)" (chamada de funcao)
            mag_call = re.search(r'mag\(\s*([^,()\s]+)\s*,\s*([^,()\s]+)\s*\)', cmd_user)
            # "d u;v" - sempre plota vetor, sobrepondo a figura atual
            vector_call = re.match(r'^\s*([^\s;()]+)\s*;\s*([^\s;()]+)\s*$', resto)

            # Modo de serie temporal entre arquivos: 'set t <arquivo_inicial>
            # <arquivo_final>' com mais de um arquivo aberto, e 'd <variavel>'
            # simples ou uma expressao aritmetica (sem mag/vetor). Linha/
            # Hovmoller num ponto/faixa fixo, ou animacao (mapa completo) -
            # ver plot_serie em plot_func.py.
            if _modo_serie_ativo(setup) and cmd_split[1] != "mag" and not mag_call and not vector_call:
                if re.search(r'[\+\-\*/()]', resto):
                    # Expressao aritmetica no modo serie, ex: "t2m-273.15":
                    # cada variavel sem sufixo '.N' usa o arquivo do proprio
                    # frame (tempo) em vez de sempre o arquivo 1 - ver
                    # _dados_serie_temporal_expr.
                    nome_var = resto
                    dados = _dados_serie_temporal_expr(setup, resto)
                else:
                    nome_var = re.sub(r'\.\d+$', '', cmd_split[1])
                    if nome_var != cmd_split[1]:
                        print("Aviso: sufixo de arquivo ('.N') ignorado no modo de serie temporal - usa o intervalo de 'set t'.")
                    dados = _dados_serie_temporal(setup, nome_var)
                if dados is None:
                    return setup,dataset,ax, cbar
                ax, cbar = plot_serie(setup, nome_var, dados, cbar)
                return setup,dataset,ax, cbar

            if cmd_split[1] == "mag" or mag_call:
                if mag_call:
                    var_u, var_v = mag_call.group(1), mag_call.group(2)
                else:
                    if len(cmd_split) < 4:
                        print("Uso: d mag(<var_u>,<var_v>)  ou  d mag <var_u> <var_v>")
                        return setup,dataset,ax, cbar
                    var_u, var_v = cmd_split[2], cmd_split[3]

                _, _, var1 = _resolver_variavel(setup, var_u)
                _, _, var2 = _resolver_variavel(setup, var_v)
                if var1 is None or var2 is None:
                    return setup,dataset,ax, cbar

                # mag(u,v) e tratada como uma variavel escalar comum (a magnitude):
                # obedece shaded/contour, corte vertical e perfil, igual a qualquer "d <var>".
                var = mag(var1, var2)
                ax, cbar = plot_var(setup, var, cbar)
            elif vector_call:
                var_u, var_v = vector_call.group(1), vector_call.group(2)

                _, _, var1 = _resolver_variavel(setup, var_u)
                _, _, var2 = _resolver_variavel(setup, var_v)
                if var1 is None or var2 is None:
                    return setup,dataset,ax, cbar

                # u;v e sempre plotagem de vento: stream, barb ou vetor (padrao),
                # conforme 'set gxout' - ver plot_wind.
                ax, cbar = plot_wind(setup, var1, var2, cbar)
            else:
                if re.search(r'[\+\-\*/()]', resto):
                    # Expressao aritmetica, ex: "(t2m - 273.15)" ou "(t2m.1 - t2m.2)"
                    try:
                        var = _avaliar_expressao(setup, resto)
                    except Exception as e:
                        print("Erro ao avaliar a expressao '{0}': {1}".format(resto, e))
                        return setup,dataset,ax, cbar
                    if var is None:
                        return setup,dataset,ax, cbar
                    ax, cbar  = plot_var(setup, var, cbar)
                else:
                    _, _, var = _resolver_variavel(setup, cmd_split[1])
                    if var is None:
                        return setup,dataset,ax, cbar
                    ax, cbar  = plot_var(setup, var, cbar)

    return setup,dataset,ax, cbar

def run_file(script_file,setup, dataset, ax, cbar, setup_toml):
    f = open(script_file,"r")
    lines = f.readlines()
    for line in lines:
        cmd_split = line.split()
        try:
            cmd = cmd_split[0]
        except:
            continue
        setup, dataset, ax, cbar  = exec_cmd(line, cmd, cmd_split,setup, dataset, ax, cbar, setup_toml)     
    return setup, dataset, ax
