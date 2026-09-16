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
import pickle
import hashlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
import matplotlib.tri as mtri
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - registra a projecao '3d'
from .utils import normalize_lon, mag, load_zgrid_centers
from .map_func import plot_map
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree

# Cache persistente da triangulacao de Delaunay entre sessoes (nao so dentro
# da mesma execucao do programa) - ver _obter_triangulacao mais abaixo.
_CONFIG_DIR = os.path.expanduser("~/.config/grads_monan")
_DELAUNAY_CACHE_PATH = os.path.join(_CONFIG_DIR, "delaunay_cache.pkl")
_LAST_GRID_INFO_PATH = os.path.join(_CONFIG_DIR, "last_grid.info")


def set_ion():
    plt.ion()

def _ativar_figura_2d(setup):
    """
    Garante que a figura 2D (usada por 'd'/'display') esteja ativa (current
    figure do matplotlib) antes de plotar - necessario porque 'd3' usa uma
    janela/figura separada, e o matplotlib so tem uma 'figura atual' por vez.
    """
    fig = setup.get("fig2d")
    if fig is None or not plt.fignum_exists(fig.number):
        fig = plt.gcf()  # reaproveita a figura corrente, ou cria uma se nao houver nenhuma
        setup["fig2d"] = fig
    else:
        plt.figure(fig.number)
    return fig

def _ativar_figura_3d(setup):
    """
    Garante que a figura 3D (usada por 'd3') esteja ativa e com um eixo 3D
    pronto, reaproveitando a mesma janela entre chamadas sucessivas de 'd3'
    (em vez de abrir uma janela nova a cada vez).
    """
    fig = setup.get("fig3d")
    if fig is None or not plt.fignum_exists(fig.number):
        fig = plt.figure()
        ax3d = fig.add_subplot(111, projection='3d')
        setup["fig3d"] = fig
        setup["ax3d"] = ax3d
    else:
        plt.figure(fig.number)
        ax3d = setup.get("ax3d")
        if ax3d is None or ax3d not in fig.axes:
            ax3d = fig.add_subplot(111, projection='3d')
            setup["ax3d"] = ax3d
    return fig, ax3d

def clear_plots(setup=None):
    fig_atual = plt.gcf()
    if setup is not None and setup.get("fig3d") is not None and fig_atual is setup["fig3d"]:
        # Figura 3D: limpa tudo (inclusive barras de cor antigas) e recria o eixo 3D
        fig_atual.clf()
        setup["ax3d"] = fig_atual.add_subplot(111, projection='3d')
        return
    # Com paginas/paineis ativos (set pages), limpa so o painel atual
    # (eixo corrente), para nao apagar os demais paineis da janela.
    if setup is not None and (setup.get("pages_rows", 1) > 1 or setup.get("pages_cols", 1) > 1):
        plt.gca().cla()
    else:
        plt.clf()

def set_window_title(titulo):
    """
    Define o titulo da janela do matplotlib (nao confundir com o titulo do
    grafico em si, comando 'set title'). Cria a figura se ainda nao existir.
    Envolto em try/except pois nem todo backend suporta essa chamada.
    """
    fig = plt.gcf()
    try:
        fig.canvas.manager.set_window_title(titulo)
    except Exception:
        pass

def _niveis_cor(setup):
    """
    Niveis de cor/contorno a usar em contourf/tricontourf/tricontour.
    Se 'set clevs' tiver sido usado (lista nao vazia em setup['clevs']),
    usa exatamente esses valores como fronteiras dos intervalos de cor
    (ex: clevs 0 100 200 ... cria faixas 0-100, 100-200, ...).
    Caso contrario, usa o padrao de 20 niveis automaticos.
    """
    clevs = setup.get("clevs")
    if clevs:
        return clevs
    return 20

def _tamanho_malha_ok(label, tamanho_dado, tamanho_malha):
    """
    Confere se o numero de pontos da variavel bate com o numero de pontos
    da malha aberta (latCell/lonCell). Se nao bater, avisa com uma mensagem
    clara (em vez do erro criptico do matplotlib/scipy la na frente) e
    retorna False.
    """
    if tamanho_dado != tamanho_malha:
        print("Erro: a variavel '{0}' tem {1} ponto(s), mas a malha aberta (latCell/lonCell) tem {2} ponto(s).".format(
            label, tamanho_dado, tamanho_malha))
        print("Isso indica que esta variavel nao esta na mesma malha do arquivo de grade usado no 'open'.")
        print("Verifique se e realmente o arquivo de grade correto para este arquivo de dados.")
        return False
    return True

def _assinatura_grade(setup):
    """
    Assinatura curta que identifica as caracteristicas da malha - NAO o
    nome do arquivo - usada para saber se a triangulacao de Delaunay salva
    em disco (cache persistente entre sessoes) ainda corresponde a malha
    atualmente aberta: numero de celulas + hash (md5) do conteudo real de
    latitude/longitude.
    """
    lons = np.asarray(setup["longitudes"])
    lats = np.asarray(setup["latitudes"])
    n_cells = len(lons)
    resumo = hashlib.md5(lons.tobytes() + lats.tobytes()).hexdigest()
    return n_cells, resumo

