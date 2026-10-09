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

def levf_efetivo(lev, levf):
    """
    'levf' e guardado (por 'set lev', set_func.py) como o limite superior
    EXCLUSIVO da faixa de niveis - a convencao de fatia do Python usada em
    toda fatia de nivel do codigo ('var[..., lev:levf]', 'levels[lev:levf]',
    etc: 'set lev <inicial> <final>' guarda 'levf' = <final> + 1, para que
    <final> - um indice de nivel de verdade, igual a <inicial> - fique
    INCLUIDO na fatia).

    So 'levf' de fato define uma faixa quando maior que 'lev' (uma faixa
    "de verdade", vinda de 'set lev <inicial> <final>'); no caso mais comum
    - um UNICO nivel selecionado ('set lev <n>', que guarda lev==levf==n) -
    a fatia 'lev:levf' ficaria VAZIA (limite superior exclusivo do Python
    aplicado a um par de indices iguais). Esta funcao devolve o limite
    superior EFETIVO a usar nesse caso (lev+1, incluindo exatamente aquele
    nivel), preservando o comportamento normal quando ja ha uma faixa
    genuina - usada tanto pelas estatisticas (estatistics.py) quanto pela
    plotagem direta de perfil/corte (plot_func.py), para que um UNICO
    nivel selecionado sempre produza aquele nivel, nunca uma fatia vazia.
    """
    return levf if levf > lev else lev + 1

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

def custom_input(prompt="> "):
    """
    Input personalizado que salva o histórico. 'prompt' (secao 1 do
    manual) muda a cada comando conforme o resultado do anterior: '> '
    (comando reconhecido e executado sem erro), 'E> ' (comando
    reconhecido, mas a execucao falhou) ou '?> ' (comando/sub-comando
    nao reconhecido) - ver '_status_comando'/'_executar_com_status' em
    cli.py.
    """
    # O prompt precisa ser passado direto para input() (e nao escrito antes,
    # via stdout.write) para que o readline o redesenhe corretamente ao
    # navegar pelo historico com as setas para cima/baixo.
    user_input = input(prompt)
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

# ---------------------------------------------------------------------------
# Coordenada vertical POR VARIAVEL
#
# Uma saida MONAN/MPAS pode trazer varios tipos de nivel vertical ao mesmo
# tempo, cada um com a sua dimensao no NetCDF:
#   - pressao : dimensao 't_iso_levels' / 'nIsoLevelsT' (valores em Pa na
#               variavel 't_iso_levels'; o programa mostra em hPa);
#   - altura  : dimensao 'nVertLevels' / 'nVertLevelsP1' (niveis nativos do
#               modelo; a altura em metros vem da variavel 'zgrid', quando
#               existe, e varia de celula para celula);
#   - solo    : dimensao 'nSoilLevels' (profundidade do centro das camadas,
#               em metros, vem da variavel 'zs'; na falta dela, calculada a
#               partir da espessura das camadas 'dzs').
# O tipo de nivel de uma variavel e decidido pela sua PROPRIA dimensao
# vertical (e nao mais por um unico eixo valido para o arquivo todo).
# ---------------------------------------------------------------------------

TIPOS_NIVEL = ("pressao", "altura", "solo", "indice")

_NOME_TIPO_NIVEL = {
    "pressao": "pressao (hPa)",
    "altura": "altura do modelo",
    "solo": "solo (profundidade, m)",
    "indice": "indice de nivel",
}

def classificar_dim_vertical(nome_dim):
    """Tipo de nivel ('pressao'/'solo'/'altura'/'indice') de uma dimensao
    pelo nome, ou None se nao for uma dimensao vertical."""
    n = str(nome_dim).lower()
    if "iso" in n:
        return "pressao"
    if "soil" in n:
        return "solo"
    if "vert" in n:
        return "altura"
    if "lev" in n:
        return "indice"
    return None

def _para_float(x):
    """Array float, com mascara (masked array) virando NaN."""
    return np.ma.filled(np.ma.asarray(x, dtype=float), np.nan)

