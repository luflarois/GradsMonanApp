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
import difflib
#
#My functions
from .files_nc import file_open
from .show_func import cmd_show, show_legend
from .plot_func import plot_wind, plot_var, plot_var_3d, clear_plots,save_fig
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
        grid_file = cmd_split[2] if len(cmd_split) > 2 else None
        setup_anterior = setup if isinstance(setup, dict) and setup.get("openFile") else None
        novo_dataset, novo_setup = file_open(cmd_split[1],setup_toml,grid_file,setup_anterior)
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
                map = cmd_user[9:]
                draw_map(setup,ax)
            if cmd_split[1] == "label":
                lbl = cmd_user[11:]
                draw_label(setup,cbar,lbl)
        elif cmd == "d3":
            if len(cmd_split) < 2:
                print("Uso: d3 <variavel>")
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