def _carregar_delaunay_disco(setup):
    """
    Tenta reaproveitar, de uma sessao anterior, a triangulacao de Delaunay
    salva em ~/.config/grads_monan/ (delaunay_cache.pkl + last_grid.info),
    se as caracteristicas da malha baterem com o arquivo atualmente aberto.
    Retorna None se nao houver cache valido (ou se a malha for diferente).
    """
    try:
        if not (os.path.exists(_DELAUNAY_CACHE_PATH) and os.path.exists(_LAST_GRID_INFO_PATH)):
            return None
        n_cells, resumo = _assinatura_grade(setup)
        info = {}
        with open(_LAST_GRID_INFO_PATH) as f:
            for linha in f:
                if "=" in linha:
                    chave, valor = linha.strip().split("=", 1)
                    info[chave] = valor
        if info.get("n_cells") != str(n_cells) or info.get("hash") != resumo:
            return None
        with open(_DELAUNAY_CACHE_PATH, "rb") as f:
            tri = pickle.load(f)
        print("Triangulacao (Delaunay) reaproveitada do cache em disco (mesma malha de uma sessao anterior).")
        return tri
    except Exception:
        return None

def _salvar_delaunay_disco(setup, tri):
    """
    Salva a triangulacao de Delaunay recem-calculada em
    ~/.config/grads_monan/, junto com um resumo legivel das caracteristicas
    da malha (last_grid.info), para reaproveitar em sessoes futuras sem
    precisar reconstruir do zero. Falha em silencio (so avisa) se nao
    conseguir escrever - isso nunca deve impedir a plotagem em si.
    """
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        n_cells, resumo = _assinatura_grade(setup)
        with open(_DELAUNAY_CACHE_PATH, "wb") as f:
            pickle.dump(tri, f, protocol=pickle.HIGHEST_PROTOCOL)
        with open(_LAST_GRID_INFO_PATH, "w") as f:
            f.write("n_cells={0}\n".format(n_cells))
            f.write("hash={0}\n".format(resumo))
            f.write("lon_min={0}\n".format(float(np.min(setup["longitudes"]))))
            f.write("lon_max={0}\n".format(float(np.max(setup["longitudes"]))))
            f.write("lat_min={0}\n".format(float(np.min(setup["latitudes"]))))
            f.write("lat_max={0}\n".format(float(np.max(setup["latitudes"]))))
            f.write("arquivo_origem={0}\n".format(setup.get("openFileName", "desconhecido")))
    except Exception as e:
        print("Aviso: nao foi possivel salvar o cache de triangulacao em disco ({0}).".format(e))

def _obter_triangulacao(setup):
    """
    Cria a triangulacao de Delaunay dos pontos da malha (longitude,
    latitude) do arquivo aberto e a guarda em cache no proprio 'setup', para
    ser reaproveitada por todas as interpolacoes (corte vertical, altura do
    zgrid, streamlines de vento) em vez de ser reconstruida a cada nivel/
    chamada - que e o principal gargalo de desempenho em arquivos grandes.
    A cache em memoria e refeita sozinha (o 'setup' e outro) sempre que um
    novo arquivo e aberto (ou 'reinit'). Alem disso, tambem tenta um cache
    EM DISCO (~/.config/grads_monan/) para reaproveitar entre sessoes
    diferentes do programa, quando a mesma malha for reaberta.
    """
    tri = setup.get("_delaunay_malha")
    if tri is None:
        tri = _carregar_delaunay_disco(setup)
        if tri is None:
            pontos = np.column_stack((setup["longitudes"], setup["latitudes"]))
            tri = Delaunay(pontos)
            _salvar_delaunay_disco(setup, tri)
        setup["_delaunay_malha"] = tri
    return tri

def _interpolar(setup, valores, pontos_destino):
    """
    Interpolacao linear sobre a malha nao estruturada, equivalente a
    griddata(pontos_origem, valores, pontos_destino, method='linear'), mas
    reaproveitando a triangulacao ja calculada (ver _obter_triangulacao) em
    vez de reconstrui-la a cada chamada.
    """
    tri = _obter_triangulacao(setup)
    interpolador = LinearNDInterpolator(tri, valores)
    return interpolador(pontos_destino)

def _grade_regular_interpolada(setup, ax, data):
    """
    Interpola 'data' (na malha nao estruturada) para uma grade regular,
    reaproveitando a triangulacao em cache (ver _obter_triangulacao) - usada
    por 'shaded'/'contour' para poder chamar o contourf/contour de GRADE
    REGULAR do matplotlib, em vez do tricontourf/tricontour, que nao
    escala bem para milhoes de pontos (mesmo com a triangulacao em cache,
    o algoritmo de extracao das faixas de cor sobre a malha inteira e caro
    e tem que ser refeito a cada troca de variavel).
    """
    lon_min = setup["lon_min"]
    lon_max = setup["lon_max"]
    lat_min = setup["lat_min"]
    lat_max = setup["lat_max"]

    largura, altura = 800, 400
    try:
        fig = ax.get_figure()
        largura = int(np.clip(fig.get_size_inches()[0]*fig.dpi, 200, 1600))
        altura = int(np.clip(fig.get_size_inches()[1]*fig.dpi, 150, 1600))
    except Exception:
        pass

    xs = np.linspace(lon_min, lon_max, largura)
    ys = np.linspace(lat_min, lat_max, altura)
    grade_x, grade_y = np.meshgrid(xs, ys)
    pontos_destino = np.column_stack((grade_x.ravel(), grade_y.ravel()))

    campo = _interpolar(setup, data, pontos_destino).reshape(altura, largura)
    return grade_x, grade_y, campo

