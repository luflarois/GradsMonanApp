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
import matplotlib.pyplot as plt

def show_legend():
    plt.legend()

def _mostrar_info_arquivo(setup):
    """
    Comando 'show info': mostra informacoes do arquivo NetCDF aberto (e da
    grade, se houver), suas dimensoes, e a lista de variaveis com seus
    niveis, descricao e unidade.
    """
    print("Arquivo NetCDF: {0}".format(setup.get("openFileName", "?")))
    grid_file = setup.get("gridFileName")
    if grid_file:
        print("Arquivo de grade: {0}".format(grid_file))

    variables = setup["variables"]

    print("Dimensoes:")
    print("  Numero de celulas (nCells): {0}".format(len(setup.get("latitudes", []))))
    print("  Numero de niveis verticais: {0}".format(len(setup.get("levels", []))))
    n_tempos = len(setup.get("time", []))
    if n_tempos:
        print("  Numero de tempos: {0}".format(n_tempos))

    print("Numero de variaveis: {0}".format(len(variables)))
    for vname in sorted(variables.keys()):
        var = variables[vname]
        attrs = var.ncattrs()

        n_niveis_var = 1
        for i, d in enumerate(var.dimensions):
            if "lev" in d.lower() or "vert" in d.lower():
                n_niveis_var = var.shape[i]
                break

        descricao = "Sem descricao"
        for chave in ("long_name", "description", "standard_name"):
            if chave in attrs:
                descricao = getattr(var, chave)
                break

        unidade = getattr(var, "units", None) if "units" in attrs else None
        texto = "{0} ({1})".format(descricao, unidade) if unidade else descricao

        print("  {0} - niveis: {1} - {2}".format(vname, n_niveis_var, texto))

def cmd_show(setup, cmd_split):
    latitudes = setup["latitudes"]
    longitudes = setup["longitudes"]
    levels = setup["levels"]
    lev  = setup["lev"] 
    levf = setup["levf"]
    variables = setup["variables"]

    if cmd_split[1] == "info":
        _mostrar_info_arquivo(setup)
        return
    if cmd_split[1] == "latitudes":
        lat = sorted(latitudes)
        count = 0 
        for l in lat:
            count = count + 1
            print(count," - ",l)
        return
    if cmd_split[1] == "longitudes":
        lon = sorted(longitudes)
        count = 0 
        for l in lon:
            count = count + 1
            print(count," - ",l)
        return
    if cmd_split[1] == "levels":
        for i in range(len(levels)):
            print(i," - ",levels[i])
        return
    if cmd_split[1] == "time":
        print(setup["time"])
        return
    if cmd_split[1] == "time_variable":
        print(setup["time_variable"])
        return
    if cmd_split[1] == "variables":
        count = 0
        for vname in variables.keys():
            count = count+1
            var = variables[vname]
            long_name = var.long_name if 'long_name' in var.ncattrs() else "Sem descrição"
            print(count,"-",vname," : ",long_name)
        return
    if cmd_split[1] == "time_units":
        print(setup["time_units"])
        return
    if cmd_split[1] == "Date":
        print(setup["DataDado"])
        return
    if cmd_split[1] == "lev":
        print("Level set from {0} to {1} = {2} to {3}".format(lev,levels[lev],levf,levels[levf])) 
        return
    if cmd_split[1] == "title":
        print(setup["title"])
        return
    if cmd_split[1] == "label":
        print(setup["label"])   
        return      
    if cmd_split[1] == "map":
        shp_files = [f for f in os.listdir(setup["mappath"]) if f.endswith('.shp')]
        for shp in shp_files:
            if shp == setup["map"]:
                print(shp,"[*]")
            else:
               print(shp,"")   
        return
    if cmd_split[1] == "map_color":
        print(setup["map_color"])  
        return
    if cmd_split[1] == "map_line":
        print(setup["map_line"])  
        return
    if cmd_split[1] == "lat":
        print("from ",setup["lat_min"]," to ",setup["lat_max"]) 
        return
    if cmd_split[1] == "lon":
        print("from ",setup["lon_min"]," to ",setup["lon_max"]) 
        return
    if cmd_split[1] == 'cmap':
        print(setup["cmap"])
        return
    if cmd_split[1] == 'setup':
        print(setup)
        return

