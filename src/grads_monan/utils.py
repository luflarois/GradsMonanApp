#!/usr/bin/python
# -*- coding: utf-8 -*- Line 2
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# Created Date: 13Jun2025
# version ='0.1'
# ---------------------------------------------------------------------------
""" This script plot data from NetCDF data generated From MONAN MODEL"""  
# ---------------------------------------------------------------------------
import bisect
import numpy as np
import readline
import os

def encontrar_posicao_mais_proxima(lista, valor):
    """
    Versão mais eficiente para listas grandes usando bisect.
    Requer que a lista esteja ordenada.
    """
    # Ordena a lista se não estiver ordenada
    lista_ordenada = lista
    
    # Encontra o ponto de inserção
    pos = bisect.bisect_left(lista_ordenada, valor)
    return pos

    # Verifica os vizinhos mais próximos
    if pos == 0:
        return lista.index(lista_ordenada[0])
    if pos == len(lista_ordenada):
        return lista.index(lista_ordenada[-1])
    
    antes = lista_ordenada[pos-1]
    depois = lista_ordenada[pos]
    
    if abs(antes - valor) < abs(depois - valor):
        return lista.index(antes)
    else:
        return lista.index(depois)

def sem_mascara(arr):
    """
    Converte um array mascarado do netCDF4 (numpy.ma.MaskedArray) para um
    array numpy comum, substituindo qualquer valor mascarado por NaN (o
    codigo ja trata NaN como "sem dado" em toda parte - corte, topografia,
    etc). O netCDF4 retorna arrays mascarados sempre que a variavel tem
    metadado de _FillValue/missing_value, mesmo sem nenhum dado faltando de
    verdade - e bibliotecas como scipy (Delaunay, cKDTree) rejeitam
    array mascarado diretamente. Arrays normais passam por sem alteracao.
    """
    if np.ma.isMaskedArray(arr):
        return np.ma.filled(arr.astype(float), np.nan)
    return np.asarray(arr)

def normalize_lon(lon):
    return ((lon + 180) % 360) - 180

def mag(u,v):
    return np.sqrt(u**2+v**2)

def load_zgrid_centers(variables, n_cells, n_levels):
    """
    Retorna o zgrid no formato (nCells, n_levels), alinhado com os indices
    'lev'/'levf' usados para as demais variaveis. Se o zgrid tiver
    n_levels+1 valores (interfaces entre camadas), faz a media dos dois
    vizinhos para obter a altura no centro de cada camada.
    Retorna None se a variavel 'zgrid' nao existir, se nao for possivel
    identificar quais dimensoes correspondem a celula e a nivel, ou se
    houver dimensoes extras (ex: Time>1) que nao seja possivel reduzir
    com seguranca.
    """
    if "zgrid" not in variables:
        return None
    var = variables["zgrid"]
    try:
        shape = var.shape
        eixo_cell = None
        eixo_nivel = None
        for i, tamanho in enumerate(shape):
            if tamanho == n_cells and eixo_cell is None:
                eixo_cell = i
            elif tamanho in (n_levels, n_levels+1) and eixo_nivel is None and i != eixo_cell:
                eixo_nivel = i
        if eixo_cell is None or eixo_nivel is None or eixo_cell == eixo_nivel:
            return None

        arr = np.asarray(var[:])
        outros = [i for i in range(len(shape)) if i not in (eixo_cell, eixo_nivel)]
        arr = np.transpose(arr, [eixo_cell, eixo_nivel] + outros)

        if arr.ndim > 2:
            # Reduz eixos extras (ex: Time com tamanho 1) via squeeze; se
            # algum deles tiver tamanho > 1, desistimos (nao sabemos qual
            # fatia escolher) em vez de arriscar um resultado errado.
            if all(arr.shape[i] == 1 for i in range(2, arr.ndim)):
                arr = arr.reshape(arr.shape[0], arr.shape[1])
            else:
                return None

        if arr.shape[1] == n_levels+1:
            arr = (arr[:, :-1] + arr[:, 1:]) / 2.0

        if arr.shape != (n_cells, n_levels):
            return None

        return arr  # (nCells, n_levels)
    except Exception:
        return None

# def custom_input():
#     #return prompt('> ')
#     sys.stdout.write(">")
#     sys.stdout.flush()
#     return input() 

def custom_input():
    """Input personalizado que salva o histórico."""
    # O prompt precisa ser passado direto para input() (e nao escrito antes,
    # via stdout.write) para que o readline o redesenhe corretamente ao
    # navegar pelo historico com as setas para cima/baixo.
    user_input = input("> ")
    return user_input

def load_history(HISTORY_FILE):
    """Carrega o histórico de comandos do arquivo, se existir."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            for line in f:
                # Remove espaços em branco e adiciona ao histórico
                cmd = line.strip()
                if cmd:
                    readline.add_history(cmd)

def save_command_to_history(cmd,HISTORY_FILE):
    """Salva um novo comando no histórico e no arquivo."""
    if cmd.strip():  # Ignora linhas vazias
        readline.add_history(cmd)
        with open(HISTORY_FILE, "a") as f:
            f.write(cmd + "\n")