def _aplicar_corte(data, cut):
    """
    Marca como NaN os valores fora do intervalo [minimo, maximo] definido
    por 'set cut <minimo> <maximo>'. 'cut' e None (sem corte) ou uma tupla
    (minimo, maximo).
    """
    if cut is None:
        return data
    cmin, cmax = cut
    data = np.asarray(data, dtype=float)
    return np.where((data < cmin) | (data > cmax), np.nan, data)

def _mask_corte(valores, cut):
    """
    Mascara booleana (True = dentro do intervalo de 'set cut', portanto
    visivel). 'cut' e None (sem corte, tudo visivel) ou uma tupla
    (minimo, maximo).
    """
    valores = np.asarray(valores)
    if cut is None:
        return np.ones(valores.shape, dtype=bool)
    cmin, cmax = cut
    return (valores >= cmin) & (valores <= cmax)


def plot_perfil(setup, var):


    lat_min = setup["lat_min"]
    lon_min = setup["lon_min"]
    lat_max = setup["lat_max"]
    lon_max = setup["lon_max"]
    time_sel = setup["time_sel"]
    lev  = setup["lev"] 
    levf = setup["levf"]
    label = setup["label"]
    cmap = setup["cmap"]
    lc = setup["lc"]
    lw = setup["lw"]
    z = setup["levels"]
    latitudes = setup["latitudes"]
    longitudes = setup["longitudes"]
    levels = setup["levels"]

    lon = np.array(longitudes)
    lat = np.array(latitudes)
    if len(var.shape) < 3:
        print("Nao e possivel plotar perfil vertical: a variavel e bidimensional (sem dimensao de nivel).")
        return -1
    data = var[time_sel, :,lev:levf]
    lon = normalize_lon(lon)

    if not _tamanho_malha_ok(label, data.shape[0], len(lon)):
        return -1


    # posLat = encontrar_posicao_mais_proxima(latitudes,lat_min)
    # posLon = encontrar_posicao_mais_proxima(longitudes,lon_min)


    if lat_min == lat_max and lon_min != lon_max:
        print("Not implemented!")
        return -1

    if lat_min != lat_max and lon_min == lon_max:
        print("Not implemented!")
        return -1
        
    if lat_min != lat_max or lon_min != lon_max:
         print("Isnt a point lat lon selected!")
         return -1  
    
    dist = np.sqrt((lat - lat_min)**2 + (lon - lon_min)**2)
    closest_index = np.argmin(dist)
    vertical_profile = data[closest_index,:]

    cut = setup.get("cut")
    vertical_profile = _aplicar_corte(vertical_profile, cut)

    eixo_pressao = setup.get("eixo_pressao", False)
    variables = setup.get("variables", {})
    zgrid_arr = None
    if not eixo_pressao:
        zgrid_arr = load_zgrid_centers(variables, len(lat), len(levels))

    if eixo_pressao:
        # Pressao (t_iso_levels): maior pressao embaixo, menor em cima
        y_vals = np.array(levels[lev:levf])
        ylabel = 'Pressao (hPa)'
    elif zgrid_arr is not None and np.mean(np.isfinite(zgrid_arr[closest_index, lev:levf])) >= 0.5:
        # Sem t_iso_levels, mas com zgrid: altura geometrica, menor embaixo, maior em cima
        y_vals = zgrid_arr[closest_index, lev:levf]
        ylabel = 'Altura (m)'
    else:
        if zgrid_arr is not None:
            print("Aviso: zgrid majoritariamente invalido para o ponto selecionado (shape={0}); usando indice de nivel no eixo Y.".format(zgrid_arr.shape))
        # Sem os dois: apenas o indice do nivel, menor embaixo, maior em cima
        y_vals = np.array(levels[lev:levf])
        ylabel = 'Levels'

    plt.scatter(vertical_profile,y_vals)
    plt.plot(vertical_profile,y_vals, color='blue', linestyle='-',label=label)
    plt.xlabel(label)
    plt.ylabel(ylabel)
    if eixo_pressao:
        plt.gca().invert_yaxis()
    plt.grid()
    return 1

def save_fig(fig_name, setup):
    plt.savefig(fig_name, dpi=setup["fig_dpi"], bbox_inches=setup["fig_inches"], transparent=setup["fig_transparency"])
    return 0

