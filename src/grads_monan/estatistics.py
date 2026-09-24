#!/usr/bin/python
# -*- coding: utf-8 -*- Line 2
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# Created Date: 24Sep2026
# version ='0.5'
# ---------------------------------------------------------------------------
""" Funcoes estatisticas sobre variaveis da malha aberta: soma, media,
minimo, maximo e percentis (P10 a P90).

Cada estatistica tem duas formas:
  - ESCALAR ('sum'/'mean'/'min'/'max'/'p10'..'p90' all|inlimits|point
    <variavel>, despachada por exec_func.py): reduz a variavel a UM UNICO
    NUMERO, impresso na tela antes do proximo prompt; nenhum grafico e
    alterado.
  - ESPACIAL ('d sum|mean|min|max|p10..p90 all|inlimits|point <variavel>'):
    reduz so sobre os arquivos/tempos selecionados (e, no complemento
    'point', tambem sobre os niveis - ver abaixo), plotando o resultado
    como 'd'/'d3' plotariam a propria variavel (mapa, perfil vertical ou
    corte vertical - ver abaixo).

Em ambas as formas, a fatia usada e baseada na MESMA selecao atual de
latitude/longitude/nivel que 'd'/'d3' usariam para plotar a variavel agora
mesmo (secao 3/8 do manual - setup['lat_min']/['lat_max']/['lon_min']/
['lon_max']/['lev']/['levf']):
  - MAPA horizontal (nem lat nem lon fixadas num unico ponto): todas as
    celulas da malha, no NIVEL UNICO selecionado ('set lev <n>').
  - PONTO (lat e lon fixadas no mesmo valor - 'set lat -22'+'set lon -55'):
    perfil vertical na celula mais proxima desse ponto, ao longo da FAIXA
    de niveis selecionada ('set lev <ini> <fim>') - ou so o nivel unico
    selecionado, se nenhuma faixa tiver sido definida.
  - CORTE (so lat OU so lon fixada - 'set lat -22' sozinho): todas as
    celulas da malha, ao longo da FAIXA de niveis selecionada (ou so o
    nivel unico, idem).

O complemento 'point' (ex: 'max point <var>', 'd sum point <var>') pede
explicitamente a estatistica sobre o PERFIL TEMPORAL/VERTICAL: alem dos
tempos (arquivos de 'set t <ini> <fim>'), tambem reduz sobre a faixa de
niveis selecionada mesmo quando nem lat nem lon estao fixadas (modo
"mapa") - permitindo combinar QUALQUER variacao dos 4 componentes (lat,
lon, lev, t): um so ponto e varios tempos, um so tempo e varios niveis,
uma faixa de niveis com o mapa inteiro, etc. Quando isso resulta numa
matriz com eixo de celulas E eixo de niveis ao mesmo tempo, sem lat/lon
fixada para escolher uma direcao de corte (modo interno 'mapa_niveis'), a
forma ESCALAR calcula normalmente (reduz tudo a um numero), mas a forma
ESPACIAL nao tem como plotar (nao ha um mapa nem um corte bem definido) e
avisa em vez de tentar.

E, quando houver mais de um arquivo aberto com um intervalo definido por
'set t <arquivo_inicial> <arquivo_final>', a estatistica usa TODOS os
arquivos (tempos) desse intervalo; caso contrario, usa so o arquivo/
instante atualmente selecionado - ver '_dados_estatistica' em
exec_func.py, que monta a lista de arrays (um por arquivo/tempo) e
tambem resolve expressoes aritmeticas (ex: 't2m-273.15') consumidas pelas
funcoes deste modulo.
"""
# ---------------------------------------------------------------------------
import numpy as np
from .utils import sem_mascara, levf_efetivo as _levf_efetivo

