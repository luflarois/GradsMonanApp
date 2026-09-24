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
import hashlib
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

def assinatura_malha(latitudes, longitudes):
    """
    Assinatura curta (numero de celulas + hash md5) que identifica as
    caracteristicas de uma malha (coordenadas lat/lon de cada celula).
    Usada para conferir se dois arquivos abertos na mesma sessao
    compartilham a mesma grade.
    """
    lons = np.asarray(longitudes)
    lats = np.asarray(latitudes)
    n_cells = len(lons)
    resumo = hashlib.md5(lons.tobytes() + lats.tobytes()).hexdigest()
    return n_cells, resumo

def mag(u,v):
    return np.sqrt(u**2+v**2)

def construir_poligonos_celulas(mesh):
    """
    Monta o poligono (lon, lat) de CADA celula da malha MPAS/MONAN, a
    partir da conectividade completa do arquivo de grade:
      - 'verticesOnCell' (nCells, maxEdges): indices (1-based, convencao
        Fortran do MPAS) dos vertices de cada celula, em ordem ao redor
        dela - o preenchimento apos o vertice valido nao e usado;
      - 'nEdgesOnCell' (nCells): numero real de vertices/arestas de cada
        celula (6 para um hexagono, 5 para um pentagono - defeitos
        topologicos inevitaveis de uma malha icosaedrica/Voronoi -, e
        possivelmente outros valores em celulas de borda de dominios
        regionais/de area limitada);
      - 'latVertex'/'lonVertex' (nVertices): coordenadas (radianos) de
        cada vertice.

    Retorna uma lista de arrays (n_vertices, 2) - uma por celula, na mesma
    ordem de latCell/lonCell -, ou None se alguma dessas variaveis nao
    existir no arquivo de grade (ex: saidas que so trazem latCell/lonCell,
    sem a malha completa - nesse caso o poligono exato nao pode ser
    reconstruido, e quem chamar deve usar a aproximacao rasterizada).

    Nao ha NENHUM tratamento especial para bordas de dominios regionais:
    a geometria de cada celula (inclusive o tamanho/formato irregular das
    celulas de borda, tipicamente diferentes das internas) vem direto dos
    vertices do proprio arquivo de grade, que ja e a malha de Voronoi real
    usada pelo modelo - reconstruir os poligonos a partir dela e suficiente
    para que a borda saia correta automaticamente.
    """
    obrigatorias = ("verticesOnCell", "nEdgesOnCell", "latVertex", "lonVertex")
    if not all(v in mesh.variables for v in obrigatorias):
        return None

    vertices_on_cell = np.asarray(mesh.variables["verticesOnCell"][:])  # (nCells, maxEdges), 1-based
    n_edges_on_cell = np.asarray(mesh.variables["nEdgesOnCell"][:])     # (nCells,)
    lat_vertex = np.degrees(sem_mascara(mesh.variables["latVertex"][:]))
    lon_vertex = normalize_lon(np.degrees(sem_mascara(mesh.variables["lonVertex"][:])))

    poligonos = []
    for i in range(vertices_on_cell.shape[0]):
        n = int(n_edges_on_cell[i])
        if n < 3:
            poligonos.append(np.empty((0, 2)))
            continue
        idx = vertices_on_cell[i, :n].astype(int) - 1  # 1-based -> 0-based
        lons = lon_vertex[idx]
        lats = lat_vertex[idx]
        # Celulas que cruzam a linha internacional de data (+-180 graus):
        # sem isso, o poligono "esticaria" pela largura inteira do mapa.
        if lons.size and (lons.max() - lons.min() > 180):
            lons = np.where(lons < 0, lons + 360, lons)
        poligonos.append(np.column_stack((lons, lats)))
    return poligonos

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