def plot_corte(setup, var, cbar=None):
    """
    Corte vertical (nivel x longitude, com latitude fixa; ou nivel x latitude,
    com longitude fixa), interpolando a malha nao estruturada (Voronoi) sobre
    uma linha reta na coordenada fixada.
    """
    lat_min = setup["lat_min"]
    lat_max = setup["lat_max"]
    lon_min = setup["lon_min"]
    lon_max = setup["lon_max"]
    time_sel = setup["time_sel"]
    lev  = setup["lev"]
    levf = setup["levf"]
    label = setup["label"]
    cmap = setup["cmap"]
    Title = setup["title"]
    latitudes = np.array(setup["latitudes"])
    longitudes = normalize_lon(np.array(setup["longitudes"]))
    levels = np.array(setup["levels"])

    if len(var.shape) < 3:
        print("Nao e possivel fazer corte vertical: a variavel e bidimensional (sem dimensao de nivel).")
        ax = plt.gca()
        return ax, cbar

    data = var[time_sel, :, lev:levf]  # (nCells, nLevs)
    n_lev = data.shape[1]

    if not _tamanho_malha_ok(label, data.shape[0], len(longitudes)):
        ax = plt.gca()
        return ax, cbar

    cut = setup.get("cut")
    data = _aplicar_corte(data, cut)

    lat_fixa = (lat_min == lat_max)

    if lat_fixa:
        eixo_x = np.linspace(lon_min, lon_max, 200)
        pontos_destino = np.column_stack((eixo_x, np.full_like(eixo_x, lat_min)))
        xlabel = 'Longitude'
    else:
        eixo_x = np.linspace(lat_min, lat_max, 200)
        pontos_destino = np.column_stack((np.full_like(eixo_x, lon_min), eixo_x))
        xlabel = 'Latitude'

    corte = np.full((n_lev, len(eixo_x)), np.nan)
    for k in range(n_lev):
        corte[k, :] = _interpolar(setup, data[:, k], pontos_destino)

    if np.all(np.isnan(corte)):
        print("Aviso: a interpolacao do corte nao gerou nenhum ponto valido (verifique lat/lon selecionadas).")
        ax = plt.gca()
        return ax, cbar

    ax = plt.gca()

    eixo_pressao = setup.get("eixo_pressao", False)
    variables = setup.get("variables", {})
    zgrid_arr = None
    if not eixo_pressao:
        zgrid_arr = load_zgrid_centers(variables, len(latitudes), len(levels))

    altura = None
    if not eixo_pressao and zgrid_arr is not None:
        # Sem t_iso_levels, mas com zgrid: interpola tambem a altura sobre a
        # mesma linha, nivel a nivel, para um corte que acompanha o terreno
        # (a altura de um mesmo nivel de modelo varia espacialmente).
        altura = np.full((n_lev, len(eixo_x)), np.nan)
        for k in range(n_lev):
            altura[k, :] = _interpolar(setup, zgrid_arr[:, lev+k], pontos_destino)
        frac_valida = np.mean(np.isfinite(altura))
        if frac_valida < 0.5:
            print("Aviso: interpolacao do zgrid majoritariamente invalida ({0:.0f}% dos pontos); usando indice de nivel no eixo Y.".format(frac_valida*100))
            altura = None

    if altura is not None:
        # contourf com X/Y em 2D (grade curvilinea) nao atualiza sozinho os
        # limites dos eixos (autoscale) - fixamos manualmente a partir dos
        # proprios dados, em vez de depender do autoscale do matplotlib.
        eixo_x_mesh = np.tile(eixo_x, (n_lev, 1))
        cs = ax.contourf(eixo_x_mesh, altura, corte, levels=_niveis_cor(setup), cmap=cmap)
        # Hachura nas celulas sem dado valido (tipicamente abaixo da
        # topografia local, na grade seguindo o terreno).
        mascara = np.isnan(corte).astype(int)
        if np.any(mascara):
            ax.contourf(eixo_x_mesh, altura, mascara, levels=[0.5, 1.5],
                        colors='none', hatches=['//'])
        ax.set_xlim(np.nanmin(eixo_x_mesh), np.nanmax(eixo_x_mesh))
        ax.set_ylim(np.nanmin(altura), np.nanmax(altura))
        plt.ylabel('Altura (m)')
    else:
        y = levels[lev:levf]
        cs = ax.contourf(eixo_x, y, corte, levels=_niveis_cor(setup), cmap=cmap)
        # Hachura nas celulas sem dado valido (mesmo motivo: geralmente
        # abaixo da topografia local).
        mascara = np.isnan(corte).astype(int)
        if np.any(mascara):
            ax.contourf(eixo_x, y, mascara, levels=[0.5, 1.5],
                        colors='none', hatches=['//'])
        ax.set_xlim(np.min(eixo_x), np.max(eixo_x))
        ax.set_ylim(np.min(y), np.max(y))
        if eixo_pressao:
            # Pressao (t_iso_levels): maior pressao embaixo, menor em cima
            plt.ylabel('Pressao (hPa)')
            ax.invert_yaxis()
        else:
            # Sem os dois: apenas o indice do nivel, menor embaixo, maior em cima
            plt.ylabel('Levels')

    cbar = plt.colorbar(cs, ax=ax, label=label)
    plt.xlabel(xlabel)
    if Title:
        plt.title(Title)

    return ax, cbar