# Rotulo (para as mensagens) e a funcao de reducao "sobre tudo" (escalar) de
# cada estatistica. As funcoes 'np.nan*' ignoram valores sem dado (NaN).
_NOMES_FUNCAO = {
    "sum": "Soma",
    "mean": "Media",
    "min": "Minimo",
    "max": "Maximo",
}
_OPERACOES = {
    "sum": np.nansum,
    "mean": np.nanmean,
    "min": np.nanmin,
    "max": np.nanmax,
}
# Reducao "so sobre o eixo do tempo" (axis=0), mantendo o restante da forma
# (celulas, e/ou niveis, conforme o modo - ver '_fatia') - usada pela forma
# espacial ('d sum|mean|min|max|p10..p90 ...').
_OPERACOES_EIXO = {
    "sum": lambda d: np.nansum(d, axis=0),
    "mean": lambda d: np.nanmean(d, axis=0),
    "min": lambda d: np.nanmin(d, axis=0),
    "max": lambda d: np.nanmax(d, axis=0),
}
for _p in range(10, 91, 10):
    _NOMES_FUNCAO["p{0}".format(_p)] = "Percentil {0}".format(_p)
    _OPERACOES["p{0}".format(_p)] = (lambda q: (lambda d: np.nanpercentile(d, q)))(_p)
    _OPERACOES_EIXO["p{0}".format(_p)] = (lambda q: (lambda d: np.nanpercentile(d, q, axis=0)))(_p)
del _p

# Nomes de comando reconhecidos por exec_func.py: todos tem a forma escalar
# ('<nome> all|inlimits|point <variavel>') e a forma espacial ('d <nome>
# all|inlimits|point <variavel>').
NOMES_ESTATISTICA_ESCALAR = tuple(_NOMES_FUNCAO.keys())
NOMES_ESTATISTICA_ESPACIAL = tuple(_OPERACOES_EIXO.keys())


def _descricao_nivel(setup):
    """
    Texto curto descrevendo o NIVEL UNICO atualmente selecionado
    (setup['lev']) - usado nas mensagens do modo 'mapa' (a estatistica so
    olha para um nivel de cada vez): pressao em hPa, se disponivel
    (setup['eixo_pressao']), senao so o indice.
    """
    lev = setup["lev"]
    levels = setup.get("levels")
    if setup.get("eixo_pressao") and levels is not None and 0 <= lev < len(levels):
        return "nivel {0} = {1:.1f} hPa".format(lev, levels[lev])
    return "nivel {0}".format(lev)


def _descricao_intervalo_niveis(setup):
    """
    Texto curto descrevendo a FAIXA de niveis atualmente selecionada
    (setup['lev']:setup['levf']) - usado nas mensagens dos modos 'ponto'
    (perfil vertical), 'corte' (corte vertical) e 'mapa_niveis' (mapa com
    faixa de niveis, complemento 'point'), onde a estatistica roda sobre
    varios niveis de uma vez, diferente do modo 'mapa' simples (um so
    nivel - ver '_descricao_nivel').
    """
    lev = setup["lev"]
    levf = setup["levf"]
    levels = setup.get("levels")
    ultimo = max(lev, levf - 1)
    if setup.get("eixo_pressao") and levels is not None and 0 <= lev < len(levels) and 0 <= ultimo < len(levels):
        return "niveis {0}-{1} ({2:.1f}-{3:.1f} hPa)".format(lev, ultimo, levels[lev], levels[ultimo])
    return "niveis {0}-{1}".format(lev, ultimo)


def _modo_espacial(setup):
    """
    Decide, a partir da selecao atual de lat/lon (setup['lat_min']/
    ['lat_max']/['lon_min']/['lon_max']), o mesmo modo que 'd'/'d3'
    usariam para plotar uma variavel 3D agora mesmo (secao 8 do manual):
    'ponto' (perfil vertical - lat e lon fixadas no mesmo valor), 'corte'
    (corte vertical - so uma das duas fixa) ou 'mapa' (mapa horizontal -
    nenhuma das duas fixa).
    """
    lat_min = setup["lat_min"]
    lat_max = setup["lat_max"]
    lon_min = setup["lon_min"]
    lon_max = setup["lon_max"]
    if (lat_min == lat_max) and (lon_min == lon_max):
        return "ponto"
    if (lat_min == lat_max) != (lon_min == lon_max):
        return "corte"
    return "mapa"


