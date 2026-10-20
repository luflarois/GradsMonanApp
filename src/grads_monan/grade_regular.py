#!/usr/bin/python
# -*- coding: utf-8 -*- Line 2
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# Created Date: 19Oct2026
# version ='0.1'
# ---------------------------------------------------------------------------
""" Suporte a arquivos NetCDF em GRADE REGULAR (latitude x longitude)."""
# ---------------------------------------------------------------------------
#
# Saidas pos-processadas do MONAN (e de outros modelos) podem vir
# interpoladas para uma grade regular lat/lon: dimensoes 'latitude' e
# 'longitude' (com variaveis-coordenada 1-D de mesmo nome) e variaveis
# (Time, latitude, longitude) ou (Time, level, latitude, longitude), em vez
# da malha nao estruturada de Voronoi (dimensao 'nCells' + 'latCell'/
# 'lonCell').
#
# Em vez de duplicar todo o programa para duas geometrias, este modulo
# "adapta" o arquivo regular para a representacao que o resto do programa
# ja entende: cada ponto da grade vira uma "celula" (nCells = nlat x nlon,
# ordem lat-maior) e as variaveis passam a ter o formato
#     (Time, nCells)  ou  (Time, nCells, nivel)
# - o nivel vertical sempre na ULTIMA posicao, qualquer que seja a ordem no
# arquivo (ex: acc_etrani(Time, level, latitude, longitude)). O arquivo
# original nao e alterado: a conversao e feita sob demanda, na leitura.
import numpy as np

from .utils import classificar_dim_vertical

_NOMES_LAT = ("latitude", "lat", "lats", "latitudes")
_NOMES_LON = ("longitude", "lon", "lons", "longitudes", "long")


def _attr(var, nome):
    try:
        if nome in var.ncattrs():
            return var.getncattr(nome)
    except Exception:
        pass
    return None


def _coordenada_1d(variables, nome, var, nomes_aceitos, palavra_unidade, standard):
    """True se 'var' e uma variavel-coordenada 1-D (dimensao com o proprio
    nome) que representa latitude/longitude, pelo CONTEUDO do arquivo:
    standard_name, unidades de grau ou, na falta disso, o nome."""
    dims = tuple(getattr(var, "dimensions", ()))
    if len(dims) != 1 or dims[0] != nome:
        return False
    sn = str(_attr(var, "standard_name") or "").lower()
    un = str(_attr(var, "units") or "").lower().replace(" ", "_")
    if sn == standard:
        return True
    if un.startswith("degree") and palavra_unidade in un:
        return True
    if un in ("degrees_" + palavra_unidade[0], "degree_" + palavra_unidade[0]):
        return True
    return nome.lower() in nomes_aceitos


def detectar_grade_regular(dataset):
    """
    Retorna {'lat_dim','lon_dim','lat','lon'} (lat/lon: vetores 1-D em
    graus) se o arquivo estiver em grade regular lat/lon, ou None.
    Regras (pelo conteudo do arquivo, nao pelo nome do arquivo): NAO ter a
    malha do MPAS ('nCells'/'latCell'/'lonCell'); ter uma variavel-
    coordenada 1-D de latitude e outra de longitude (standard_name,
    unidades em graus norte/leste ou nome usual), com mais de um ponto e
    valores plausiveis.
    """
    variables = dataset.variables
    if "nCells" in dataset.dimensions or "latCell" in variables or "lonCell" in variables:
        return None

    achados = {}
    for nome, var in variables.items():
        if "lat" not in achados and _coordenada_1d(variables, nome, var, _NOMES_LAT, "north", "latitude"):
            achados["lat"] = nome
        elif "lon" not in achados and _coordenada_1d(variables, nome, var, _NOMES_LON, "east", "longitude"):
            achados["lon"] = nome
    if "lat" not in achados or "lon" not in achados:
        return None

    try:
        lat = np.ma.filled(np.ma.asarray(variables[achados["lat"]][:], dtype=float), np.nan)
        lon = np.ma.filled(np.ma.asarray(variables[achados["lon"]][:], dtype=float), np.nan)
    except Exception:
        return None
    if lat.size < 2 or lon.size < 2 or not np.all(np.isfinite(lat)) or not np.all(np.isfinite(lon)):
        return None
    if np.nanmax(np.abs(lat)) > 90.0 + 1e-6 or np.nanmax(np.abs(lon)) > 360.0 + 1e-6:
        return None
    return {"lat_dim": achados["lat"], "lon_dim": achados["lon"], "lat": lat, "lon": lon}


class _Dimensao:
    """Dimensao virtual (mesma interface minima de netCDF4.Dimension)."""
    def __init__(self, size):
        self.size = int(size)

    def __len__(self):
        return self.size


class _VariavelVirtual:
    """Variavel 1-D calculada (latCell/lonCell, em radianos)."""
    def __init__(self, dados, dims, atributos):
        self._dados = np.asarray(dados)
        self.dimensions = tuple(dims)
        self.shape = self._dados.shape
        self.ndim = self._dados.ndim
        self._atributos = dict(atributos)

    def __getitem__(self, item):
        return self._dados[item]

    def ncattrs(self):
        return list(self._atributos.keys())

    def getncattr(self, nome):
        return self._atributos[nome]

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        try:
            return self.__dict__["_atributos"][nome]
        except KeyError:
            raise AttributeError(nome)


