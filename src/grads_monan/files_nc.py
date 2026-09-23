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
import numpy as np
from netCDF4 import Dataset
from .plot_func import set_ion, set_window_title
from .utils import normalize_lon, sem_mascara, assinatura_malha

def file_open(fileName, setup_toml, gridFile=None, setup_anterior=None):

    caminho_do_arquivo = os.path.dirname(fileName)
    if os.path.exists(fileName):
        try:
            dataset = Dataset(fileName, 'r')
        except:
            print("File ",fileName," not found!")
            print("Please, check it!")
            return None, None
        nCells_size = None
        if "nCells" in dataset.dimensions:
            nCells_size = dataset.dimensions['nCells'].size

        dataset_tem_malha = "latCell" in dataset.variables and "lonCell" in dataset.variables

        if gridFile is None and nCells_size is not None and dataset_tem_malha:
            # O próprio arquivo de saída já traz a malha (comum quando o stream
            # do MPAS/MONAN inclui latCell/lonCell) - não precisa de arquivo de grade.
            mesh = dataset
            new_file = fileName
        else:
            if nCells_size is None:
                print("Aviso: dimensao 'nCells' nao encontrada no arquivo de dados ", fileName)
                print("Isso costuma acontecer em saidas de diagnostico/pos-processadas, que nao trazem a malha.")

            if gridFile:
                # Grade informada explicitamente pelo usuário (ex: grades regionais,
                # ou quando o proprio arquivo de dados nao tem a dimensao nCells)
                new_file = gridFile
            elif nCells_size is not None:
                # So e possivel adivinhar o nome padrao se soubermos o numero
                # de celulas (obtido do proprio arquivo de dados)
                if caminho_do_arquivo!="":
                    new_file = caminho_do_arquivo+"/x1.{0}.grid.nc".format(nCells_size)
                else:
                    new_file = "x1.{0}.grid.nc".format(nCells_size)
            else:
                # Sem nCells no arquivo de dados e sem grade informada: nao ha
                # como adivinhar o nome do arquivo de grade.
                print("Forneca um arquivo de grade para abrir este arquivo:")
                print("  open "+fileName+" <path_to_grid_file.nc>")
                return None, None

            if not os.path.exists(new_file):
                print("File ",new_file," not found!")
                print("Please, check it!")
                if not gridFile:
                    print("If this is a regional/regionalized grid, provide the grid file explicitly:")
                    print("  open "+fileName+" <path_to_grid_file.nc>")
                return None, None

            try:
                mesh = Dataset(new_file, 'r')
            except:
                print("File ",new_file," not found!")
                print("Please, check it!")
                return None, None

            if "nCells" not in mesh.dimensions:
                print("Arquivo de grade '",new_file,"' tambem nao tem a dimensao 'nCells'!")
                print("Please, check it!")
                return None, None

            if nCells_size is not None and mesh.dimensions['nCells'].size != nCells_size:
                print("Warning: grid file '{0}' has {1} cells, but data file '{2}' has {3} cells.".format(
                    new_file, mesh.dimensions['nCells'].size, fileName, nCells_size))
                print("Please, check it!")
                return None, None
        #patch_collection = get_mpas_patches(mesh, pickleFile=None,file = new_file)
        # Vetorizado com numpy (em vez de um loop Python + math.degrees por
        # elemento) - para malhas grandes (milhoes de celulas), isso sozinho
        # e dezenas de vezes mais rapido.
        latitudes = np.degrees(sem_mascara(mesh.variables['latCell'][:]))
        longitudes = normalize_lon(np.degrees(sem_mascara(mesh.variables['lonCell'][:])))

        variables = dataset.variables

        if 'xtime' in dataset.variables:
            time = dataset.variables['xtime'][:]
            time_str = ''.join([x.decode('utf-8') for x in time[0]])
            #print(time_str)  # Saída: "2025-04-20_00:00:00"
            ano = int(time_str[:4])
            mes = int(time_str[5:7])
            dia = int(time_str[8:10])
            hora = int(time_str[11:13])
            DataDado = "{0:04d}-{1:02d}-{2:02d}T{3}".format(ano,mes,dia,hora)
        else:
            # Algumas saidas (ex: diagnostico/pos-processadas) nao trazem a
            # variavel 'xtime' no formato padrao do MPAS/MONAN.
            print("Aviso: variavel 'xtime' nao encontrada em ",fileName)
            candidatos = [v for v in dataset.variables if "time" in v.lower()]
            if candidatos:
                print("Variaveis com 'time' no nome disponiveis neste arquivo: "+", ".join(candidatos))
            time = [0]
            time_str = ""
            DataDado = "desconhecida"

        if 'initial_time' in dataset.variables:
            time_variable = dataset.variables['initial_time']
            time_units = time_variable.getncattr('units') if 'units' in time_variable.ncattrs() else "desconhecida"
        else:
            print("Aviso: variavel 'initial_time' nao encontrada em ",fileName)
            time_variable = None
            time_units = "desconhecida"
        #Determina o limite das bordas
        if 't_iso_levels' in dataset.variables:
            levels = sem_mascara(dataset.variables['t_iso_levels'][:])/100.
            eixo_pressao = True
        else:
            # Em algumas saídas (ex: regionais) o arquivo não traz níveis
            # isobáricos interpolados (t_iso_levels) - só níveis nativos do modelo.
            print("Aviso: variavel 't_iso_levels' nao encontrada em ",fileName)
            vert_dim = None
            for dim_name in dataset.dimensions:
                if "lev" in dim_name.lower() or "vert" in dim_name.lower():
                    vert_dim = dim_name
                    break
            if vert_dim is not None:
                n_levels = dataset.dimensions[vert_dim].size
                levels = list(range(n_levels))
                print("Usando indices de nivel do modelo (dimensao '{0}', {1} niveis) no lugar de niveis de pressao.".format(vert_dim, n_levels))
            else:
                levels = [0]
                print("Nenhuma dimensao vertical identificada. Assumindo nivel unico (dado 2D).")
            eixo_pressao = False

        malha_atual = assinatura_malha(latitudes, longitudes)

        if setup_anterior is not None and setup_anterior.get("openFile"):
            malha_anterior = setup_anterior.get("_malha_assinatura")
            if malha_anterior is not None and malha_anterior != malha_atual:
                print("Erro: o arquivo '{0}' tem uma malha diferente do(s) arquivo(s) ja aberto(s) nesta sessao.".format(fileName))
                print("Nao e possivel abrir arquivos com grades diferentes na mesma sessao.")
                print("Use 'reinit' se quiser comecar uma nova sessao com outra grade.")
                try:
                    dataset.close()
                except Exception:
                    pass
                if mesh is not dataset:
                    try:
                        mesh.close()
                    except Exception:
                        pass
                return None, None

            setup = setup_anterior
            novo_indice = len(setup.get("files", [])) + 1

            set_ion()
            set_window_title(os.path.basename(fileName))

            file_info = {
                "index"        : novo_indice,
                "fileName"     : fileName,
                "gridFileName" : (None if new_file == fileName else new_file),
                "dataset"      : dataset,
                "time"         : time,
                "time_variable": time_variable,
                "time_units"   : time_units,
                "time_str"     : time_str,
                "DataDado"     : DataDado,
            }
            setup["files"].append(file_info)

            return dataset, setup

        novo_indice = 1

        setup = {"xmark"           : setup_toml["xmark"],
                 "ymark"           : setup_toml["ymark"],
                 "colormark"       : setup_toml["colormark"],
                 "sizemark"        : setup_toml["sizemark"],
                 "legend"          : setup_toml["legend"],
                 "lev"             : setup_toml["lev"],
                 "levf"            : setup_toml["levf"],
                 "gxout"           : setup_toml["gxout"],
                 "title"           : setup_toml["title"],
                 "label"           : setup_toml["label"],
                 "map"             : setup_toml["map"],
                 "map_color"       : setup_toml["map_color"],
                 "map_line"        : setup_toml["map_line"],
                 "cmap"            : setup_toml["cmap"],
                 "lw"              : setup_toml["lw"],
                 "lc"              : setup_toml["lc"],
                 "clevs"           : setup_toml["clevs"],
                 "mappath"         : setup_toml["mappath"],
                 "time_sel"        : setup_toml["time_sel"],
                 "label_fontsize"  : setup_toml["label_fontsize"],
                 "label_fontweight": setup_toml["label_fontweight"],
                 "fig_dpi"         : setup_toml["fig_dpi"],
                 "fig_inches"      : setup_toml["fig_inches"],
                 "fig_transparency": setup_toml["fig_transparency"],
                 "title_color"     : setup_toml["title_color"],
                 "title_fs"        : setup_toml["title_fs"],
                 "title_fw"        : setup_toml["title_fw"],
                 "lat_min"         : float(latitudes.min()), 
                 "lat_max"         : float(latitudes.max()), 
                 "lon_min"         : float(longitudes.min()),
                 "lon_max"         : float(longitudes.max()),
                 "levels"          : levels, 
                 "eixo_pressao"    : eixo_pressao,
                 "latitudes"       : latitudes,
                 "longitudes"      : longitudes,
                 "time"            : time,
                 "time_variable"   : time_variable,
                 "time_units"      : time_units,
                 "time_str"        : time_str,
                 "DataDado"        : DataDado,
                 "openFile"        : True,
                 "openFileName"    : fileName,
                 "gridFileName"    : (None if new_file == fileName else new_file),
                 "pages_rows"      : 1,
                 "pages_cols"      : 1,
                 "page_row"        : 1,
                 "page_col"        : 1,
                 "cut"             : None,
                 "tint"            : 1.0,
                 "draw_map_on"     : False,
                 "variables"       :variables,
                 "_malha_assinatura": malha_atual,
                 "files"           : []}

        set_ion()
        set_window_title(os.path.basename(fileName))

        file_info = {
            "index"        : novo_indice,
            "fileName"     : fileName,
            "gridFileName" : (None if new_file == fileName else new_file),
            "dataset"      : dataset,
            "time"         : time,
            "time_variable": time_variable,
            "time_units"   : time_units,
            "time_str"     : time_str,
            "DataDado"     : DataDado,
        }
        setup["files"].append(file_info)
    else:
        dataset = None
        print(f"O arquivo {fileName} não foi encontrado.")
        print("Verifique o caminho ou o arquivo!")
        return None, None

    return dataset,setup
