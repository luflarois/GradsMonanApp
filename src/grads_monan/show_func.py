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

    arquivos = setup.get("files") or []
    if len(arquivos) > 1:
        print("")
        print("Ha {0} arquivos abertos nesta sessao. Use 'show files' para ve-los.".format(len(arquivos)))

def _mostrar_arquivos(setup):
    """
    Comando 'show files': mostra uma tabela com os arquivos abertos na
    sessao (numero, nome do arquivo e timestamp, quando disponivel).
    """
    arquivos = setup.get("files") or []
    if not arquivos:
        print("Nenhum arquivo aberto.")
        return

    cab_num, cab_nome, cab_tempo = "Num", "Arquivo", "Timestamp"
    largura_num = max(len(cab_num), max(len(str(info["index"])) for info in arquivos))
    largura_nome = max(len(cab_nome), max(len(info["fileName"]) for info in arquivos))
    largura_tempo = max(len(cab_tempo), max(len(str(info.get("DataDado") or "desconhecida")) for info in arquivos))

    linha_fmt = "{0:<{w0}}  {1:<{w1}}  {2:<{w2}}"
    cabecalho = linha_fmt.format(cab_num, cab_nome, cab_tempo, w0=largura_num, w1=largura_nome, w2=largura_tempo)
    print(cabecalho)
    print("-" * len(cabecalho))
    for info in arquivos:
        timestamp = info.get("DataDado") or "desconhecida"
        print(linha_fmt.format(info["index"], info["fileName"], timestamp,
                                w0=largura_num, w1=largura_nome, w2=largura_tempo))

def _mostrar_tempos(setup):
    """
    Comando 'show times': mostra uma tabela (numero do arquivo + timestamp)
    com o(s) tempo(s) atualmente selecionado(s) por 'set t' (secao 2.1/6
    do manual):

      - Com o modo de serie/animacao ligado ('set t <inicio> <fim>'),
        mostra TODOS os arquivos desse intervalo, um por linha.
      - Caso contrario (selecao pontual de um unico arquivo/tempo, via
        'set t <n>' ou o padrao - setup['arquivo_sel'], secao 2.1), mostra
        so essa UNICA linha.

    Mesmo formato/dado de 'show files' (que sempre lista TODOS os
    arquivos abertos, independente da selecao de 'set t'), so que
    restrito ao(s) tempo(s) selecionado(s) no momento.
    """
    arquivos = setup.get("files") or []
    if not arquivos:
        print("Nenhum arquivo aberto.")
        return

    por_indice = {info["index"]: info for info in arquivos}

    time_ini = setup.get("time_ini")
    time_fim = setup.get("time_fim")
    if time_ini is not None and time_fim is not None:
        indices = list(range(time_ini, time_fim + 1))
    else:
        indices = [setup.get("arquivo_sel", 1)]

    linhas = []
    for i in indices:
        info = por_indice.get(i)
        if info is None:
            linhas.append((i, "(arquivo nao encontrado)"))
        else:
            linhas.append((i, str(info.get("DataDado") or "desconhecida")))

    cab_num, cab_tempo = "Num", "Timestamp"
    largura_num = max(len(cab_num), max(len(str(n)) for n, _ in linhas))
    largura_tempo = max(len(cab_tempo), max(len(t) for _, t in linhas))

    linha_fmt = "{0:<{w0}}  {1:<{w1}}"
    cabecalho = linha_fmt.format(cab_num, cab_tempo, w0=largura_num, w1=largura_tempo)
    print(cabecalho)
    print("-" * len(cabecalho))
    for n, t in linhas:
        print(linha_fmt.format(n, t, w0=largura_num, w1=largura_tempo))

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
    if cmd_split[1] == "files":
        _mostrar_arquivos(setup)
        return
    if cmd_split[1] == "times":
        _mostrar_tempos(setup)
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
        # 'levf' e guardado como o limite EXCLUSIVO da faixa (ver
        # 'levf_efetivo' em utils.py) - o ULTIMO nivel de verdade
        # incluido na selecao e 'levf - 1', nao 'levf' (que pode valer
        # ate 'len(levels)', um indice fora da lista 'levels').
        ultimo = max(lev, levf - 1)
        print("Level set from {0} to {1} = {2} to {3}".format(lev, ultimo, levels[lev], levels[ultimo]))
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
    if cmd_split[1] == 'limits':
        arquivo = setup.get("limits_arquivo")
        mask = setup.get("limits_mask")
        if arquivo is None or mask is None:
            print("Nenhuma area de limites carregada. Use 'load limits <arquivo.csv>'.")
            return
        print("Arquivo de limites: {0}".format(arquivo))
        print("Pontos do poligono: {0}".format(len(setup.get("limits_poligono", []))))
        print("Celulas da malha dentro da area: {0} de {1}".format(int(mask.sum()), len(mask)))
        return

