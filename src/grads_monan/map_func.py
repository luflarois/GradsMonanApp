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
