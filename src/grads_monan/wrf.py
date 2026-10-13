#!/usr/bin/python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# ---------------------------------------------------------------------------
"""
Suporte a saidas do modelo atmosferico WRF (wrfout_*, grade Arakawa C).

Mesma ideia do ROMS (roms.py), cuja classe de variavel e reaproveitada:
o arquivo e apresentado ao resto do programa como uma "malha" de pontos de
MASSA (south_north x west_east), no formato (Time, nCells[, niveis]):

  - variaveis em pontos U (west_east_stag) ou V (south_north_stag) sao
    levadas para os pontos de massa pela media dos dois vizinhos;
  - niveis: 'bottom_top' -> 'nVertLevels', 'bottom_top_stag' (W, PH...) ->
    'nVertLevelsP1', 'soil_layers_stag' -> 'nSoilLevels'. A ordem do WRF e
    mantida: nivel 0 = o mais baixo (junto a superficie), como no MONAN;
  - 'zgrid' (virtual): altura geopotencial (PH+PHB)/g nas interfaces W, do
    primeiro tempo - usada nos cortes verticais, perfis e 'set lev';
  - 'zs' (virtual): profundidade das camadas de solo (de ZS);
  - 'U_east'/'V_north' e 'U10_east'/'V10_north' (virtuais): vento
    rotacionado da grade do modelo para leste/norte com SINALPHA/COSALPHA
    (em projecao Mercator a rotacao e nula, mas em Lambert/polar nao);
  - 'pressure' (hPa, P+PB), 'theta' (K, T+300) e 'tk' (temperatura, K)
    (virtuais), ja que o wrfout guarda so as perturbacoes.

A grade vem do proprio wrfout (XLAT/XLONG). Opcionalmente, pode vir de um
arquivo separado (geo_em/wrfinput, com XLAT/XLONG ou XLAT_M/XLONG_M).
"""
# ---------------------------------------------------------------------------
import os
from datetime import datetime, timedelta
import numpy as np
from netCDF4 import Dataset

from .roms import (VariavelGradeC, _Variaveis, _Dim, _float_nan, _origem_unidades)

_PONTOS_WRF = {
    ("south_north", "west_east"): "rho",
    ("south_north", "west_east_stag"): "u+",     # U: uma coluna a mais que a massa
    ("south_north_stag", "west_east"): "v+",     # V: uma linha a mais
}
_DIMS_VERTICAIS_WRF = {
    "bottom_top": "nVertLevels",
    "bottom_top_stag": "nVertLevelsP1",
    "soil_layers_stag": "nSoilLevels",
}
_OCULTAS_WRF = {"XLAT_U", "XLONG_U", "XLAT_V", "XLONG_V"}
_PARES_VETOR_WRF = (("U", "V", "U_east", "V_north"),
                    ("U10", "V10", "U10_east", "V10_north"))
_G = 9.81


def eh_wrf(dataset):
    """True se o arquivo usa a grade do WRF (dimensoes south_north/west_east)."""
    try:
        dims = dataset.dimensions
        return "south_north" in dims and "west_east" in dims
    except Exception:
        return False


def _primeiro_tempo(arr):
    arr = _float_nan(arr)
    return arr[0] if arr.ndim == 3 else arr


class GradeWrf(object):
    """Geometria da grade do WRF (pontos de massa, cantos, rotacao)."""

    pontos = _PONTOS_WRF
    dims_verticais = _DIMS_VERTICAIS_WRF
    inverter_niveis = False

    def __init__(self, dados, grade=None):
        fontes = [ds for ds in (grade, dados) if ds is not None]

        def achar(*nomes):
            for ds in fontes:
                for nome in nomes:
                    if nome in ds.variables:
                        return ds.variables[nome]
            return None

        lat = achar("XLAT", "XLAT_M")
        lon = achar("XLONG", "XLONG_M")
        if lat is None or lon is None:
            raise ValueError("XLAT/XLONG nao encontradas no arquivo de dados nem no de grade")
        self.lat_rho = _primeiro_tempo(lat[:])
        self.lon_rho = _primeiro_tempo(lon[:])
        self.shape = self.lat_rho.shape            # (south_north, west_east)
        for nome_dim, tamanho in zip(("south_north", "west_east"), self.shape):
            if nome_dim in dados.dimensions and dados.dimensions[nome_dim].size != tamanho:
                raise ValueError("a grade tem {0}={1}, mas o arquivo de dados tem {0}={2}".format(
                    nome_dim, tamanho, dados.dimensions[nome_dim].size))

        # Cantos das celulas (equivalente aos pontos PSI do ROMS)
        self.lon_psi = 0.25 * (self.lon_rho[:-1, :-1] + self.lon_rho[1:, :-1] +
                               self.lon_rho[:-1, 1:] + self.lon_rho[1:, 1:])
        self.lat_psi = 0.25 * (self.lat_rho[:-1, :-1] + self.lat_rho[1:, :-1] +
                               self.lat_rho[:-1, 1:] + self.lat_rho[1:, 1:])

        self.mask_rho = np.ones(self.shape, dtype=bool)   # atmosfera: sem mascara
        sin_a = achar("SINALPHA")
        cos_a = achar("COSALPHA")
        if sin_a is not None and cos_a is not None:
            self.angle = np.arctan2(np.nan_to_num(_primeiro_tempo(sin_a[:])),
                                    np.nan_to_num(_primeiro_tempo(cos_a[:]), nan=1.0))
        else:
            self.angle = np.zeros(self.shape)
        self.h = None
        self.vertical = None

    @property
    def n_cells(self):
        return self.shape[0] * self.shape[1]

    def latitudes(self):
        return self.lat_rho.ravel()

    def longitudes(self):
        return self.lon_rho.ravel()


