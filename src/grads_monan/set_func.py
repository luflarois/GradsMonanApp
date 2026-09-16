#!/usr/bin/python
# -*- coding: utf-8 -*- Line 2
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# Created Date: 13Jun2025
# version ='0.1'
# ---------------------------------------------------------------------------
""" This script plot data from NetCDF data generated From MONAN MODEL"""  
# ---------------------------------------------------------------------------
import matplotlib.pyplot as plt
import numpy as np

def _print_level_info(setup, l):
    """
    Imprime a informacao do nivel selecionado em 'set lev N':
    pressao (t_iso_levels), senao altura geometrica (zgrid),
    senao apenas o indice do nivel.
    """
    variables = setup.get("variables", {})

    if "t_iso_levels" in variables:
        print("Nivel {0} selecionado: {1:.1f} hPa".format(l, setup["levels"][l]))
        return

    if "zgrid" in variables:
        zgrid_var = variables["zgrid"]
        try:
            dims = zgrid_var.dimensions
            shape = zgrid_var.shape
            n_levels = len(setup["levels"])
            eixo_nivel = None
            for i, tamanho in enumerate(shape):
                if tamanho == n_levels or tamanho == n_levels+1:
                    eixo_nivel = i
                    break
            if eixo_nivel is None:
                raise ValueError("dimensao de nivel nao identificada em zgrid")
            slicer = [slice(None)] * len(shape)
            slicer[eixo_nivel] = l
            valores = np.asarray(zgrid_var[tuple(slicer)])
            altura = float(np.nanmean(valores))
            print("Nivel {0} selecionado: zgrid = {1:.1f} m".format(l, altura))
        except Exception:
            print("Nivel {0} selecionado.".format(l))
        return

    print("Nivel {0} selecionado.".format(l))

def cmd_set(cmd_split, setup, cmd_user):
    """
    Ponto de entrada publico do comando 'set'. Avalia os termos numericos do
    comando (int()/float()) com seguranca: se algum termo nao for um numero
    valido, ou faltar algum argumento, avisa na tela e retorna ao prompt sem
    alterar a configuracao anterior, em vez de derrubar o programa.
    """
    try:
        return _cmd_set_dispatch(cmd_split, setup, cmd_user)
    except ValueError as e:
        print("Erro: termo(s) numerico(s) invalido(s) no comando '{0}' ({1})".format(cmd_user, e))
        return setup
    except IndexError:
        print("Erro: faltam argumento(s) no comando '{0}'".format(cmd_user))
        return setup

