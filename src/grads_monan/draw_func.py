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
from .map_func import plot_map

def draw_title(setup):
    plt.title(setup["title"], fontsize=setup["title_fs"], fontweight=setup["title_fw"], color=setup["title_color"])

def draw_map(setup,ax):
    plot_map(setup,ax)

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
    cbar.set_label(lbl, fontsize=setup["label_fontsize"], fontweight=setup["label_fontweight"])


