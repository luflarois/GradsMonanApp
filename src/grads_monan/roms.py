#!/usr/bin/python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# ---------------------------------------------------------------------------
"""
Suporte a saidas do modelo oceanico ROMS (grade curvilinea Arakawa C).

O resto do programa foi escrito para a malha nao estruturada do MONAN/MPAS:
toda variavel e vista como (Time, nCells[, nVertLevels]), com uma latitude/
longitude por "celula". Este modulo apresenta um arquivo ROMS nesse MESMO
formato, sem que o restante do codigo precise conhecer a grade C:

  - cada ponto RHO (centro de celula) vira uma "celula": nCells = eta_rho *
    xi_rho, na ordem de lon_rho.ravel() (eta varia mais devagar);
  - variaveis em pontos U, V ou PSI (defasadas) sao levadas para os pontos
    RHO por media dos vizinhos (destaggering) - nas bordas, onde so existe
    um vizinho, o valor da borda e repetido;
  - pontos de terra (mask_rho == 0) e o _FillValue viram NaN;
  - a coordenada vertical s (s_rho / s_w) vira a dimensao 'nVertLevels' /
    'nVertLevelsP1', com o indice 0 = SUPERFICIE (ordem invertida em
    relacao ao ROMS, onde k=0 e o fundo);
  - uma variavel virtual 'zgrid' traz a profundidade z (m, negativa abaixo
    da superficie) de cada nivel s em cada ponto RHO, calculada a partir de
    Vtransform/Vstretching (Cs_r, s_rho, hc, h, zeta) - usada nos cortes
    verticais, perfis e 'set lev' (profundidade media do nivel);
  - variaveis virtuais 'u_east'/'v_north' (e 'ubar_east'/'vbar_north')
    trazem as componentes da corrente rotacionadas da direcao da grade
    (xi, eta) para leste/norte, usando o angulo 'angle' da grade - estas
    sao as que devem ser usadas para vetores/linhas de corrente em mapas.

A grade pode vir do proprio arquivo de saida (que normalmente ja traz lon_*,
lat_*, mask_*, angle, h) ou de um arquivo de grade separado (ex:
swa6_grd.nc), informado no 'open <dados> <grade>'.
"""
# ---------------------------------------------------------------------------
import os
import warnings
from datetime import datetime, timedelta
import numpy as np
from netCDF4 import Dataset

# Pares de dimensoes horizontais de cada tipo de ponto da grade C.
_PONTOS = {
    ("eta_rho", "xi_rho"): "rho",
    ("eta_u", "xi_u"): "u",
    ("eta_v", "xi_v"): "v",
    ("eta_psi", "xi_psi"): "psi",
}
_DIMS_VERTICAIS = {"s_rho": "nVertLevels", "s_w": "nVertLevelsP1"}

# Variaveis da grade que NAO fazem sentido como campo a plotar (coordenadas
# de pontos defasados, mascaras defasadas) - ficam fora da lista de
# variaveis para nao poluir 'show info'/'show variables'.
_OCULTAS = {"lon_u", "lat_u", "lon_v", "lat_v", "lon_psi", "lat_psi",
            "mask_u", "mask_v", "mask_psi", "x_u", "y_u", "x_v", "y_v",
            "x_psi", "y_psi"}

# Variaveis de grade estaticas que NAO devem ser mascaradas em terra.
_SEM_MASCARA = {"lon_rho", "lat_rho", "mask_rho", "angle", "f", "pm", "pn",
                "x_rho", "y_rho", "dndx", "dmde", "hraw"}

# Pares (u, v) que ganham versao rotacionada para leste/norte.
_PARES_VETOR = (("u", "v", "u_east", "v_north"),
                ("ubar", "vbar", "ubar_east", "vbar_north"),
                ("sustr", "svstr", "sustr_east", "svstr_north"),
                ("bustr", "bvstr", "bustr_east", "bvstr_north"),
                ("Uwind", "Vwind", "Uwind_east", "Vwind_north"))


def eh_roms(dataset):
    """True se o arquivo usa a grade C do ROMS (dimensoes eta_rho/xi_rho)."""
    try:
        dims = dataset.dimensions
        return "eta_rho" in dims and "xi_rho" in dims
    except Exception:
        return False