def _cmd_set_dispatch(cmd_split, setup, cmd_user):
    levels = setup["levels"]
    if cmd_split[1] == "lev":
        n_levels = len(levels)
        if len(cmd_split) == 3:
            l = int(cmd_split[2])
            if l<0 or l>=n_levels:
                print("Levels from 0 to {0}!".format(n_levels-1))
                return setup
            #print("Level set to {0} = {1}".format(l,levels[l]))
            setup["lev"] = l
            setup["levf"] = l
            _print_level_info(setup, l)
        elif len(cmd_split) == 4:
            l1 = int(cmd_split[2])
            l2 = int(cmd_split[3])
            if l1<0 or l1>=n_levels or l2<0 or l2>=n_levels:
                print("Levels from 0 to {0}!".format(n_levels-1))
                return setup
            setup["lev"] = l1
            setup["levf"] = l2
            #print("Level set from {0} to {1} : {2} to {3}".format(lev,levf,levels[lev],levels[levf]))               
        else:
            print("Uso: set lev <nivel>  ou  set lev <nivel_inicial> <nivel_final>")
        return setup
    elif cmd_split[1] == "cut":
        # Intervalo [minimo, maximo] plotado (2D e 3D); fora dele, fica
        # transparente. 'set cut' sem valores desliga o corte.
        if len(cmd_split) == 2:
            setup["cut"] = None
            print("Corte (set cut) desligado.")
        elif len(cmd_split) == 4:
            cmin = float(cmd_split[2])
            cmax = float(cmd_split[3])
            if cmin > cmax:
                print("Erro: o minimo ({0}) nao pode ser maior que o maximo ({1}).".format(cmin, cmax))
                return setup
            setup["cut"] = (cmin, cmax)
        else:
            print("Uso: set cut <minimo> <maximo>  ou  set cut (sem valores, desliga)")
        return setup
    elif cmd_split[1] == "pages":
        # Define a grade de paineis da janela: set pages <linhas> <colunas>
        if len(cmd_split) != 4:
            print("Uso: set pages <linhas> <colunas>")
            return setup
        m = int(cmd_split[2])
        n = int(cmd_split[3])
        if m < 1 or n < 1:
            print("Numero de linhas e colunas deve ser >= 1.")
            return setup
        setup["pages_rows"] = m
        setup["pages_cols"] = n
        setup["page_row"] = 1
        setup["page_col"] = 1
        plt.clf()
        plt.subplot(m, n, 1)
        return setup
    elif cmd_split[1] == "page":
        # Seleciona em qual painel plotar: set page <linha> <coluna>
        if len(cmd_split) != 4:
            print("Uso: set page <linha> <coluna>")
            return setup
        m = int(cmd_split[2])
        n = int(cmd_split[3])
        rows = setup.get("pages_rows", 1)
        cols = setup.get("pages_cols", 1)
        if m < 1 or m > rows or n < 1 or n > cols:
            print("Pagina fora do intervalo: linhas de 1 a {0}, colunas de 1 a {1}.".format(rows, cols))
            return setup
        setup["page_row"] = m
        setup["page_col"] = n
        indice = (m-1)*cols + n
        plt.subplot(rows, cols, indice)
        return setup
    elif cmd_split[1] == "label":
        setup["label"] = cmd_user[10:]
        return setup
    elif cmd_split[1] == "label_fs":
        setup["label_fontsize"] = int(cmd_split[2])
    elif cmd_split[1] == "label_fw":    
        setup["label_fontweight"] = cmd_split[2]
    elif cmd_split[1] == "mappat":
        setup["mappath"] = cmd_split[2]
        return setup
    elif cmd_split[1] == "mpdset":
        setup["map"] = cmd_split[2]
        return setup
    elif cmd_split[1] == "mpt":
        setup["map_color"] =  cmd_split[2]
        setup["map_line"] =  float(cmd_split[3])
        return setup
    elif cmd_split[1] == "lat":
        if len(cmd_split) == 3:
            setup["lat_min"] = float(cmd_split[2])
            setup["lat_max"] = float(cmd_split[2])
            return setup
        elif len(cmd_split) == 4:
            setup["lat_min"] = float(cmd_split[2])
            setup["lat_max"] = float(cmd_split[3])  
            return setup              
    elif cmd_split[1] == "lon":
        if len(cmd_split) == 3:
            setup["lon_min"] = float(cmd_split[2])
            setup["lon_max"] = float(cmd_split[2])
            return setup
        elif len(cmd_split) == 4:
            setup["lon_min"] = float(cmd_split[2])
            setup["lon_max"] = float(cmd_split[3]) 
            return setup
    elif cmd_split[1] == "cmap":
        setup["cmap"] = cmd_split[2]    
        return setup
    elif cmd_split[1] == "gxout":
        setup["gxout"]  =  cmd_split[2] 
        return setup
    elif cmd_split[1] == "plot_line":
        setup["lw"] = float(cmd_split[2])
        setup["lc"] = cmd_split[3]  
        return setup
    elif cmd_split[1] == "grid":
        if cmd_split[2] == "on":
            plt.grid()
            return setup
        else:
            plt.grid(False)
            return setup
    elif cmd_split[1] == "clevs":
        levs_in = cmd_user[9:]
        levs_in = levs_in.split()
        setup["clevs"] = [float(x) for x in levs_in]
        return setup
    elif cmd_split[1] == "time" or cmd_split[1] == "t":
        setup["time_sel"] = int(cmd_split[2])
        return setup
    elif cmd_split[1] == "mark":
        setup["xmark"].append(float(cmd_split[2]))
        setup["ymark"].append(float(cmd_split[3]))
        setup["colormark"].append(cmd_split[4])
        setup["sizemark"].append(float(cmd_split[5]))
        setup["legend"].append(cmd_split[6])
    elif cmd_split[1] == "fig_dpi":
        setup["fig_dpi"] = int(cmd_split[2])
    elif cmd_split[1] == "fig_inches":
        setup["fig_inches"] = cmd_split[2]
    elif cmd_split[1] == "fig_transparency":
        setup["fig_transparency"] = cmd_split[2]
    elif cmd_split[1] == "title_color":
        setup["title_color"] = cmd_split[2]
    elif cmd_split[1] == "title_fs":
        setup["title_fs"] = int(cmd_split[2])
    elif cmd_split[1] == "title_fw":
        setup["title_fw"] = cmd_split[2]        
    else:
        print("Command not recognized!")
    return setup