class VariavelGradeRegular:
    """
    Visao de uma variavel (..., latitude, longitude) como
    (Time, nCells[, nivel]): ver o comentario do modulo. Mesma interface
    usada pelo programa em netCDF4.Variable: 'dimensions', 'shape',
    indexacao, 'ncattrs()', 'getncattr()' e os atributos (units, long_name).
    """
    def __init__(self, var, lat_dim, lon_dim, nlat, nlon):
        self._var = var
        dims = tuple(var.dimensions)
        self._ilat = dims.index(lat_dim)
        self._ilon = dims.index(lon_dim)
        extras = [i for i, d in enumerate(dims) if i not in (self._ilat, self._ilon)]
        self._ivert = None
        self._itempo = None
        for i in extras:
            if classificar_dim_vertical(dims[i]) is not None and self._ivert is None:
                self._ivert = i
            elif self._itempo is None:
                self._itempo = i
            else:
                raise ValueError("dimensoes extras nao suportadas em '{0}'".format(dims))
        if len(extras) > (self._ivert is not None) + (self._itempo is not None):
            raise ValueError("dimensoes extras nao suportadas em '{0}'".format(dims))
        self._nceles = nlat * nlon
        nome_tempo = dims[self._itempo] if self._itempo is not None else "Time"
        saida_dims = [nome_tempo, "nCells"]
        saida_shape = [var.shape[self._itempo] if self._itempo is not None else 1, self._nceles]
        if self._ivert is not None:
            saida_dims.append(dims[self._ivert])
            saida_shape.append(var.shape[self._ivert])
        self.dimensions = tuple(saida_dims)
        self.shape = tuple(saida_shape)
        self.ndim = len(self.shape)

    # --- leitura ------------------------------------------------------
    def _ler(self, t=None):
        """Le os dados e reorganiza para (Time, nCells[, nivel]). Com 't'
        (indice de tempo inteiro), le so aquele instante e devolve
        (nCells[, nivel]) - sem o eixo de tempo."""
        n = len(self._var.dimensions)
        corte = [slice(None)] * n
        if t is not None:
            corte[self._itempo] = t
        arr = self._var[tuple(corte)]
        presentes = [i for i in range(n) if not (t is not None and i == self._itempo)]
        pos = {i: k for k, i in enumerate(presentes)}
        com_tempo = self._itempo is not None and t is None
        ordem = [pos[self._itempo]] if com_tempo else []
        ordem += [pos[self._ilat], pos[self._ilon]]
        if self._ivert is not None:
            ordem.append(pos[self._ivert])
        arr = np.transpose(arr, ordem)
        ini = 1 if com_tempo else 0
        nlat_, nlon_ = arr.shape[ini], arr.shape[ini + 1]
        novo = ((arr.shape[0],) if com_tempo else ()) + (nlat_ * nlon_,) + tuple(arr.shape[ini + 2:])
        arr = arr.reshape(novo)
        if self._itempo is None:
            arr = arr[np.newaxis]        # variavel estatica: um unico "instante"
        return arr

    def __getitem__(self, chave):
        if not isinstance(chave, tuple):
            chave = (chave,)
        # leitura economica: um indice de tempo inteiro le so aquele instante
        if (self._itempo is not None and chave
                and isinstance(chave[0], (int, np.integer))):
            arr = self._ler(int(chave[0]))
            return arr[chave[1:]] if len(chave) > 1 else arr
        return self._ler()[chave]

    # --- atributos ------------------------------------------------------
    def ncattrs(self):
        return self._var.ncattrs()

    def getncattr(self, nome):
        return self._var.getncattr(nome)

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        try:
            return getattr(self._var, nome)
        except AttributeError:
            if nome in self._var.ncattrs():
                return self._var.getncattr(nome)
            raise


class DatasetGradeRegular:
    """
    Arquivo em grade regular com a interface de um Dataset do netCDF4 no
    formato esperado pelo programa: dimensao 'nCells', variaveis virtuais
    'latCell'/'lonCell' (radianos, como no MPAS) e as variaveis lat/lon
    reorganizadas (ver VariavelGradeRegular).
    """
    grade_regular = True

    def __init__(self, dataset, info):
        self._dataset = dataset
        self.info = info
        lat, lon = info["lat"], info["lon"]
        nlat, nlon = len(lat), len(lon)
        lat2d, lon2d = np.meshgrid(lat, lon, indexing="ij")
        self.nlat, self.nlon = nlat, nlon

        self.variables = {}
        self.variables["latCell"] = _VariavelVirtual(
            np.radians(lat2d.ravel()), ("nCells",),
            {"units": "rad", "long_name": "Latitude of cells (grade regular)"})
        self.variables["lonCell"] = _VariavelVirtual(
            np.radians(lon2d.ravel()), ("nCells",),
            {"units": "rad", "long_name": "Longitude of cells (grade regular)"})
        for nome, var in dataset.variables.items():
            dims = tuple(var.dimensions)
            if info["lat_dim"] in dims and info["lon_dim"] in dims:
                try:
                    self.variables[nome] = VariavelGradeRegular(
                        var, info["lat_dim"], info["lon_dim"], nlat, nlon)
                    continue
                except ValueError:
                    continue   # formato nao suportado: variavel fica de fora
            if nome in self.variables:
                continue
            self.variables[nome] = var

        self.dimensions = {"nCells": _Dimensao(nlat * nlon)}
        for nome, dim in dataset.dimensions.items():
            if nome not in (info["lat_dim"], info["lon_dim"]):
                self.dimensions[nome] = dim

    def close(self):
        self._dataset.close()

    def ncattrs(self):
        return self._dataset.ncattrs()

    def getncattr(self, nome):
        return self._dataset.getncattr(nome)

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        return getattr(self._dataset, nome)


def adaptar_se_regular(dataset):
    """Se 'dataset' estiver em grade regular lat/lon (pelo conteudo),
    devolve DatasetGradeRegular; senao devolve o proprio dataset."""
    try:
        info = detectar_grade_regular(dataset)
    except Exception:
        info = None
    if info is None:
        return dataset
    return DatasetGradeRegular(dataset, info)