def _obter_arvore_celulas(setup):
    """
    Cria (uma vez por arquivo aberto) e reaproveita uma arvore cKDTree dos
    centros das celulas (longitude, latitude), usada para rasterizar o
    'gxout voronoi' rapidamente.
    """
    arvore = setup.get("_arvore_celulas")
    if arvore is None:
        pontos = np.column_stack((setup["longitudes"], setup["latitudes"]))
        arvore = cKDTree(pontos)
        setup["_arvore_celulas"] = arvore
    return arvore

def plot_voronoi(setup, data):
    """
    Plota o diagrama de Voronoi da malha, rasterizado: para cada pixel da
    imagem final, usa o valor da celula mais proxima - que e, por
    definicao, a propria regiao de Voronoi correta para aquele ponto
    (nearest-neighbor = Voronoi). Muito mais rapido que desenhar o poligono
    exato de cada celula via PolyCollection (que nao escala bem para
    milhoes de celulas - mesmo ja vetorizado, a propria construcao do
    PolyCollection e o desenho subsequente dominam o tempo). So precisa de
    latCell/lonCell (sempre disponivel), nao da conectividade completa
    (verticesOnCell/latVertex/lonVertex).

    Limitacao conhecida: opera em coordenadas lon/lat planas (nao
    esfericas), entao pode haver uma costura sutil perto da linha
    internacional de data (+-180 graus) em malhas globais.
    """
    label = setup.get("label", "variavel")
    if not _tamanho_malha_ok(label, len(data), len(setup["longitudes"])):
        return None

    data = np.asarray(data, dtype=float)
    lon_min = setup["lon_min"]
    lon_max = setup["lon_max"]
    lat_min = setup["lat_min"]
    lat_max = setup["lat_max"]

    ax = plt.gca()

    # Resolucao da imagem acompanha o tamanho real da figura (em pixels),
    # com limites de sanidade - nao ha ganho visual em rasterizar mais fino
    # que a propria figura vai exibir.
    largura, altura = 1400, 700
    try:
        fig = ax.get_figure()
        largura = int(np.clip(fig.get_size_inches()[0]*fig.dpi, 200, 2400))
        altura = int(np.clip(fig.get_size_inches()[1]*fig.dpi, 150, 2400))
    except Exception:
        pass

    xs = np.linspace(lon_min, lon_max, largura)
    ys = np.linspace(lat_min, lat_max, altura)
    grade_x, grade_y = np.meshgrid(xs, ys)
    pontos_pixel = np.column_stack((grade_x.ravel(), grade_y.ravel()))

    arvore = _obter_arvore_celulas(setup)
    _, indices = arvore.query(pontos_pixel)

    imagem = np.ma.masked_invalid(data[indices].reshape(altura, largura))
    if np.all(imagem.mask):
        print("Aviso: nenhuma celula com valor dentro do corte (set cut) nesta selecao.")
        return None

    niveis = _niveis_cor(setup)
    norm = None
    if isinstance(niveis, (list, tuple, np.ndarray)) and len(niveis) > 1:
        norm = BoundaryNorm(niveis, ncolors=plt.get_cmap(setup["cmap"]).N)

    im = ax.imshow(imagem, extent=(lon_min, lon_max, lat_min, lat_max), origin='lower',
                    cmap=setup["cmap"], norm=norm, interpolation='nearest', aspect='auto')
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    return im