class _Var1D(object):
    """Variavel 1-D simples (ex: 'zs', profundidade das camadas de solo)."""

    def __init__(self, nome, valores, dim, attrs):
        self.name = nome
        self._valores = np.asarray(valores, dtype=float)
        self.dimensions = (dim,)
        self.shape = self._valores.shape
        self._attrs = dict(attrs)

    def ncattrs(self):
        return list(self._attrs.keys())

    def getncattr(self, nome):
        return self._attrs[nome]

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        if nome in self._attrs:
            return self._attrs[nome]
        raise AttributeError(nome)

    def __getitem__(self, chave):
        return self._valores[chave]


class DatasetWrf(object):
    """Envolve o Dataset de um wrfout no formato MONAN-like (ver roms.py)."""

    modelo = "WRF"

    def __init__(self, dados, grade, arquivo_grade=None):
        self._ds = dados
        self.grade = grade
        self.arquivo_grade = arquivo_grade
        self.parametros = {}
        self.variables = _Variaveis("WRF")

        for nome, var in dados.variables.items():
            dims = tuple(var.dimensions)
            if len(dims) >= 2 and dims[-2:] in _PONTOS_WRF and nome not in _OCULTAS_WRF:
                self.variables[nome] = VariavelGradeC(nome, grade, var, mascarar=False)
            else:
                self.parametros[nome] = var

        self._criar_vetores_rotacionados()
        self._criar_derivadas()
        self._criar_zgrid()
        self._criar_zs()

        self.dimensions = {"Time": _Dim("Time", self._n_tempos()),
                           "nCells": _Dim("nCells", grade.n_cells)}
        for dim_wrf, dim_nova in _DIMS_VERTICAIS_WRF.items():
            if dim_wrf in dados.dimensions:
                self.dimensions[dim_nova] = _Dim(dim_nova, dados.dimensions[dim_wrf].size)

    def _n_tempos(self):
        if "Time" in self._ds.dimensions:
            return int(self._ds.dimensions["Time"].size)
        return 1

    def _virtual(self, nome, calcular, base, attrs):
        return VariavelGradeC(nome, self.grade, calcular=calcular, attrs=attrs,
                              dims=base.dimensions, shape=base.shape)

    def _criar_vetores_rotacionados(self):
        ang = self.grade.angle.ravel()
        cos_a, sin_a = np.cos(ang), np.sin(ang)
        for nu, nv, nome_e, nome_n in _PARES_VETOR_WRF:
            if nu not in self.variables or nv not in self.variables:
                continue
            vu, vv = self.variables[nu], self.variables[nv]
            if vu.shape != vv.shape:
                continue

            def rot(vu=vu, vv=vv, leste=True):
                u = vu.valores()
                v = vv.valores()
                c = cos_a.reshape((1, -1) + (1,) * (u.ndim - 2))
                s = sin_a.reshape((1, -1) + (1,) * (u.ndim - 2))
                return u * c - v * s if leste else v * c + u * s

            unid = vu.units if "units" in vu.ncattrs() else "m s-1"
            self.variables[nome_e] = self._virtual(
                nome_e, lambda f=rot: f(leste=True), vu,
                {"description": "earth-relative eastward wind (from {0}, rotated with SINALPHA/COSALPHA)".format(nu),
                 "units": unid})
            self.variables[nome_n] = self._virtual(
                nome_n, lambda f=rot: f(leste=False), vv,
                {"description": "earth-relative northward wind (from {0}, rotated with SINALPHA/COSALPHA)".format(nv),
                 "units": unid})

    def _criar_derivadas(self):
        v = self.variables
        if "P" in v and "PB" in v and "pressure" not in v:
            p, pb = v["P"], v["PB"]
            v["pressure"] = self._virtual(
                "pressure", lambda: (p.valores() + pb.valores()) / 100.0, p,
                {"description": "full pressure (P+PB)", "units": "hPa"})
        if "T" in v and "theta" not in v:
            t = v["T"]
            v["theta"] = self._virtual(
                "theta", lambda: t.valores() + 300.0, t,
                {"description": "potential temperature (T+300)", "units": "K"})
            if "pressure" in v and "tk" not in v:
                pr = v["pressure"]
                v["tk"] = self._virtual(
                    "tk", lambda: (t.valores() + 300.0) * (pr.valores() / 1000.0) ** (287.0 / 1004.5), t,
                    {"description": "air temperature", "units": "K"})

    def _criar_zgrid(self):
        ds = self._ds
        if "PH" not in ds.variables or "PHB" not in ds.variables:
            return
        grade = self.grade
        n = ds.dimensions["bottom_top_stag"].size if "bottom_top_stag" in ds.dimensions else ds.variables["PH"].shape[1]

        def calc():
            ph = _float_nan(ds.variables["PH"][:])
            phb = _float_nan(ds.variables["PHB"][:])
            z = (ph[0] + phb[0]) / _G if ph.ndim == 4 else (ph + phb) / _G   # (N+1, Y, X)
            return np.ascontiguousarray(z.reshape(z.shape[0], -1).T)        # (nCells, N+1)

        self.variables["zgrid"] = VariavelGradeC(
            "zgrid", grade, calcular=calc,
            attrs={"description": "geopotential height (PH+PHB)/g at W levels (first time)", "units": "m"},
            dims=("nCells", "nVertLevelsP1"), shape=(grade.n_cells, n))

    def _criar_zs(self):
        ds = self._ds
        if "ZS" in ds.variables and "zs" not in self.variables:
            try:
                zs = _float_nan(ds.variables["ZS"][:])
                zs = zs[0] if zs.ndim == 2 else zs
                self.variables["zs"] = _Var1D("zs", zs, "nSoilLevels",
                                              {"description": "depths of centers of soil layers", "units": "m"})
            except Exception:
                pass

    def ncattrs(self):
        return self._ds.ncattrs()

    def getncattr(self, nome):
        return self._ds.getncattr(nome)

    def close(self):
        try:
            self._ds.close()
        except Exception:
            pass

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        return getattr(self._ds, nome)


