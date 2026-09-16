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
from .utils import mag

def _var_not_found(dataset, varname):
    print("Variavel '{0}' nao encontrada no arquivo aberto!".format(varname))
    candidatos = difflib.get_close_matches(varname, list(dataset.variables.keys()), n=5, cutoff=0.4)
    if candidatos:
        print("Voce quis dizer: "+", ".join(candidatos)+"?")
    else:
        print("Variaveis disponiveis: "+", ".join(sorted(dataset.variables.keys())))

_TOKEN_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')

def _avaliar_expressao(dataset, expr):
    """
    Avalia uma expressao aritmetica (+ - * / ** e parenteses) sobre variaveis
    do arquivo aberto, ex: "(t2m - 273.15)". Retorna o array resultante.
    Lanca ValueError com a lista de nomes nao encontrados, se houver.
    """
    tokens = set(_TOKEN_RE.findall(expr))
    namespace = {}
    faltantes = []
    for tok in tokens:
        if tok in dataset.variables:
            namespace[tok] = dataset.variables[tok][:]
        else:
            faltantes.append(tok)
    if faltantes:
        raise ValueError(faltantes)
    return eval(expr, {"__builtins__": {}}, namespace)

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
        novo_dataset, novo_setup = file_open(cmd_split[1],setup_toml,grid_file)
        if novo_dataset is None:
            print("Falha ao abrir o arquivo; configuracao anterior mantida.")
        else:
            dataset, setup = novo_dataset, novo_setup
    elif cmd == "reinit":
        # Fecha o(s) arquivo(s) aberto(s), apaga a configuracao do arquivo
        # anterior e volta ao estado inicial, pronto para um novo 'open'.
        if hasattr(dataset, "close"):
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
            if cmd_split[1] not in dataset.variables:
                _var_not_found(dataset, cmd_split[1])
                return setup,dataset,ax, cbar
            var = dataset.variables[cmd_split[1]][:]
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

                faltantes = [v for v in (var_u, var_v) if v not in dataset.variables]
                if faltantes:
                    for v in faltantes:
                        _var_not_found(dataset, v)
                    return setup,dataset,ax, cbar

                var1 = dataset.variables[var_u][:]
                var2 = dataset.variables[var_v][:]
                # mag(u,v) e tratada como uma variavel escalar comum (a magnitude):
                # obedece shaded/contour, corte vertical e perfil, igual a qualquer "d <var>".
                var = mag(var1, var2)
                ax, cbar = plot_var(setup, var, cbar)
            elif vector_call:
                var_u, var_v = vector_call.group(1), vector_call.group(2)

                faltantes = [v for v in (var_u, var_v) if v not in dataset.variables]
                if faltantes:
                    for v in faltantes:
                        _var_not_found(dataset, v)
                    return setup,dataset,ax, cbar

                var1 = dataset.variables[var_u][:]
                var2 = dataset.variables[var_v][:]
                # u;v e sempre plotagem de vento: stream, barb ou vetor (padrao),
                # conforme 'set gxout' - ver plot_wind.
                ax, cbar = plot_wind(setup, var1, var2, cbar)
            else:
                if re.search(r'[\+\-\*/()]', resto):
                    # Expressao aritmetica, ex: "(t2m - 273.15)"
                    try:
                        var = _avaliar_expressao(dataset, resto)
                    except ValueError as e:
                        for v in e.args[0]:
                            _var_not_found(dataset, v)
                        return setup,dataset,ax, cbar
                    except Exception as e:
                        print("Erro ao avaliar a expressao '{0}': {1}".format(resto, e))
                        return setup,dataset,ax, cbar
                    ax, cbar  = plot_var(setup, var, cbar)
                else:
                    if cmd_split[1] not in dataset.variables:
                        _var_not_found(dataset, cmd_split[1])
                        return setup,dataset,ax, cbar
                    var = dataset.variables[cmd_split[1]][:]
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