def _indice_mais_proximo(setup):
    """
    Indice da celula da malha mais proxima do ponto de lat/lon
    selecionado (setup['lat_min']/['lon_min']) - a mesma celula que
    'plot_perfil' usaria (ver plot_func.py); determinista, dado o mesmo
    'setup', entao pode ser recalculado de forma independente por quem
    for plotar o resultado (plot_estatistica_campo).
    """
    lat = np.asarray(setup["latitudes"])
    lon = np.asarray(setup["longitudes"])
    dist = np.sqrt((lat - setup["lat_min"]) ** 2 + (lon - setup["lon_min"]) ** 2)
    return int(np.argmin(dist))


def _fatia(setup, var, rotulo, modo_point=False):
    """
    Extrai, de UM array de variavel (um arquivo/tempo), a fatia usada
    para a estatistica, conforme a selecao atual de lat/lon/nivel (ver
    '_modo_espacial'):

      - Variavel 2D (sem nivel): sempre 'var[time_sel, :]' - (nCells,); a
        selecao de ponto/corte/nivel nao se aplica (mesma regra do 'd'/
        'd3' - so faz sentido para variaveis com nivel).
      - Variavel 3D, modo 'ponto': 'var[time_sel, indice_mais_proximo,
        lev:levf_efetivo]' - (nLevels,), perfil vertical na celula mais
        proxima (um so nivel se nao houver faixa definida).
      - Variavel 3D, modo 'corte': 'var[time_sel, :, lev:levf_efetivo]' -
        (nCells, nLevels), a faixa de niveis (ou nivel unico), em todas
        as celulas.
      - Variavel 3D, modo 'mapa', SEM o complemento 'point' (modo_point=
        False - comportamento classico, 'all'/'inlimits'): 'var[time_sel,
        :, lev]' - (nCells,), so o nivel unico selecionado.
      - Variavel 3D, modo 'mapa', COM o complemento 'point' (modo_point=
        True) e uma FAIXA genuina de niveis selecionada: 'var[time_sel,
        :, lev:levf_efetivo]' - (nCells, nLevels); modo interno retornado
        vira 'mapa_niveis' (nem lat nem lon fixada, mas ha eixo de
        niveis) em vez de 'mapa'. Sem faixa genuina (nivel unico), o
        complemento 'point' se comporta como o modo 'mapa' normal.

    Retorna (dados, modo, indice_mais_proximo) - 'indice_mais_proximo' so
    e diferente de None no modo 'ponto' - ou (None, None, None) com uma
    mensagem de erro ja impressa, se o numero de celulas nao bater com o
    da malha aberta.
    """
    time_sel = setup["time_sel"]
    n_malha = len(setup["longitudes"])

    # 'set t <n>' (indice de tempo DENTRO do arquivo, secao 6 do manual) -
    # com varios arquivos abertos (cada um tipicamente com 1 unico
    # horario, saida MONAN/MPAS), um indice fora do intervalo derrubava o
    # programa com um IndexError cru do numpy (mesmo problema corrigido
    # em plot_func.py/_tempo_valido, para 'd'/'d3'; aqui cobre 'sum'/
    # 'mean'/etc. e o 'd sum|mean|...' espacial, que passam pela mesma
    # '_fatia').
    n_tempos = var.shape[0]
    if time_sel < 0 or time_sel >= n_tempos:
        if n_tempos == 1:
            print("Erro: 'set t {0}' invalido para '{1}' - este arquivo tem um unico horario (indice 0).".format(time_sel, rotulo))
        else:
            print("Erro: 'set t {0}' invalido para '{1}' - indices de tempo validos neste arquivo: 0 a {2}.".format(time_sel, rotulo, n_tempos-1))
        print("Para escolher outro ARQUIVO entre os varios abertos, use o sufixo '.N' na variavel (ex: '{0}.8'), ou 'set t <arquivo_inicial> <arquivo_final>' para uma serie/animacao entre arquivos.".format(rotulo))
        return None, None, None

    if len(var.shape) == 2:
        dados = sem_mascara(var[time_sel, :])
        if len(dados) != n_malha:
            print("Erro: a variavel '{0}' tem {1} ponto(s), mas a malha aberta tem {2} ponto(s).".format(
                rotulo, len(dados), n_malha))
            return None, None, None
        return dados, "mapa", None

    lev = setup["lev"]
    levf = setup["levf"]
    levf_ok = _levf_efetivo(lev, levf)
    modo = _modo_espacial(setup)

    if modo == "ponto":
        indice = _indice_mais_proximo(setup)
        dados = sem_mascara(var[time_sel, indice, lev:levf_ok])
        return dados, "ponto", indice

    if modo == "corte":
        dados = sem_mascara(var[time_sel, :, lev:levf_ok])
        if dados.shape[0] != n_malha:
            print("Erro: a variavel '{0}' tem {1} celula(s), mas a malha aberta tem {2} ponto(s).".format(
                rotulo, dados.shape[0], n_malha))
            return None, None, None
        return dados, "corte", None

    # modo == "mapa": com o complemento 'point' e uma faixa genuina de
    # niveis, reduz tambem sobre os niveis (modo interno 'mapa_niveis');
    # caso contrario, comportamento classico (um so nivel).
    if modo_point and levf_ok > lev + 1:
        dados = sem_mascara(var[time_sel, :, lev:levf_ok])
        if dados.shape[0] != n_malha:
            print("Erro: a variavel '{0}' tem {1} celula(s), mas a malha aberta tem {2} ponto(s).".format(
                rotulo, dados.shape[0], n_malha))
            return None, None, None
        return dados, "mapa_niveis", None

    dados = sem_mascara(var[time_sel, :, lev])
    if len(dados) != n_malha:
        print("Erro: a variavel '{0}' tem {1} ponto(s), mas a malha aberta tem {2} ponto(s).".format(
            rotulo, len(dados), n_malha))
        return None, None, None
    return dados, "mapa", None