def plot_var_3d(setup, var):
    """
    Comando 'd3 <variavel>': plota em 3D (scatter), numa janela separada da
    usada pelo 'd' (2D), o subdominio definido por 'set lat <min> <max>',
    'set lon <min> <max>' e 'set lev <n1> <n2>' - ou seja, exige faixas
    reais (nao pontos unicos) nas tres dimensoes.

    O eixo Z segue a mesma hierarquia do corte/perfil 2D (secao 7 do
    manual): pressao (t_iso_levels), senao altura real (zgrid), senao
    indice do nivel do modelo.
    """
    lat_min = setup["lat_min"]
    lat_max = setup["lat_max"]
    lon_min = setup["lon_min"]
    lon_max = setup["lon_max"]
    lev = setup["lev"]
    levf = setup["levf"]
    time_sel = setup["time_sel"]
    label = setup["label"]
    cmap = setup["cmap"]
    Title = setup["title"]
    latitudes = np.array(setup["latitudes"])
    longitudes = np.array(setup["longitudes"])
    levels = np.array(setup["levels"])
    eixo_pressao = setup.get("eixo_pressao", False)
    variables = setup.get("variables", {})

    if lat_min == lat_max or lon_min == lon_max or lev == levf:
        print("Para plotar em 3D, selecione faixas (nao pontos unicos) nas tres dimensoes:")
        print("  set lat <min> <max>")
        print("  set lon <min> <max>")
        print("  set lev <n1> <n2>")
        return None

    if len(var.shape) < 3:
        print("Nao e possivel plotar em 3D: a variavel e bidimensional (sem dimensao de nivel).")
        return None

    data = var[time_sel, :, lev:levf]  # (nCells, nLevs)

    if not _tamanho_malha_ok(label, data.shape[0], len(longitudes)):
        return None

    mascara = (latitudes >= lat_min) & (latitudes <= lat_max) & (longitudes >= lon_min) & (longitudes <= lon_max)
    if not np.any(mascara):
        print("Nenhuma celula da malha cai dentro da faixa de latitude/longitude selecionada.")
        return None

    lats_sel = latitudes[mascara]
    lons_sel = longitudes[mascara]
    data_sel = data[mascara, :]  # (nCellsSel, nLevs)
    n_lev = data_sel.shape[1]
    n_cell_sel = data_sel.shape[0]

    zgrid_arr = None
    if not eixo_pressao:
        zgrid_arr = load_zgrid_centers(variables, len(latitudes), len(levels))

    if eixo_pressao:
        zlabel = 'Pressao (hPa)'
        zs_2d = np.tile(levels[lev:levf], (n_cell_sel, 1))  # (nCellsSel, nLevs)
    elif zgrid_arr is not None:
        zgrid_sel = zgrid_arr[mascara, :][:, lev:levf]
        if np.mean(np.isfinite(zgrid_sel)) < 0.5:
            print("Aviso: zgrid majoritariamente invalido nesta selecao; usando indice de nivel no eixo Z.")
            zlabel = 'Levels'
            zs_2d = np.tile(levels[lev:levf], (n_cell_sel, 1))
        else:
            zlabel = 'Altura (m)'
            zs_2d = zgrid_sel
    else:
        zlabel = 'Levels'
        zs_2d = np.tile(levels[lev:levf], (n_cell_sel, 1))

    cut = setup.get("cut")
    gxout = setup.get("gxout", "contour")

    # Reaproveita a mesma janela 3D entre chamadas sucessivas de 'd3' (nao
    # abre uma janela nova a cada vez), sem mexer na figura 2D usada pelo 'd'.
    fig3d, ax3d = _ativar_figura_3d(setup)

    niveis = _niveis_cor(setup)
    norm = None
    if isinstance(niveis, (list, tuple, np.ndarray)) and len(niveis) > 1:
        # 'set clevs' definido: discretiza as cores exatamente nessas faixas,
        # igual e feito no shaded/contour 2D.
        norm = BoundaryNorm(niveis, ncolors=plt.get_cmap(cmap).N)

    if gxout == "shaded":
        # Uma superficie triangulada (shaded) por nivel, empilhadas no eixo Z,
        # coloridas pelo valor da variavel (nao pela altura). Requer pelo
        # menos 3 celulas visiveis por nivel para triangular.
        triang_base = mtri.Triangulation(lons_sel, lats_sel)
        alguma_superficie = False
        mappable_ref = None
        for k in range(n_lev):
            valores_k = data_sel[:, k]
            visivel_k = (valores_k != 0) & _mask_corte(valores_k, cut)
            mask_tri = ~visivel_k[triang_base.triangles].all(axis=1)
            if mask_tri.all():
                continue  # nenhum triangulo visivel neste nivel
            triang_base.set_mask(mask_tri)
            surf = ax3d.plot_trisurf(triang_base, zs_2d[:, k], cmap=cmap, norm=norm, shade=False, alpha=0.7)
            cores_tri = valores_k[triang_base.triangles].mean(axis=1)
            surf.set_array(cores_tri)
            if norm is None:
                surf.autoscale()
            mappable_ref = surf
            alguma_superficie = True
        if not alguma_superficie:
            print("Aviso: nenhum valor visivel (tudo zero ou fora do corte) em nenhum nivel - nada para plotar em 3D.")
            return None
        fig3d.colorbar(mappable_ref, ax=ax3d, label=label)
    else:
        xs = np.repeat(lons_sel, n_lev)
        ys = np.repeat(lats_sel, n_lev)
        zs = zs_2d.flatten()
        valores = data_sel.flatten()

        # Pontos com valor exatamente zero ficam transparentes (nao aparecem
        # no scatter), em vez de saírem pintados com a cor da primeira faixa
        # do clevs. O mesmo vale para valores fora do intervalo de 'set cut'.
        visivel = (valores != 0) & _mask_corte(valores, cut)
        if not np.any(visivel):
            print("Aviso: nenhum valor selecionado ficou visivel (tudo zero ou fora do corte) - nada para plotar em 3D.")
            return None
        xs, ys, zs, valores = xs[visivel], ys[visivel], zs[visivel], valores[visivel]

        sc = ax3d.scatter(xs, ys, zs, c=valores, cmap=cmap, norm=norm)
        fig3d.colorbar(sc, ax=ax3d, label=label)

    ax3d.set_xlabel('Longitude')
    ax3d.set_ylabel('Latitude')
    ax3d.set_zlabel(zlabel)
    if eixo_pressao:
        ax3d.invert_zaxis()
    if Title:
        ax3d.set_title(Title)

    # Z "da superficie" (para 'draw map' desenhar o mapa junto ao solo/base
    # da caixa 3D, e nao no meio do ar).
    setup["z_superficie_3d"] = float(np.max(zs_2d)) if eixo_pressao else float(np.min(zs_2d))

    return fig3d, ax3d