def tempos_wrf(dataset):
    """Datas de cada registro do wrfout, de 'Times' (ou de 'XTIME').
    Retorna (lista de datetime ou [], variavel de tempo ou None, unidades)."""
    bruto = dataset._ds if isinstance(dataset, DatasetWrf) else dataset
    if "Times" in bruto.variables:
        var = bruto.variables["Times"]
        try:
            arr = np.asarray(var[:])
            datas = []
            for linha in np.atleast_2d(arr):
                texto = b"".join(x if isinstance(x, bytes) else str(x).encode() for x in np.ravel(linha))
                texto = texto.decode("utf-8", "ignore").strip("\x00 ").replace("_", " ")
                datas.append(datetime.strptime(texto[:19], "%Y-%m-%d %H:%M:%S"))
            return datas, var, "Times (AAAA-MM-DD_hh:mm:ss)"
        except Exception:
            pass
    if "XTIME" in bruto.variables:
        var = bruto.variables["XTIME"]
        unidades = var.getncattr("units") if "units" in var.ncattrs() else "desconhecida"
        escala, origem = _origem_unidades(unidades)
        if escala is not None:
            valores = np.asarray(var[:], dtype=float).ravel()
            return [origem + timedelta(seconds=float(v) * escala) for v in valores], var, unidades
        return [], var, unidades
    return [], None, "desconhecida"


def abrir_wrf(dataset, nome_arquivo, arquivo_grade=None):
    """
    Monta o DatasetWrf de um wrfout ja aberto. 'arquivo_grade' (opcional):
    geo_em/wrfinput com XLAT/XLONG (ou XLAT_M/XLONG_M) - so necessario se o
    proprio wrfout nao trouxer XLAT/XLONG.
    Retorna (DatasetWrf, caminho_da_grade_usada_ou_None).
    """
    ds_grade = None
    if arquivo_grade is not None:
        if not os.path.exists(arquivo_grade):
            raise IOError("arquivo de grade '{0}' nao encontrado".format(arquivo_grade))
        ds_grade = Dataset(arquivo_grade, "r")
        if not eh_wrf(ds_grade):
            ds_grade.close()
            raise ValueError("'{0}' nao parece uma grade do WRF (sem south_north/west_east)".format(arquivo_grade))
    elif "XLAT" not in dataset.variables:
        raise ValueError("o wrfout nao traz XLAT/XLONG; informe a grade: open {0} <geo_em_ou_wrfinput.nc>".format(nome_arquivo))
    try:
        grade = GradeWrf(dataset, ds_grade)
    finally:
        if ds_grade is not None:
            ds_grade.close()
    return DatasetWrf(dataset, grade, arquivo_grade), arquivo_grade