def _attr(var, nome):
    try:
        if nome in var.ncattrs():
            return var.getncattr(nome)
    except Exception:
        pass
    return None

def _reduzir_para_eixo(var, dim):
    """Media de 'var' sobre todas as dimensoes menos 'dim' -> vetor 1-D."""
    dims = tuple(getattr(var, "dimensions", ()))
    if dim not in dims:
        return None
    arr = _para_float(var[:])
    eixo = dims.index(dim)
    outros = tuple(i for i in range(arr.ndim) if i != eixo)
    if not outros:
        return arr
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.nanmean(arr, axis=outros)

def _valores_pressao(variables, dim, n):
    """Pressao em hPa dos niveis da dimensao 'dim' (ou None)."""
    candidatos = [dim]
    d = str(dim)
    if d.lower().startswith("niso") and len(d) > 0:
        candidatos.append(d[-1].lower() + "_iso_levels")
    candidatos += [v for v in variables if str(v).endswith("_iso_levels")]
    for nome in candidatos:
        if nome in variables:
            v = variables[nome]
            try:
                if len(v.shape) == 1 and v.shape[0] == n:
                    vals = _para_float(v[:])
                    un = str(_attr(v, "units") or "Pa").strip().lower()
                    if un not in ("hpa", "mb", "mbar", "millibar"):
                        vals = vals / 100.
                    return vals
            except Exception:
                continue
    return None

def _valores_solo(variables, dim, n):
    """(profundidades em m, fonte) das camadas de solo da dimensao 'dim'."""
    # 1) 'zs': profundidade do centro das camadas
    if "zs" in variables:
        try:
            v = variables["zs"]
            vals = None
            if dim in tuple(getattr(v, "dimensions", ())):
                vals = _reduzir_para_eixo(v, dim)
            elif len(v.shape) == 1 and v.shape[0] == n:
                vals = _para_float(v[:])
            if vals is not None and vals.shape == (n,) and np.all(np.isfinite(vals)):
                return np.abs(vals), "zs"
        except Exception:
            pass
    # 2) 'dzs': espessura das camadas -> centros = acumulado - metade
    if "dzs" in variables:
        try:
            dz = _reduzir_para_eixo(variables["dzs"], dim)
            if dz is not None and dz.shape == (n,) and np.all(np.isfinite(dz)):
                dz = np.abs(dz)
                return np.cumsum(dz) - dz / 2.0, "dzs (centros calculados da espessura das camadas)"
        except Exception:
            pass
    return None, "indice"

def _montar_descritor(variables, dim, n):
    tipo = classificar_dim_vertical(dim) or "indice"
    desc = {"tipo": tipo, "dim": dim, "n": int(n), "fonte": "indice",
            "valores": np.arange(n, dtype=float), "rotulo": "Levels",
            "unidade": "", "invertido": False}
    if tipo == "pressao":
        vals = _valores_pressao(variables, dim, n)
        if vals is not None:
            desc.update(valores=vals, rotulo="Pressao (hPa)", unidade="hPa",
                        invertido=True, fonte="t_iso_levels")
        else:
            desc["tipo"] = "indice"
    elif tipo == "solo":
        vals, fonte = _valores_solo(variables, dim, n)
        if vals is not None:
            desc.update(valores=vals, rotulo="Profundidade do solo (m)",
                        unidade="m", invertido=True, fonte=fonte)
        else:
            desc.update(rotulo="Nivel do solo (indice)", invertido=False)
    elif tipo == "altura":
        desc["fonte"] = "zgrid" if "zgrid" in variables else "indice"
    desc["nome_tipo"] = _NOME_TIPO_NIVEL[desc["tipo"]]
    return desc