# Função para ler e plotar a variável 
def plot_var(setup, var, cbar=None):

    _ativar_figura_2d(setup)

    time_sel = setup["time_sel"]
    lev = setup["lev"]
    levf = setup["levf"]
    cmap = setup["cmap"]
    Title = setup["title"]
    label = setup["label"]
    map = setup["map"]
    map_color = setup["map_color"]
    map_line = setup["map_line"]
    gxout = setup["gxout"]
    lon_min = setup["lon_min"]
    lon_max = setup["lon_max"]
    lat_min = setup["lat_min"]
    lat_max = setup["lat_max"]
    latitudes = setup["latitudes"]
    longitudes = setup["longitudes"]
    levels = setup["levels"]

    ponto_unico = (lat_min == lat_max) and (lon_min == lon_max)
    corte_vertical = (lat_min == lat_max) != (lon_min == lon_max)  # so uma das duas fixa

    if ponto_unico:
        # lat e lon fixas num unico ponto: perfil vertical
        plot_perfil(setup, var)
        ax = plt.gca()
        return ax, cbar

    if corte_vertical:
        if lev == levf:
            print("Para um corte vertical (latitude ou longitude fixa), selecione um intervalo de niveis:")
            print("  set lev <lev_ini> <lev_fim>")
            ax = plt.gca()
            return ax, cbar
        return plot_corte(setup, var, cbar)

    if len(var.shape) == 2:
        data = var[time_sel, :]
    else:
        data = var[time_sel, :,lev]

    if not _tamanho_malha_ok(label, len(data), len(longitudes)):
        ax = plt.gca()
        return ax, cbar

    cut = setup.get("cut")
    data = _aplicar_corte(data, cut)

    ax = plt.gca()
    plt.xlim(lon_min, lon_max)  # Limitar o eixo X (longitude)
    plt.ylim(lat_min, lat_max)  # Limitar o eixo Y (latitude)

    if gxout == "shaded":
        # Preenchido, interpolando para uma grade regular (reaproveitando a
        # triangulacao em cache) e usando o contourf de GRADE REGULAR do
        # matplotlib, bem mais rapido que o tricontourf para malhas grandes.
        if np.all(np.isnan(data)):
            print("Aviso: nenhum valor dentro do corte (set cut) nesta selecao.")
        else:
            grade_x, grade_y, campo = _grade_regular_interpolada(setup, ax, data)
            if np.all(np.isnan(campo)):
                print("Aviso: a interpolacao nao gerou nenhum ponto valido nesta selecao.")
            else:
                cs = ax.contourf(grade_x, grade_y, campo, levels=_niveis_cor(setup), cmap=cmap)
                cbar = plt.colorbar(cs,ax=ax,label=label)
    elif gxout == "contour":
        if np.all(np.isnan(data)):
            print("Aviso: nenhum valor dentro do corte (set cut) nesta selecao.")
        else:
            grade_x, grade_y, campo = _grade_regular_interpolada(setup, ax, data)
            if np.all(np.isnan(campo)):
                print("Aviso: a interpolacao nao gerou nenhum ponto valido nesta selecao.")
            else:
                cs = ax.contour(grade_x, grade_y, campo, levels=_niveis_cor(setup), cmap=cmap)
                plt.clabel(cs, inline=True, fontsize=10)
    elif gxout == "voronoi":
        # Plota o poligono real de cada celula (sem interpolar/triangular)
        coll = plot_voronoi(setup, data)
        if coll is not None:
            cbar = plt.colorbar(coll, ax=ax, label=label)

    plt.xlabel('Longitude')
    plt.ylabel('Latitude')

    return ax,cbar

def plot_vector_field(setup, var_u, var_v):
    """
    Plota vetores (quiver) das componentes var_u/var_v, sempre como vetor
    (independente do 'gxout'), sobre a figura/eixo atual (sem limpar) - assim
    sobrepoe a um shaded/contour ja plotado anteriormente.
    """
    time_sel = setup["time_sel"]
    lev = setup["lev"]
    lon_min = setup["lon_min"]
    lon_max = setup["lon_max"]
    lat_min = setup["lat_min"]
    lat_max = setup["lat_max"]
    latitudes = setup["latitudes"]
    longitudes = setup["longitudes"]

    if len(var_u.shape) == 2:
        u = var_u[time_sel, :]
        v = var_v[time_sel, :]
    else:
        u = var_u[time_sel, :, lev]
        v = var_v[time_sel, :, lev]

    if not _tamanho_malha_ok("u;v", len(u), len(longitudes)):
        ax = plt.gca()
        return ax

    ax = plt.gca()
    if lon_min != lon_max:
        ax.set_xlim(lon_min, lon_max)
    if lat_min != lat_max:
        ax.set_ylim(lat_min, lat_max)

    ax.quiver(longitudes, latitudes, u, v, scale=350, color='k')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')

    return ax

