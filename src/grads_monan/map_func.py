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

def plot_map(setup,ax):

    map = setup["map"]
    map_color = setup["map_color"]
    map_line = setup["map_line"]
    mappath = setup["mappath"]

    # Carregar o shapefile com as fronteiras do país/continentes usando geopandas
    gdf = gpd.read_file(mappath+"/"+map)
    gdf.boundary.plot(ax=ax, color=map_color, linewidth=map_line)

def _desenhar_geometria_3d(ax3d, geom, z, color, linewidth):
    """
    Desenha uma geometria do shapefile (Polygon/MultiPolygon/LineString/
    MultiLineString) sobre um eixo 3D, projetada num Z constante.
    """
    if geom is None:
        return
    tipo = geom.geom_type
    if tipo == "Polygon":
        xs, ys = geom.exterior.xy
        ax3d.plot(xs, ys, zs=z, zdir='z', color=color, linewidth=linewidth)
        for interior in geom.interiors:
            xi, yi = interior.xy
            ax3d.plot(xi, yi, zs=z, zdir='z', color=color, linewidth=linewidth)
    elif tipo == "MultiPolygon":
        for parte in geom.geoms:
            _desenhar_geometria_3d(ax3d, parte, z, color, linewidth)
    elif tipo == "LineString":
        xs, ys = geom.xy
        ax3d.plot(xs, ys, zs=z, zdir='z', color=color, linewidth=linewidth)
    elif tipo == "MultiLineString":
        for parte in geom.geoms:
            _desenhar_geometria_3d(ax3d, parte, z, color, linewidth)

def plot_map_3d(setup, ax3d):
    """
    Versao de 'draw map' para a janela 3D (comando 'd3'): desenha o mesmo
    shapefile de fundo, mas como linhas projetadas num Z constante (a
    "superficie" da caixa 3D - maior pressao, ou menor altura/indice de
    nivel, conforme o que foi plotado por ultimo com 'd3'), em vez de usar
    o plot padrao do geopandas (que so funciona em eixos 2D).
    """
    map = setup["map"]
    map_color = setup["map_color"]
    map_line = setup["map_line"]
    mappath = setup["mappath"]
    z_superficie = setup.get("z_superficie_3d")
    if z_superficie is None:
        z_superficie = ax3d.get_zlim3d()[0]

    gdf = gpd.read_file(mappath+"/"+map)
    for geom in gdf.geometry:
        _desenhar_geometria_3d(ax3d, geom, z_superficie, map_color, map_line)