def _empilhar(setup, arrays, rotulo, modo_point=False):
    """
    Fatia (ver '_fatia') CADA array bruto da lista 'arrays' (um por
    arquivo/tempo selecionado - ver '_dados_estatistica' em
    exec_func.py) e empilha o resultado numa matriz com um EIXO A MAIS na
    frente (o dos "tempos"): (n_tempos, nCells) no modo 'mapa',
    (n_tempos, nCells, nLevels) nos modos 'corte'/'mapa_niveis', ou
    (n_tempos, nLevels) no modo 'ponto'.

    Retorna (matriz, modo, indice_mais_proximo), ou (None, None, None) em
    caso de erro (mensagem ja impressa por '_fatia').
    """
    fatias = []
    modo_final = None
    indice_final = None
    for var in arrays:
        fatia, modo, indice = _fatia(setup, var, rotulo, modo_point=modo_point)
        if fatia is None:
            return None, None, None
        if modo_final is None:
            modo_final, indice_final = modo, indice
        fatias.append(fatia)
    return np.stack(fatias, axis=0), modo_final, indice_final


def _preparar_mascara(mask, n_cells, rotulo_erro="a variavel"):
    """
    Confere se 'mask' (setup['limits_mask']) bate com o numero de celulas
    da matriz empilhada; imprime erro (e retorna False) se nao bater -
    ex: apos um 'reinit' com outra malha, sem recarregar 'load limits'.
    """
    if len(mask) != n_cells:
        print("Erro: a mascara de limites tem {0} celula(s), mas {1} tem {2} - "
              "a malha pode ter mudado desde o 'load limits'. Recarregue os limites.".format(
                  len(mask), rotulo_erro, n_cells))
        return False
    return True


