#!/usr/bin/python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# ---------------------------------------------------------------------------
"""
Suporte a saidas do modelo oceanico MOM6 (GFDL), grade Arakawa C - em
geral a grade TRIPOLAR global (dois polos no norte, sobre os continentes).

Mesma maquinaria do ROMS/WRF (roms.py): os pontos h (centro da celula,
dimensoes yh/xh) viram as "celulas" do programa, no formato (Time, nCells[,
niveis]), lidos um tempo de cada vez.

Coordenadas
-----------
Os arquivos de diagnostico do MOM6 (ex: tempsalt.nc, ocean_daily.nc) so
trazem as coordenadas NOMINAIS 1-D 'xh'/'yh', que NAO sao a posicao real na
grade tripolar (ao norte de ~65N, a grade se dobra sobre dois polos sobre a
terra). A posicao real fica no arquivo estatico (ocean_static.nc, citado em
'associated_files'): geolon/geolat (pontos h), geolon_c/geolat_c (cantos
q), wet (mascara), deptho (profundidade), sin_rot/cos_rot (rotacao).

  open tempsalt.nc ocean_static.nc   -> usa a grade real (recomendado)
  open tempsalt.nc                   -> procura o ocean_static.nc citado em
                                        'associated_files' no mesmo diretorio;
                                        sem ele, usa a grade nominal xh x yh
                                        (correta so para grades regulares)

Pontos da grade C
-----------------
  h (yh, xh)  - temp, salt, SSH, thetao, so...
  u (yh, xq)  - uo, u (face leste)
  v (yq, xh)  - vo, v (face norte)
  q (yq, xq)  - vorticidade (canto nordeste)
Grade "simetrica" (xq = xh + 1): media das duas faces; "nao simetrica" (xq
= xh): face leste/norte de cada celula, periodica em x num dominio global.

Vertical: z_l (centro da camada, m, positivo para baixo) -> nVertLevels;
z_i (interfaces) -> nVertLevelsP1. Indice 0 = superficie (a ordem do MOM6).
'zgrid' (virtual) = -z_l (m, negativo), igual em todos os pontos - usado nos
cortes verticais, perfis e 'set lev' (o fundo e a terra aparecem como dado
ausente nos campos).

Costura de longitude: numa grade global, as longitudes de geolon costumam ir
de -300 a 60. Normalizadas para (-180, 180], ha um "salto" de 360 graus no
meio de cada linha - as colunas sao "roladas" para o salto ficar na borda.
"""
# ---------------------------------------------------------------------------
import os
from datetime import datetime, timedelta
import numpy as np
from netCDF4 import Dataset

from .roms import (VariavelGradeC, _Variaveis, _Dim, _float_nan, _origem_unidades)

_DIMS_VERTICAIS_MOM6 = {
    "z_l": "nVertLevels", "zl": "nVertLevels", "z_i": "nVertLevelsP1", "zi": "nVertLevelsP1",
    "rho2_l": "nVertLevels", "rho2_i": "nVertLevelsP1",
}
_PARES_VETOR_MOM6 = (("uo", "vo", "uo_east", "vo_north"),
                     ("u", "v", "u_east", "v_north"),
                     ("taux", "tauy", "taux_east", "tauy_north"),
                     ("ssu", "ssv", "ssu_east", "ssv_north"))
_ESTATICAS = {"geolon", "geolat", "geolon_c", "geolat_c", "geolon_u", "geolat_u",
              "geolon_v", "geolat_v", "wet", "wet_c", "wet_u", "wet_v",
              "sin_rot", "cos_rot", "area_t", "dxt", "dyt"}


def eh_mom6(dataset):
    """True se o arquivo usa a grade do MOM6 (dimensoes xh/yh, ou xq/yq)."""
    try:
        dims = dataset.dimensions
        return ("xh" in dims and "yh" in dims) or ("xq" in dims and "yq" in dims)
    except Exception:
        return False


def _normalizar(lon):
    return ((np.asarray(lon, dtype=float) + 180.0) % 360.0) - 180.0


