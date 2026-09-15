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

    ## Carregar o shapefile com as fronteiras do país e estados usando geopandas
    #gdf = gpd.read_file(map)

    ## Plotar as fronteiras do país e estados
    #gdf.boundary.plot(ax=ax, color=map_color, linewidth=map_line)

    # Carregar o shapefile com as fronteiras do país e estados usando geopandas
    gdf = gpd.read_file(mappath+"/"+map)
     # Opção 1: Deslocar o shapefile para 0°–360° (recomendado para dados MPAS)
    gdf_shifted = gdf.copy()
    gdf_shifted.geometry = gdf_shifted.geometry.translate(xoff=180)  # Desloca +360° onde lon < 0
    gdf_shifted.boundary.plot(ax=ax, color=map_color, linewidth=map_line)
    # Plotar as fronteiras do país e estados
    gdf.boundary.plot(ax=plt.gca(), color=map_color, linewidth=map_line)