def calcular_valor(setup, nome_funcao, arrays, mask, rotulo, modo_point=False):
    """
    Forma ESCALAR das estatisticas: 'sum'/'mean'/'min'/'max'/'p10'..'p90'
    'all'/'inlimits'/'point' <variavel> (secao 2.3 do manual). Reduz
    'arrays' (ver '_empilhar') a UM UNICO NUMERO - sobre todos os tempos
    selecionados e:
      - modo 'mapa': todas as celulas (mask=None) ou so as de dentro da
        area de limites (mask=setup['limits_mask']), no nivel unico.
      - modo 'corte'/'mapa_niveis': idem, mas sobre a FAIXA de niveis
        selecionada (o segundo so ocorre com o complemento 'point').
      - modo 'ponto': sobre a faixa de niveis selecionada, na celula mais
        proxima do ponto; 'mask' so verifica se esse ponto cai dentro da
        area de limites (nao ha mais celulas para restringir).

    'modo_point' (True para o complemento 'point') so muda a FATIA usada
    (ver '_fatia'/'_empilhar') - permitindo o modo 'mapa_niveis' -, nao a
    forma de reducao em si.

    Imprime o resultado antes do proximo prompt e o retorna (float), ou
    None (com mensagem de erro/aviso ja impressa) se a variavel nao tiver
    o formato esperado, a mascara nao bater com a malha atual, ou nao
    sobrar nenhum dado para calcular.
    """
    matriz, modo, indice = _empilhar(setup, arrays, rotulo, modo_point=modo_point)
    if matriz is None:
        return None

    n_tempos = matriz.shape[0]

    if modo == "ponto":
        if mask is not None and not (0 <= indice < len(mask) and mask[indice]):
            print("Aviso: o ponto selecionado (lat {0:g}, lon {1:g}) esta fora da area de limites carregada - nada para calcular.".format(
                setup["lat_min"], setup["lon_min"]))
            return None
        if matriz.size == 0:
            print("Aviso: nenhum nivel disponivel para calcular a estatistica (verifique 'set lev <ini> <fim>').")
            return None
        resultado = float(_OPERACOES[nome_funcao](matriz))
        partes = ["ponto lat {0:g}, lon {1:g}".format(setup["lat_min"], setup["lon_min"])]
        if n_tempos > 1:
            partes.append("{0} tempo(s)".format(n_tempos))
        partes.append(_descricao_intervalo_niveis(setup))
        print("{0} de '{1}' ({2}): {3}".format(_NOMES_FUNCAO[nome_funcao], rotulo, ", ".join(partes), resultado))
        return resultado

    # modo 'mapa', 'corte' ou 'mapa_niveis': ha um eixo de celulas (axis=1)
    # sobre o qual 'inlimits' restringe - a diferenca entre eles e so a
    # descricao do nivel (unico vs. faixa) na mensagem final.
    if mask is not None:
        if not _preparar_mascara(mask, matriz.shape[1], "a variavel"):
            return None
        dados = matriz[:, mask]
        n_cel = int(mask.sum())
    else:
        dados = matriz
        n_cel = matriz.shape[1]

    if n_cel == 0 or dados.size == 0:
        print("Aviso: nenhuma celula disponivel para calcular a estatistica "
              "(area de limites vazia) - nada para calcular.")
        return None

    resultado = float(_OPERACOES[nome_funcao](dados))

    partes = ["dentro dos limites, {0} celula(s)".format(n_cel) if mask is not None
              else "todos os {0} ponto(s) da malha".format(n_cel)]
    if n_tempos > 1:
        partes.append("{0} tempo(s)".format(n_tempos))
    if modo in ("corte", "mapa_niveis"):
        partes.append(_descricao_intervalo_niveis(setup))
    elif len(arrays[0].shape) == 3:
        partes.append(_descricao_nivel(setup))

    print("{0} de '{1}' ({2}): {3}".format(_NOMES_FUNCAO[nome_funcao], rotulo, ", ".join(partes), resultado))
    return resultado