def descritor_nivel(setup, var=None, variables=None):
    """
    Descritor da coordenada vertical de UMA variavel (dict com: tipo, dim,
    n, valores, rotulo, unidade, invertido, fonte, nome_tipo), a partir da
    sua propria dimensao vertical. Retorna None se 'var' nao tiver
    dimensao vertical (variavel 2D) ou nao trouxer informacao de
    dimensoes (array puro).
    """
    dims = getattr(var, "dimensions", None)
    shape = getattr(var, "shape", None)
    if dims is None or shape is None or len(dims) != len(shape):
        return None
    if variables is None:
        variables = setup.get("variables", {}) if isinstance(setup, dict) else {}
    for eixo, dim in enumerate(dims):
        if eixo == 0 or classificar_dim_vertical(dim) is None:
            continue
        n = shape[eixo]
        cache = setup.setdefault("_cache_niveis", {}) if isinstance(setup, dict) else {}
        chave = (id(variables), dim, n)
        if chave not in cache:
            cache[chave] = _montar_descritor(variables, dim, n)
        return cache[chave]
    return None

def descritores_disponiveis(setup, variables=None):
    """Lista de descritores de TODAS as dimensoes verticais realmente usadas
    pelas variaveis (3D) do arquivo - pressao, altura, solo..."""
    if variables is None:
        variables = setup.get("variables", {})
    vistos = []
    lista = []
    for nome in variables:
        v = variables[nome]
        try:
            d = descritor_nivel(setup, v, variables)
        except Exception:
            d = None
        if d is not None and (d["dim"], d["n"]) not in vistos:
            vistos.append((d["dim"], d["n"]))
            lista.append(d)
    return lista

def nivel_padrao(setup):
    """Descritor 'global' (legado) a partir de setup['levels'] /
    setup['eixo_pressao'], usado quando a variavel nao e conhecida."""
    levels = np.asarray(setup.get("levels", [0]), dtype=float)
    if setup.get("eixo_pressao"):
        return {"tipo": "pressao", "dim": "t_iso_levels", "n": len(levels), "fonte": "t_iso_levels",
                "valores": levels, "rotulo": "Pressao (hPa)", "unidade": "hPa",
                "invertido": True, "nome_tipo": _NOME_TIPO_NIVEL["pressao"]}
    return {"tipo": "altura", "dim": "", "n": len(levels), "fonte": "indice",
            "valores": levels, "rotulo": "Levels", "unidade": "",
            "invertido": False, "nome_tipo": _NOME_TIPO_NIVEL["altura"]}

def nivel_do_setup(setup):
    """Descritor do nivel da variavel em uso agora (registrado pelo
    exec_func ao resolver a variavel), ou o padrao global."""
    nv = setup.get("_nivel_atual")
    return nv if nv is not None else nivel_padrao(setup)

def formatar_nivel(desc, i):
    """Texto do valor do nivel 'i' ('850.0 hPa', '0.35 m de profundidade'...)."""
    try:
        v = float(desc["valores"][i])
    except Exception:
        return "indice {0}".format(i)
    if desc["tipo"] == "pressao":
        return "{0:.1f} hPa".format(v)
    if desc["tipo"] == "solo" and desc["unidade"] == "m":
        return "{0:.3f} m de profundidade".format(v)
    return "indice {0}".format(i)

def checar_niveis(setup, desc, nome_var):
    """Confere se o 'set lev' atual cabe nos niveis de 'desc'. Imprime o
    erro e retorna False se nao couber."""
    if desc is None:
        return True
    lev = setup.get("lev", 0)
    ultimo = levf_efetivo(lev, setup.get("levf", lev)) - 1
    n = desc["n"]
    if lev < 0 or ultimo >= n:
        print("Erro: '{0}' tem {1} nivel(is) de {2} (indices 0 a {3}), mas o 'set lev' atual vai de {4} a {5}.".format(
            nome_var, n, desc["nome_tipo"], n - 1, lev, ultimo))
        print("Use 'set lev <n>' (ou 'set lev <ini> <fim>') dentro dessa faixa; 'show levels' lista os niveis de cada tipo.")
        return False
    return True