class GradeMom6(object):
    """Geometria da grade do MOM6 (pontos h, cantos q, mascara, rotacao)."""

    dims_verticais = _DIMS_VERTICAIS_MOM6
    inverter_niveis = False

    def __init__(self, dados, estatico=None):
        self.nominal = estatico is None or "geolon" not in estatico.variables
        dd = dados.dimensions
        nxh = dd["xh"].size if "xh" in dd else None
        nyh = dd["yh"].size if "yh" in dd else None

        if not self.nominal:
            ev = estatico.variables
            lon = _float_nan(ev["geolon"][:])
            lat = _float_nan(ev["geolat"][:])
            if nxh is not None and lon.shape != (nyh, nxh):
                raise ValueError("o arquivo estatico tem geolon {0}, mas os dados tem (yh, xh) = ({1}, {2})".format(
                    lon.shape, nyh, nxh))
            lon_c = _float_nan(ev["geolon_c"][:]) if "geolon_c" in ev else None
            lat_c = _float_nan(ev["geolat_c"][:]) if "geolat_c" in ev else None
            mask = (np.nan_to_num(_float_nan(ev["wet"][:])) > 0.5) if "wet" in ev else None
            self.h = _float_nan(ev["deptho"][:]) if "deptho" in ev else None
            if "sin_rot" in ev and "cos_rot" in ev:
                ang = np.arctan2(np.nan_to_num(_float_nan(ev["sin_rot"][:])),
                                 np.nan_to_num(_float_nan(ev["cos_rot"][:]), nan=1.0))
            else:
                ang = None
        else:
            if "xh" not in dados.variables or "yh" not in dados.variables:
                raise ValueError("sem coordenadas xh/yh e sem arquivo estatico (ocean_static.nc)")
            xh = _float_nan(dados.variables["xh"][:])
            yh = _float_nan(dados.variables["yh"][:])
            lon, lat = np.meshgrid(xh, yh)
            lon_c = lat_c = None
            if "xq" in dados.variables and "yq" in dados.variables:
                xq = _float_nan(dados.variables["xq"][:])
                yq = _float_nan(dados.variables["yq"][:])
                lon_c, lat_c = np.meshgrid(xq, yq)
            mask = None
            self.h = None
            ang = None

        self.shape = lon.shape                         # (yh, xh)
        ny, nx = self.shape

        # Pontos defasados: simetrico (xq = xh+1) ou nao (xq = xh)
        nxq = dd["xq"].size if "xq" in dd else nx
        nyq = dd["yq"].size if "yq" in dd else ny
        sim_x, sim_y = nxq == nx + 1, nyq == ny + 1
        self.pontos = {
            ("yh", "xh"): "rho",
            ("yh", "xq"): "u+" if sim_x else "ue",
            ("yq", "xh"): "v+" if sim_y else "vn",
            ("yq", "xq"): "q+" if (sim_x and sim_y) else "qne",
        }

        # Dominio global em x? (as longitudes de uma linha cobrem ~360 graus)
        with np.errstate(all="ignore"):
            meio = lon[ny // 2]
            dlon = np.nanmedian(np.abs(np.diff(meio)))
            self.periodico_x = bool(np.isfinite(dlon) and abs(np.nanmax(meio) - np.nanmin(meio) + dlon - 360.0) < 2 * dlon + 1e-6)

        # Angulo da grade: de sin_rot/cos_rot ou calculado das coordenadas
        if ang is None:
            with np.errstate(all="ignore"):
                dx_lon = np.gradient(np.unwrap(np.radians(lon), axis=1), axis=1) * np.cos(np.radians(lat))
                dx_lat = np.gradient(np.radians(lat), axis=1)
                ang = np.nan_to_num(np.arctan2(dx_lat, dx_lon))
        self.angle = ang

        # Longitudes em (-180, 180] e "rolagem" das colunas para a costura
        # (salto de 360 graus) ficar na borda direita
        lon_n = _normalizar(lon)
        self.rolagem_x = 0
        if self.periodico_x:
            linha = lon_n[ny // 2]
            saltos = np.nonzero(np.diff(linha) < -180.0)[0]
            if saltos.size:
                self.rolagem_x = int(saltos[0] + 1)

        def rolar(a):
            return np.roll(a, -self.rolagem_x, axis=-1) if (a is not None and self.rolagem_x) else a

        self.lon_rho = rolar(lon_n)
        self.lat_rho = rolar(lat)
        self.angle = rolar(self.angle)
        self.h = rolar(self.h)
        self.mask_rho = rolar(mask) if mask is not None else np.ones(self.shape, dtype=bool)

        # Cantos das celulas (pontos q) para o 'gxout grfill'
        self.recorte_celulas = None
        if lon_c is not None and lat_c is not None:
            if lon_c.shape == (ny + 1, nx + 1):
                # simetrico: todos os cantos de todas as celulas
                if self.rolagem_x:
                    lon_c = np.concatenate([lon_c[:, self.rolagem_x:-1], lon_c[:, :self.rolagem_x + 1]], axis=1)
                    lat_c = np.concatenate([lat_c[:, self.rolagem_x:-1], lat_c[:, :self.rolagem_x + 1]], axis=1)
                self.lon_psi, self.lat_psi = _normalizar(lon_c), lat_c
                self.recorte_celulas = (slice(None), slice(None))
            elif lon_c.shape == (ny, nx):
                # nao simetrico: canto NE da celula (j, i); a celula (j, i)
                # usa os cantos (j-1..j, i-1..i) -> so celulas j>=1, i>=1
                lon_c, lat_c = rolar(_normalizar(lon_c)), rolar(lat_c)
                self.lon_psi, self.lat_psi = lon_c, lat_c
                self.recorte_celulas = (slice(1, None), slice(1, None))
        if self.recorte_celulas is None:
            self.lon_psi = 0.25 * (self.lon_rho[:-1, :-1] + self.lon_rho[1:, :-1] +
                                   self.lon_rho[:-1, 1:] + self.lon_rho[1:, 1:])
            self.lat_psi = 0.25 * (self.lat_rho[:-1, :-1] + self.lat_rho[1:, :-1] +
                                   self.lat_rho[:-1, 1:] + self.lat_rho[1:, 1:])
            self.recorte_celulas = (slice(1, -1), slice(1, -1))

        self.vertical = None

    @property
    def n_cells(self):
        return self.shape[0] * self.shape[1]

    def latitudes(self):
        return self.lat_rho.ravel()

    def longitudes(self):
        return self.lon_rho.ravel()


class DatasetMom6(object):
    """Envolve o Dataset de uma saida do MOM6 no formato MONAN-like."""

    modelo = "MOM6"

    def __init__(self, dados, grade, arquivo_grade=None):
        self._ds = dados
        self.grade = grade
        self.arquivo_grade = arquivo_grade
        self.parametros = {}
        self.variables = _Variaveis("MOM6")

        for nome, var in dados.variables.items():
            dims = tuple(var.dimensions)
            if len(dims) >= 2 and dims[-2:] in grade.pontos and nome not in _ESTATICAS:
                self.variables[nome] = VariavelGradeC(nome, grade, var)
            else:
                self.parametros[nome] = var

        if "deptho" not in self.variables and grade.h is not None:
            h = grade.h

            def calc_h(k=0):
                return np.asarray(h, dtype=float).reshape(-1)
            self.variables["deptho"] = VariavelGradeC(
                "deptho", grade, calcular=calc_h,
                attrs={"long_name": "Sea Floor Depth (ocean_static)", "units": "m"},
                dims=("Time", "nCells"), shape=(1, grade.n_cells))

        self._criar_vetores_rotacionados()
        self._criar_zgrid()

        self.dimensions = {"Time": _Dim("Time", self.n_tempos),
                           "nCells": _Dim("nCells", grade.n_cells)}
        for dim_m, dim_nova in _DIMS_VERTICAIS_MOM6.items():
            if dim_m in dados.dimensions and dim_nova not in self.dimensions:
                self.dimensions[dim_nova] = _Dim(dim_nova, dados.dimensions[dim_m].size)

    @property
    def n_tempos(self):
        for nome in ("time", "Time"):
            if nome in self._ds.dimensions:
                return int(self._ds.dimensions[nome].size)
        return 1

    def _criar_vetores_rotacionados(self):
        ang = self.grade.angle.ravel()
        cos_a, sin_a = np.cos(ang), np.sin(ang)
        for nu, nv, nome_e, nome_n in _PARES_VETOR_MOM6:
            if nu not in self.variables or nv not in self.variables:
                continue
            vu, vv = self.variables[nu], self.variables[nv]
            if vu.shape != vv.shape:
                continue

            def rot(k, vu=vu, vv=vv, leste=True):
                u = vu.tempo(k)
                v = vv.tempo(k)
                c = cos_a.reshape((-1,) + (1,) * (u.ndim - 1))
                s = sin_a.reshape((-1,) + (1,) * (u.ndim - 1))
                return u * c - v * s if leste else u * s + v * c

            unid = vu.units if "units" in vu.ncattrs() else ""
            for nome, leste, base in ((nome_e, True, vu), (nome_n, False, vv)):
                self.variables[nome] = VariavelGradeC(
                    nome, self.grade, calcular=lambda k, f=rot, l=leste: f(k, leste=l),
                    attrs={"long_name": "{0} component of {1}/{2} (rotated from grid)".format(
                        "eastward" if leste else "northward", nu, nv), "units": unid},
                    dims=base.dimensions, shape=base.shape)

    def _criar_zgrid(self):
        ds = self._ds
        nome_zl = next((n for n in ("z_l", "zl") if n in ds.variables), None)
        if nome_zl is None:
            return
        zl = _float_nan(ds.variables[nome_zl][:])
        grade = self.grade
        if "units" in ds.variables[nome_zl].ncattrs() and "cm" == str(ds.variables[nome_zl].units).strip():
            zl = zl / 100.0

        def calc(k=0):
            # Coordenada z: a profundidade de cada camada e a MESMA em todos
            # os pontos (o fundo e a terra aparecem como dado ausente - NaN -
            # nos campos, hachurados nos cortes verticais).
            return np.tile(-np.abs(zl), (grade.n_cells, 1))              # (nCells, N)

        self.variables["zgrid"] = VariavelGradeC(
            "zgrid", grade, calcular=calc,
            attrs={"long_name": "depth of layer centers (-{0}, negative below surface)".format(nome_zl),
                   "units": "m"},
            dims=("nCells", "nVertLevels"), shape=(grade.n_cells, len(zl)))

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


# ---------------------------------------------------------------------------
# Tempo
# ---------------------------------------------------------------------------
_DIAS_MES_NOLEAP = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _somar_noleap(origem, dias):
    """origem + dias num calendario sem ano bissexto (noleap/365_day)."""
    inicio_ano = sum(_DIAS_MES_NOLEAP[:origem.month - 1]) + (origem.day - 1)
    seg_dia = origem.hour * 3600 + origem.minute * 60 + origem.second
    total = inicio_ano + dias + seg_dia / 86400.0
    anos, resto = divmod(total, 365.0)
    dia_ano = int(resto)
    segundos = int(round((resto - dia_ano) * 86400.0))
    if segundos >= 86400:
        segundos -= 86400
        dia_ano += 1
        if dia_ano >= 365:
            dia_ano -= 365
            anos += 1
    mes = 0
    while dia_ano >= _DIAS_MES_NOLEAP[mes]:
        dia_ano -= _DIAS_MES_NOLEAP[mes]
        mes += 1
    return datetime(origem.year + int(anos), mes + 1, dia_ano + 1) + timedelta(seconds=segundos)


def tempos_mom6(dataset):
    """Datas de cada registro de 'time'. Retorna (datetimes, var, unidades)."""
    bruto = dataset._ds if isinstance(dataset, DatasetMom6) else dataset
    nome = next((n for n in ("time", "Time") if n in bruto.variables), None)
    if nome is None:
        return [], None, "desconhecida"
    var = bruto.variables[nome]
    attrs = var.ncattrs()
    unidades = var.getncattr("units") if "units" in attrs else "desconhecida"
    cal = str(var.getncattr("calendar") if "calendar" in attrs else
              (var.getncattr("calendar_type") if "calendar_type" in attrs else "gregorian")).strip().lower()
    escala, origem = _origem_unidades(unidades)
    if escala is None:
        return [], var, unidades
    valores = np.asarray(var[:], dtype=float).ravel()
    if cal in ("noleap", "365_day", "no_leap"):
        return [_somar_noleap(origem, v * escala / 86400.0) for v in valores], var, unidades
    return [origem + timedelta(seconds=float(v) * escala) for v in valores], var, unidades


# ---------------------------------------------------------------------------
# Abertura
# ---------------------------------------------------------------------------
def _estatico_associado(dataset, nome_arquivo):
    """Caminho do ocean_static.nc citado em 'associated_files' (ou com nome
    padrao) no diretorio do arquivo de dados, se existir."""
    pasta = os.path.dirname(nome_arquivo)
    candidatos = []
    try:
        texto = dataset.getncattr("associated_files")
        for parte in str(texto).split():
            if parte.endswith(".nc"):
                candidatos.append(parte)
    except Exception:
        pass
    candidatos += ["ocean_static.nc", "static.nc", "ocean_hgrid.nc"]
    for c in candidatos:
        caminho = os.path.join(pasta, os.path.basename(c))
        if os.path.exists(caminho) and os.path.abspath(caminho) != os.path.abspath(nome_arquivo):
            return caminho
    return None


def abrir_mom6(dataset, nome_arquivo, arquivo_grade=None):
    """
    Monta o DatasetMom6. 'arquivo_grade': o ocean_static.nc (geolon/geolat).
    Sem ele, procura o arquivo citado em 'associated_files' no mesmo
    diretorio; sem nenhum, usa a grade nominal (xh, yh) e avisa.
    Retorna (DatasetMom6, caminho_do_estatico_ou_None).
    """
    if arquivo_grade is None and "geolon" not in dataset.variables:
        arquivo_grade = _estatico_associado(dataset, nome_arquivo)
    ds_est = None
    if arquivo_grade is not None:
        if not os.path.exists(arquivo_grade):
            raise IOError("arquivo estatico/de grade '{0}' nao encontrado".format(arquivo_grade))
        ds_est = Dataset(arquivo_grade, "r")
        if "geolon" not in ds_est.variables or "geolat" not in ds_est.variables:
            ds_est.close()
            raise ValueError("'{0}' nao tem geolon/geolat (esperado o ocean_static.nc do MOM6)".format(arquivo_grade))
    elif "geolon" in dataset.variables:
        ds_est = dataset
    try:
        grade = GradeMom6(dataset, ds_est)
    finally:
        if ds_est is not None and ds_est is not dataset:
            ds_est.close()
    return DatasetMom6(dataset, grade, arquivo_grade), arquivo_grade