def calcular_campo(setup, nome_funcao, arrays, mask, rotulo, modo_point=False):
    """
    Forma ESPACIAL das estatisticas: 'd sum|mean|min|max|p10..p90
    all|inlimits|point <variavel>' (secao 2.3 do manual). Reduz 'arrays'
    (ver '_empilhar') SO sobre os arquivos/tempos selecionados (e, no
    complemento 'point' em modo 'mapa_niveis', tambem sobre os niveis),
    mantendo o restante da forma - pronto para plotar exatamente como
    'd'/'d3' plotariam a variavel agora (mapa/perfil/corte - ver
    'plot_estatistica_campo' em plot_func.py):
      - modo 'mapa': (nCells,) - um valor por celula, no nivel unico.
      - modo 'corte': (nCells, nLevels) - todas as celulas, na faixa de
        niveis selecionada.
      - modo 'ponto': (nLevels,) - perfil vertical na celula mais
        proxima.
      - modo 'mapa_niveis' (so com 'point', nem lat nem lon fixada e uma
        faixa genuina de niveis selecionada): (nCells, nLevels) - mas SEM
        lat/lon fixada nao ha um mapa nem um corte bem definido para
        plotar essa forma, entao esta funcao recusa (imprime aviso e
        retorna None) em vez de arriscar um grafico incorreto; use a
        forma escalar, ou fixe 'set lat'/'set lon' (ponto ou corte).

    Com 'mask' informada (forma 'inlimits'): nos modos 'mapa'/'corte', as
    celulas de FORA da area ficam com NaN (nao aparecem no mapa/corte,
    igual a um 'set cut'); no modo 'ponto', so verifica se o ponto
    selecionado cai dentro da area (nao ha mais celulas para mascarar).

    Retorna (campo, modo), ou None (com mensagem de erro/aviso ja
    impressa) se a variavel nao tiver o formato esperado, a mascara nao
    bater com a malha atual, (no modo 'ponto') o ponto selecionado
    estiver fora da area de limites, ou (no modo 'mapa_niveis') nao
    houver como plotar.
    """
    matriz, modo, indice = _empilhar(setup, arrays, rotulo, modo_point=modo_point)
    if matriz is None:
        return None

    if modo == "mapa_niveis":
        print("Aviso: nao e possivel plotar a estatistica espacial com uma faixa de "
              "niveis sem fixar latitude e/ou longitude (perfil ou corte) - use a "
              "forma escalar ('{0} point <variavel>'), ou fixe 'set lat'/'set lon' "
              "num unico ponto (perfil) ou so um dos dois (corte).".format(nome_funcao))
        return None

    campo = np.asarray(_OPERACOES_EIXO[nome_funcao](matriz), dtype=float)

    if modo == "ponto":
        if mask is not None and not (0 <= indice < len(mask) and mask[indice]):
            print("Aviso: o ponto selecionado (lat {0:g}, lon {1:g}) esta fora da area de limites carregada - nada para plotar.".format(
                setup["lat_min"], setup["lon_min"]))
            return None
        return campo, modo

    if mask is not None:
        if not _preparar_mascara(mask, campo.shape[0], "a variavel"):
            return None
        campo = campo.copy()
        campo[~mask] = np.nan

    return campo, modo


# ---------------------------------------------------------------------------
# Atalhos nomeados (opcionais): equivalentes a 'calcular_valor'/'calcular_
# campo' com o nome da funcao ja fixado - uteis para chamar diretamente
# (ex: em testes) sem repetir a string do nome.
# ---------------------------------------------------------------------------
def sum_all(setup, arrays, rotulo):
    """Equivalente ao comando 'sum all <variavel>' (ver 'calcular_valor')."""
    return calcular_valor(setup, "sum", arrays, None, rotulo)


def sum_inlimits(setup, arrays, mask, rotulo):
    """Equivalente ao comando 'sum inlimits <variavel>' (ver 'calcular_valor')."""
    return calcular_valor(setup, "sum", arrays, mask, rotulo)


def mean_all(setup, arrays, rotulo):
    """Equivalente ao comando 'mean all <variavel>' (ver 'calcular_valor')."""
    return calcular_valor(setup, "mean", arrays, None, rotulo)


def mean_inlimits(setup, arrays, mask, rotulo):
    """Equivalente ao comando 'mean inlimits <variavel>' (ver 'calcular_valor')."""
    return calcular_valor(setup, "mean", arrays, mask, rotulo)