def _float_nan(arr):
    """Array float com mascara/_FillValue (e valores absurdos, >1e36) -> NaN."""
    if np.ma.isMaskedArray(arr):
        arr = np.ma.filled(arr.astype(float), np.nan)
    else:
        arr = np.asarray(arr, dtype=float)
    arr = np.where(np.abs(arr) > 1e36, np.nan, arr)
    return arr


def _nanmedia2(a, b):
    """Media de dois arrays ignorando NaN (se so um existir, usa ele)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmean(np.stack((a, b)), axis=0)


def _destagger_xi(arr):
    """(..., E, X-1) [pontos U] -> (..., E, X) [pontos RHO]."""
    forma = arr.shape[:-1] + (arr.shape[-1] + 1,)
    out = np.empty(forma, dtype=float)
    out[..., 1:-1] = _nanmedia2(arr[..., :-1], arr[..., 1:])
    out[..., 0] = arr[..., 0]
    out[..., -1] = arr[..., -1]
    return out


def _destagger_eta(arr):
    """(..., E-1, X) [pontos V] -> (..., E, X) [pontos RHO]."""
    forma = arr.shape[:-2] + (arr.shape[-2] + 1, arr.shape[-1])
    out = np.empty(forma, dtype=float)
    out[..., 1:-1, :] = _nanmedia2(arr[..., :-1, :], arr[..., 1:, :])
    out[..., 0, :] = arr[..., 0, :]
    out[..., -1, :] = arr[..., -1, :]
    return out


def _media_interna_xi(arr):
    """(..., E, X+1) [U do WRF, faces dos dois lados] -> (..., E, X)."""
    return _nanmedia2(arr[..., :-1], arr[..., 1:])


def _media_interna_eta(arr):
    """(..., E+1, X) [V do WRF] -> (..., E, X)."""
    return _nanmedia2(arr[..., :-1, :], arr[..., 1:, :])


def para_rho(arr, ponto):
    """
    Leva um campo do ponto 'ponto' da grade C para o ponto de massa (RHO):
      - 'u'/'v'/'psi': convencao do ROMS - U/V tem uma coluna/linha A MENOS
        que RHO (as faces da borda externa nao existem); nas bordas o valor
        da face mais proxima e repetido;
      - 'u+'/'v+': convencao do WRF - U/V tem uma coluna/linha A MAIS (as
        duas faces de toda celula existem); media simples das duas faces.
    """
    if ponto == "u+":
        return _media_interna_xi(arr)
    if ponto == "v+":
        return _media_interna_eta(arr)
    if ponto == "u":
        return _destagger_xi(arr)
    if ponto == "v":
        return _destagger_eta(arr)
    if ponto == "psi":
        return _destagger_eta(_destagger_xi(arr))
    return arr


def _angulo_radianos(var):
    """'angle' em radianos. Arquivos de grade costumam rotular 'degree'
    mesmo guardando radianos (o ROMS sempre le radianos) - decide pelos
    valores: |angle| > 2*pi so pode ser grau."""
    ang = _float_nan(var[:])
    if np.nanmax(np.abs(ang)) > 2 * np.pi + 1e-6:
        ang = np.radians(ang)
    return ang


class _Dim(object):
    def __init__(self, nome, size):
        self.name = nome
        self.size = int(size)

    def __len__(self):
        return self.size


class _Variaveis(dict):
    """dict de variaveis com o atributo 'modelo' ('ROMS', 'WRF'...) - usado
    por utils.py para rotular os niveis (ex: profundidade no ROMS)."""

    def __init__(self, modelo="ROMS"):
        dict.__init__(self)
        self.modelo = modelo


class GradeRoms(object):
    """
    Geometria da grade C: coordenadas RHO e PSI, mascara, angulo, batimetria
    e parametros da coordenada s. Vem do arquivo de grade (quando informado)
    complementado pelo arquivo de dados (lon/lat/mask/h/angle ausentes num
    sao procurados no outro; parametros verticais vem do arquivo de dados).
    """

    # Especificacao da grade C usada por VariavelRoms (o WRF - wrf.py - usa
    # a mesma classe de variavel com outra especificacao):
    #   pontos         : par de dimensoes horizontais -> tipo de ponto
    #   dims_verticais : dimensao vertical do modelo -> nome MONAN-like
    #   inverter_niveis: True -> nivel 0 passa a ser o ULTIMO indice do
    #                    modelo (no ROMS, k=0 e o fundo; aqui 0 = superficie)
    pontos = _PONTOS
    dims_verticais = _DIMS_VERTICAIS
    inverter_niveis = True

    def __init__(self, dados, grade=None):
        fontes = [ds for ds in (grade, dados) if ds is not None]

        def achar(nome):
            for ds in fontes:
                if nome in ds.variables:
                    return ds.variables[nome]
            return None

        lon = achar("lon_rho")
        lat = achar("lat_rho")
        if lon is None or lat is None:
            raise ValueError("lon_rho/lat_rho nao encontradas no arquivo de dados nem no de grade")
        self.lon_rho = _float_nan(lon[:])
        self.lat_rho = _float_nan(lat[:])
        self.shape = self.lon_rho.shape            # (eta_rho, xi_rho)

        for nome_dim, tamanho in zip(("eta_rho", "xi_rho"), self.shape):
            if nome_dim in dados.dimensions and dados.dimensions[nome_dim].size != tamanho:
                raise ValueError("a grade tem {0}={1}, mas o arquivo de dados tem {0}={2}".format(
                    nome_dim, tamanho, dados.dimensions[nome_dim].size))

        lon_psi = achar("lon_psi")
        lat_psi = achar("lat_psi")
        if lon_psi is not None and lat_psi is not None:
            self.lon_psi = _float_nan(lon_psi[:])
            self.lat_psi = _float_nan(lat_psi[:])
        else:
            # PSI = cantos das celulas: media dos 4 pontos RHO vizinhos.
            self.lon_psi = 0.25 * (self.lon_rho[:-1, :-1] + self.lon_rho[1:, :-1] +
                                   self.lon_rho[:-1, 1:] + self.lon_rho[1:, 1:])
            self.lat_psi = 0.25 * (self.lat_rho[:-1, :-1] + self.lat_rho[1:, :-1] +
                                   self.lat_rho[:-1, 1:] + self.lat_rho[1:, 1:])

        mask = achar("mask_rho")
        self.mask_rho = (np.ones(self.shape, dtype=bool) if mask is None
                         else (np.nan_to_num(_float_nan(mask[:])) > 0.5))

        ang = achar("angle")
        self.angle = np.zeros(self.shape) if ang is None else np.nan_to_num(_angulo_radianos(ang))

        h = achar("h")
        self.h = None if h is None else _float_nan(h[:])

        # Coordenada vertical s - sempre do arquivo de DADOS (e o que o
        # modelo usou nesta rodada).
        self.vertical = None
        try:
            v = dados.variables
            if all(n in v for n in ("s_rho", "Cs_r", "hc")) and self.h is not None:
                self.vertical = {
                    "Vtransform": int(np.asarray(v["Vtransform"][:]).ravel()[0]) if "Vtransform" in v else 1,
                    "s_rho": _float_nan(v["s_rho"][:]),
                    "Cs_r": _float_nan(v["Cs_r"][:]),
                    "hc": float(np.asarray(v["hc"][:]).ravel()[0]),
                }
        except Exception:
            self.vertical = None

    @property
    def n_cells(self):
        return self.shape[0] * self.shape[1]

    def latitudes(self):
        return self.lat_rho.ravel()

    def longitudes(self):
        return self.lon_rho.ravel()

    def profundidade_z(self, zeta=None):
        """z (m, negativo abaixo da superficie) nos pontos RHO, (N, E, X)
        na ordem do ROMS (k=0 no fundo). None sem parametros verticais."""
        if self.vertical is None:
            return None
        p = self.vertical
        h = np.where(np.isfinite(self.h), self.h, 0.0)
        z_eta = np.zeros(self.shape) if zeta is None else np.nan_to_num(zeta)
        s = p["s_rho"][:, None, None]
        C = p["Cs_r"][:, None, None]
        hc = p["hc"]
        with np.errstate(all="ignore"):
            if p["Vtransform"] == 2:
                z0 = (hc * s + h * C) / (hc + h)
                z = z_eta + (z_eta + h) * z0
            else:
                z0 = hc * s + (h - hc) * C
                z = z0 + z_eta * (1.0 + z0 / h)
        z[:, ~self.mask_rho] = np.nan
        return z


class VariavelRoms(object):
    """
    Uma variavel do ROMS vista no formato do resto do programa:
    shape (Time, nCells[, nVertLevels]) e dimensions ('Time', 'nCells'[,
    'nVertLevels']). Os dados so sao lidos/convertidos no primeiro acesso
    (e guardados em cache - o resto do codigo le 'var[:]' varias vezes).
    """

    def __init__(self, nome, grade, var_nc=None, calcular=None, attrs=None,
                 dims=None, shape=None, mascarar=True):
        self.name = nome
        self._grade = grade
        self._var = var_nc
        self._calcular = calcular
        self._attrs = dict(attrs or {})
        self._mascarar = mascarar
        self._cache = None
        if var_nc is not None:
            self._preparar_dims(var_nc)
        else:
            self.dimensions = tuple(dims)
            self.shape = tuple(shape)

    def _preparar_dims(self, var):
        dims = tuple(var.dimensions)
        self._ponto = self._grade.pontos[dims[-2:]]
        self._eixo_tempo = 0 if (len(dims) > 2 and "time" in dims[0].lower()) else None
        self._eixo_vert = None
        dim_vert = None
        for i, d in enumerate(dims[:-2]):
            if d in self._grade.dims_verticais:
                self._eixo_vert = i
                dim_vert = d
        n_t = var.shape[0] if self._eixo_tempo is not None else 1
        novas_dims = ["Time", "nCells"]
        nova_forma = [n_t, self._grade.n_cells]
        if dim_vert is not None:
            novas_dims.append(self._grade.dims_verticais[dim_vert])
            nova_forma.append(var.shape[self._eixo_vert])
        self.dimensions = tuple(novas_dims)
        self.shape = tuple(nova_forma)
        self.ponto_original = self._ponto
        self.dims_originais = dims

    # --- atributos NetCDF (long_name, units...) ---------------------------
    def ncattrs(self):
        if self._var is not None:
            return [a for a in self._var.ncattrs() if a != "_FillValue"]
        return list(self._attrs.keys())

    def getncattr(self, nome):
        if self._var is not None:
            return self._var.getncattr(nome)
        return self._attrs[nome]

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        if self._var is not None and nome in self._var.ncattrs():
            return self._var.getncattr(nome)
        if nome in self._attrs:
            return self._attrs[nome]
        raise AttributeError(nome)

    @property
    def ndim(self):
        return len(self.shape)

    def __len__(self):
        return self.shape[0]

    # --- dados -------------------------------------------------------------
    def _ler(self):
        var = self._var
        arr = _float_nan(var[:])
        if self._eixo_tempo is None:
            arr = arr[np.newaxis, ...]
        # Agora: (T[, N], E', X') - leva para RHO
        arr = para_rho(arr, self._ponto)
        if self._mascarar:
            arr[..., ~self._grade.mask_rho] = np.nan
        n_t = arr.shape[0]
        if arr.ndim == 4:
            # (T, N, E, X) -> (T, E*X, N); no ROMS, nivel 0 = superficie
            arr = arr.reshape(n_t, arr.shape[1], -1)
            arr = np.transpose(arr, (0, 2, 1))
            if self._grade.inverter_niveis:
                arr = arr[:, :, ::-1]
        else:
            arr = arr.reshape(n_t, -1)
        return np.ascontiguousarray(arr)

    def valores(self):
        if self._cache is None:
            if self._calcular is not None:
                self._cache = self._calcular()
            else:
                self._cache = self._ler()
        return self._cache

    def __getitem__(self, chave):
        return self.valores()[chave]

    def __array__(self, dtype=None, copy=None):
        arr = self.valores()
        return arr.astype(dtype) if dtype is not None else arr


class DatasetRoms(object):
    """
    Envolve o Dataset NetCDF de uma saida ROMS e expoe '.variables' e
    '.dimensions' no formato MONAN-like esperado pelo resto do programa.
    Variaveis escalares/parametros (dt, rdrg, Cs_r...) ficam em
    '.parametros' (fora da lista de variaveis plotaveis).
    """

    modelo = "ROMS"

    def __init__(self, dados, grade, arquivo_grade=None):
        self._ds = dados
        self.grade = grade
        self.arquivo_grade = arquivo_grade
        self.parametros = {}
        self.variables = _Variaveis("ROMS")

        for nome, var in dados.variables.items():
            dims = tuple(var.dimensions)
            if len(dims) >= 2 and dims[-2:] in _PONTOS and nome not in _OCULTAS:
                self.variables[nome] = VariavelRoms(nome, grade, var,
                                                    mascarar=nome not in _SEM_MASCARA)
            else:
                self.parametros[nome] = var

        # Batimetria/angulo vindos so do arquivo de grade, se faltarem nos dados
        for nome, valor in (("h", grade.h), ("angle", grade.angle)):
            if nome not in self.variables and valor is not None:
                self.variables[nome] = self._estatica(nome, valor, nome != "angle",
                                                      {"long_name": "bathymetry at RHO-points", "units": "meter"}
                                                      if nome == "h" else
                                                      {"long_name": "angle between XI-axis and EAST", "units": "radians"})

        self._criar_vetores_rotacionados()
        self._criar_zgrid()

        n_niveis = None
        for v in self.variables.values():
            if "nVertLevels" in v.dimensions:
                n_niveis = v.shape[2]
                break
        if n_niveis is None and grade.vertical is not None:
            n_niveis = len(grade.vertical["s_rho"])

        self.dimensions = {"Time": _Dim("Time", self._n_tempos()),
                           "nCells": _Dim("nCells", grade.n_cells)}
        if n_niveis is not None:
            self.dimensions["nVertLevels"] = _Dim("nVertLevels", n_niveis)
            self.dimensions["nVertLevelsP1"] = _Dim("nVertLevelsP1", n_niveis + 1)

    def _n_tempos(self):
        if "ocean_time" in self._ds.variables:
            return int(self._ds.variables["ocean_time"].shape[0])
        return 1

    def _estatica(self, nome, campo2d, mascarar, attrs):
        grade = self.grade

        def calc():
            arr = np.asarray(campo2d, dtype=float).copy()
            if mascarar:
                arr[~grade.mask_rho] = np.nan
            return arr.reshape(1, -1)
        return VariavelRoms(nome, grade, calcular=calc, attrs=attrs,
                            dims=("Time", "nCells"), shape=(1, grade.n_cells))

    def _criar_vetores_rotacionados(self):
        ang = self.grade.angle.ravel()
        cos_a, sin_a = np.cos(ang), np.sin(ang)
        for nu, nv, nome_e, nome_n in _PARES_VETOR:
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
                return u * c - v * s if leste else u * s + v * c

            unid = getattr(vu, "units", "") if "units" in vu.ncattrs() else ""
            self.variables[nome_e] = VariavelRoms(
                nome_e, self.grade, calcular=lambda f=rot: f(leste=True),
                attrs={"long_name": "eastward component of {0} (rotated from grid)".format(nu), "units": unid},
                dims=vu.dimensions, shape=vu.shape)
            self.variables[nome_n] = VariavelRoms(
                nome_n, self.grade, calcular=lambda f=rot: f(leste=False),
                attrs={"long_name": "northward component of {0} (rotated from grid)".format(nv), "units": unid},
                dims=vv.dimensions, shape=vv.shape)

    def _criar_zgrid(self):
        grade = self.grade
        if grade.vertical is None:
            return
        ds = self._ds

        def calc():
            zeta = None
            if "zeta" in ds.variables:
                z = _float_nan(ds.variables["zeta"][:])
                zeta = z[0] if z.ndim == 3 else z
            z = grade.profundidade_z(zeta)                  # (N, E, X), k=0 fundo
            z = z.reshape(z.shape[0], -1).T[:, ::-1]        # (nCells, N), 0 = superficie
            return np.ascontiguousarray(z)

        n = len(grade.vertical["s_rho"])
        self.variables["zgrid"] = VariavelRoms(
            "zgrid", grade, calcular=calc,
            attrs={"long_name": "depth of RHO-points (z, negative below surface; zeta of the first time)",
                   "units": "meter"},
            dims=("nCells", "nVertLevels"), shape=(grade.n_cells, n))

    # --- repassa o resto ao Dataset original ---------------------------------
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
def _origem_unidades(unidades):
    """'seconds since 1970-01-01 00:00:00' -> (fator em segundos, datetime)."""
    try:
        partes = unidades.split(" since ")
        escala = {"second": 1, "seconds": 1, "s": 1, "minute": 60, "minutes": 60,
                  "hour": 3600, "hours": 3600, "day": 86400, "days": 86400}[partes[0].strip().lower()]
        texto = partes[1].strip().replace("T", " ").split(".")[0]
        texto = texto.split(" ")[0] + (" " + texto.split(" ")[1] if " " in texto else "")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return escala, datetime.strptime(texto, fmt)
            except ValueError:
                continue
    except Exception:
        pass
    return None, None


def tempos_roms(dataset):
    """
    Datas (datetime) de cada registro de 'ocean_time'. Retorna (lista de
    datetime ou [], variavel de tempo ou None, unidades).
    """
    bruto = dataset._ds if isinstance(dataset, DatasetRoms) else dataset
    if "ocean_time" not in bruto.variables:
        return [], None, "desconhecida"
    var = bruto.variables["ocean_time"]
    unidades = var.getncattr("units") if "units" in var.ncattrs() else "desconhecida"
    escala, origem = _origem_unidades(unidades)
    if escala is None:
        return [], var, unidades
    valores = np.asarray(var[:], dtype=float).ravel()
    return [origem + timedelta(seconds=float(v) * escala) for v in valores], var, unidades


# ---------------------------------------------------------------------------
# Abertura
# ---------------------------------------------------------------------------
def abrir_roms(dataset, nome_arquivo, arquivo_grade=None):
    """
    Monta o DatasetRoms de um arquivo ROMS ja aberto ('dataset').
    'arquivo_grade': grade separada (ex: swa6_grd.nc). Sem ela, usa a grade
    do proprio arquivo de saida; se este nao tiver lon_rho/lat_rho, tenta o
    arquivo do atributo global 'grd_file' no mesmo diretorio.
    Retorna (DatasetRoms, caminho_da_grade_usada_ou_None). Levanta
    ValueError/IOError com mensagem explicativa em caso de problema.
    """
    if arquivo_grade is None and "lon_rho" not in dataset.variables:
        try:
            nome_grd = dataset.getncattr("grd_file")
            candidato = os.path.join(os.path.dirname(nome_arquivo), os.path.basename(nome_grd))
            if os.path.exists(candidato):
                arquivo_grade = candidato
        except Exception:
            pass
        if arquivo_grade is None:
            raise ValueError("o arquivo ROMS nao traz lon_rho/lat_rho; informe a grade: open {0} <arquivo_de_grade.nc>".format(nome_arquivo))

    ds_grade = None
    if arquivo_grade is not None:
        if not os.path.exists(arquivo_grade):
            raise IOError("arquivo de grade '{0}' nao encontrado".format(arquivo_grade))
        ds_grade = Dataset(arquivo_grade, "r")
        if not eh_roms(ds_grade):
            ds_grade.close()
            raise ValueError("'{0}' nao parece uma grade ROMS (sem eta_rho/xi_rho)".format(arquivo_grade))

    try:
        grade = GradeRoms(dataset, ds_grade)
    finally:
        if ds_grade is not None:
            ds_grade.close()
    return DatasetRoms(dataset, grade, arquivo_grade), arquivo_grade


# Nome generico (usado tambem pelo WRF - wrf.py)
VariavelGradeC = VariavelRoms
