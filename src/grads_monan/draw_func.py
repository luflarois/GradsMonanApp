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
import geopandas as gpd
from .map_func import plot_map, plot_map_3d
from .plot_func import _ativar_figura_2d

def draw_title(setup):
    plt.title(setup["title"], fontsize=setup["title_fs"], fontweight=setup["title_fw"], color=setup["title_color"])

def draw_map(setup,ax=None):
    # Se a janela ativa no momento for a 3D (usada pelo 'd3'), desenha o
    # mapa projetado na "superficie" da caixa 3D; senao, o comportamento
    # 2D de sempre.
    ax_ativo = plt.gca()
    if getattr(ax_ativo, "name", None) == "3d":
        plot_map_3d(setup, ax_ativo)
    else:
        # Garante uma figura/eixo 2D de verdade (a mesma janela usada por
        # 'd'/'display' - ver _ativar_figura_2d), em vez de confiar no
        # 'ax' recebido do chamador: se 'draw map' for usado antes de
        # qualquer 'd' (ax ainda vale 0, o inteiro inicial de cli.py), usar
        # esse valor direto quebrava o geopandas ("'int' object has no
        # attribute 'set_aspect'").
        _ativar_figura_2d(setup)
        plot_map(setup, plt.gca())

# Simbolos de marca - convencao classica do GrADS (numeros 1 a 11):
# 1=+  2=circulo  3=circulo cheio  4=quadrado  5=quadrado cheio  6=x
# 7=losango  8=triangulo  9=triangulo cheio
# 10=circulo meio-preenchido (esquerda/direita)  11=circulo meio-preenchido (cima/baixo)
_SIMBOLOS_MARK = {
    1:  dict(marker='+', fillstyle='full'),
    2:  dict(marker='o', fillstyle='none'),
    3:  dict(marker='o', fillstyle='full'),
    4:  dict(marker='s', fillstyle='none'),
    5:  dict(marker='s', fillstyle='full'),
    6:  dict(marker='x', fillstyle='full'),
    7:  dict(marker='D', fillstyle='none'),
    8:  dict(marker='^', fillstyle='none'),
    9:  dict(marker='^', fillstyle='full'),
    10: dict(marker='o', fillstyle='left'),
    11: dict(marker='o', fillstyle='top'),
}

def draw_mark(cmd_split):
    """
    Comando 'draw mark <lat> <lon> <simbolo>': desenha o simbolo de marca
    (1 a 11, conforme a tabela classica do GrADS) na coordenada geografica
    informada, sobre o grafico atual.
    """
    if len(cmd_split) < 5:
        print("Uso: draw mark <lat> <lon> <simbolo 1-11>")
        return

    try:
        lat = float(cmd_split[2])
        lon = float(cmd_split[3])
        simbolo = int(cmd_split[4])
    except ValueError:
        print("Erro: lat e lon devem ser numeros, e o simbolo um inteiro de 1 a 11.")
        return

    if simbolo not in _SIMBOLOS_MARK:
        print("Simbolo invalido: {0}. Use um numero de 1 a 11.".format(simbolo))
        return

    estilo = _SIMBOLOS_MARK[simbolo]
    ax = plt.gca()
    ax.plot(lon, lat, marker=estilo["marker"], fillstyle=estilo["fillstyle"],
            color='black', markersize=10, linestyle='none')

# def draw_xlabel(setup,ax):
#     ax.set_xlabel()  

# def draw_ylabel(setup,ax):
#     ax.set_ylabel()

def draw_label(setup,cbar,lbl):
    """
    Comando 'draw label <texto>': define o rotulo da barra de cores
    (colorbar) do grafico atual. O texto (com o tamanho/peso de fonte de
    'set label_fs'/'set label_fw') fica guardado em setup['cbar_label']
    (ver exec_func.py) e e reaplicado automaticamente TODA vez que uma
    barra de cores for (re)criada - inclusive quadro a quadro numa
    animacao de mapa (plot_serie_mapa), onde a colorbar e recriada a cada
    frame - ver _aplicar_rotulo_cbar em plot_func.py.
    """
    # Se ja existe uma barra de cores de verdade no grafico atual, escreve
    # o rotulo nela imediatamente (e forca o redesenho, para o texto
    # aparecer na hora, sem precisar de um novo 'd'). Se ainda nao existe
    # (ex: 'draw label' chamado antes de qualquer 'd'/'display' - 'cbar'
    # ainda vale o inteiro inicial 0 de cli.py), nao ha o que escrever
    # agora; o texto ja guardado entra em vigor sozinho assim que a
    # primeira colorbar for criada.
    if not hasattr(cbar, "set_label"):
        print("Rotulo da barra de cores guardado: sera aplicado automaticamente no proximo grafico com barra de cores.")
        return
    cbar.set_label(lbl, fontsize=setup["label_fontsize"], fontweight=setup["label_fontweight"])
    try:
        cbar.ax.figure.canvas.draw_idle()
    except Exception:
        pass