def plot_barbs(setup, var1, var2):
    """
    Plota barbelas de vento (wind barbs) a partir das componentes u/v,
    sobre a malha nao estruturada (sem interpolacao para grade regular).
    """
    time_sel = setup["time_sel"]
    lev = setup["lev"]
    lon_min = setup["lon_min"]
    lon_max = setup["lon_max"]
    lat_min = setup["lat_min"]
    lat_max = setup["lat_max"]
    latitudes = setup["latitudes"]
    longitudes = setup["longitudes"]

    if len(var1.shape) == 2:
        u = var1[time_sel, :]
        v = var2[time_sel, :]
    else:
        u = var1[time_sel, :, lev]
        v = var2[time_sel, :, lev]

    if not _tamanho_malha_ok("u;v", len(u), len(longitudes)):
        ax = plt.gca()
        return ax

    ax = plt.gca()
    if lon_min != lon_max:
        ax.set_xlim(lon_min, lon_max)
    if lat_min != lat_max:
        ax.set_ylim(lat_min, lat_max)

    ax.barbs(longitudes, latitudes, u, v, length=6)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')

    return ax

def plot_streams(setup, u, v):
    """
    Plota streamlines em grade não estruturada (MPAS).
    
    Args:
        setup: Dicionário com configurações (lon_min, lon_max, lat_min, lat_max, etc.)
        u: Componente zonal do vento (u10) em grade não estruturada.
        v: Componente meridional do vento (v10) em grade não estruturada.
    """
    time_sel = setup["time_sel"]
    lev = setup["lev"]
    lat = setup["latitudes"]
    lon = setup["longitudes"]
    
    u_data = u[time_sel, :]
    v_data = v[time_sel, :]

    if not _tamanho_malha_ok("u;v", len(u_data), len(lon)):
        return None
    
    # Cria uma grade regular para interpolação
    lon_grid = np.linspace(setup["lon_min"], setup["lon_max"], 100)
    lat_grid = np.linspace(setup["lat_min"], setup["lat_max"], 50)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
    
    # Interpola u e v para a grade regular (reaproveitando a triangulacao
    # da malha, em cache - ver _obter_triangulacao)
    pontos_destino = np.column_stack((lon_mesh.ravel(), lat_mesh.ravel()))
    u_interp = _interpolar(setup, u_data, pontos_destino).reshape(lon_mesh.shape)
    v_interp = _interpolar(setup, v_data, pontos_destino).reshape(lon_mesh.shape)
    
    # Configuração do plot
    ax = plt.gca()
    ax.set_xlim(setup["lon_min"], setup["lon_max"])
    ax.set_ylim(setup["lat_min"], setup["lat_max"])
    
    # Streamlines com cores baseadas na velocidade (opcional)
    speed = np.sqrt(u_interp**2 + v_interp**2)
    strm = ax.streamplot(
        lon_grid, lat_grid, u_interp, v_interp,
        color='black',              # Cor das linhas
        linewidth=0.1,              # Espessura
        density=2,                  # Densidade das linhas
        arrowsize=1,                # Tamanho das setas
        cmap='viridis',             # Opcional: cor por magnitude
    )
    
    # Barra de cores (se colorido por magnitude)
    #if setup.get("color_streams", False):
    #strm = ax.streamplot(
    #   lon_grid, lat_grid, u_interp, v_interp, color=speed,
    #   cmap=setup["cmap"], linewidth=1, density=2, arrowsize=1
    #    )
    #plt.colorbar(strm.lines, ax=ax, label='Velocidade (m/s)')

def plot_wind(setup, var1, var2, cbar):

    _ativar_figura_2d(setup)

    time_sel = setup["time_sel"]
    lev = setup["lev"]
    levf = setup["levf"]
    gxout = setup["gxout"]
    lon_min = setup["lon_min"]
    lon_max = setup["lon_max"]
    lat_min = setup["lat_min"]
    lat_max = setup["lat_max"]

    if lev!=levf:
        plot_perfil(setup, mag(var1,var2))
        ax = plt.gca()
        return ax, cbar

    ax = plt.gca()
    plt.xlim(lon_min, lon_max)  # Limitar o eixo X (longitude)
    plt.ylim(lat_min, lat_max)  # Limitar o eixo Y (latitude)

    # Plotagem de vento: 'stream' (linhas de corrente) e 'barb' (barbelas) sao
    # explicitos; qualquer outro valor de gxout (inclusive 'contour'/'shaded',
    # que valem para variaveis escalares - ver plot_var) cai no padrao 'vect'
    # (vetores).
    if gxout == "stream":
        plot_streams(setup, var1, var2)
    elif gxout == "barb":
        plot_barbs(setup, var1, var2)
    else:
        plot_vector_field(setup, var1, var2)

    plt.xlabel('Longitude')
    plt.ylabel('Latitude')

    return ax,cbar

def plot_marks(setup):
    for i in range(0,len(setup["xmark"])):
        x = setup["xmark"][i]
        y = setup["ymark"][i]
        plt.scatter(x, y, color=setup["colormark"][i], s=setup["sizemark"][i], label='Ponto de Interesse')