#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Inicializacao da configuracao do grads_monan (~/.config/grads_monan/).

Antes, isso era um script separado (install.py) que o usuario precisava
lembrar de rodar manualmente uma vez. Agora e chamado automaticamente pelo
'grads-monan' (cli.py) sempre que a pasta de configuracao nao existir, e
tambem pode ser rodado manualmente com o comando 'grads-monan-setup'.
"""
import os
import shutil
import glob
import toml

try:
    from importlib.resources import files as _pkg_files  # Python >= 3.9
except ImportError:  # pragma: no cover
    _pkg_files = None

DEFAULT_SETUP = {
    "xmark": [], "ymark": [], "colormark": [], "sizemark": [], "legend": [],
    "lev": 0, "levf": 0, "gxout": "contour", "title": "", "label": "",
    "map": "Continents.shp",
    "map_color": "black", "map_line": 0.1, "cmap": "jet", "lw": 0.2,
    "lc": "black", "clevs": [], "lat_min": -90.0,
    "lat_max": +90.0, "lon_min": -180.0,
    "lon_max": +180.0, "time_sel": 0, "levels": [],
    "latitudes": [], "longitudes": [],
    "time": 0, "time_variable": 0, "time_units": 0,
    "time_str": 0, "DataDado": 0, "openFile": False, "variables": [],
    "fig_dpi": 300, "fig_inches": "tight", "fig_transparency": False,
    "label_fontsize": 12, "label_fontweight": "normal",
    "title_color": "black", "title_fs": 12, "title_fw": "normal",
}


def _copiar_shapefiles(base_dir):
    """
    Copia os shapefiles de mapa (Continents.*) para a pasta de config.
    Procura primeiro nos dados empacotados junto com o programa
    (grads_monan/data/); se nao encontrar nada la, tenta o diretorio atual
    (compatibilidade com quem roda direto dos fontes, sem instalar).
    """
    candidatos = []

    if _pkg_files is not None:
        try:
            pacote_data = _pkg_files("grads_monan").joinpath("data")
            candidatos.append(str(pacote_data))
        except Exception:
            pass

    candidatos.append(os.getcwd())

    for origem in candidatos:
        arquivos = glob.glob(os.path.join(origem, "Continents.*"))
        if arquivos:
            for f in arquivos:
                shutil.copy(f, base_dir)
            return True

    print("Aviso: shapefiles 'Continents.*' nao encontrados (nem nos dados "
          "do pacote, nem no diretorio atual). O mapa de fundo ('draw map') "
          "nao funcionara ate que voce copie esses arquivos manualmente para "
          + base_dir)
    return False


def ensure_config(force=False):
    """
    Garante que ~/.config/grads_monan/ existe, com o historico de comandos
    e o grads_monan.toml (com valores padrao) prontos para uso.
    Se force=True, recria o grads_monan.toml mesmo que ja exista.
    """
    home_dir = os.path.expanduser("~")
    base_dir = os.path.join(home_dir, ".config", "grads_monan")

    novo = not os.path.exists(base_dir)
    os.makedirs(base_dir, exist_ok=True)

    if novo:
        _copiar_shapefiles(base_dir)

    history_file = os.path.join(base_dir, "grads_monan.history")
    if not os.path.exists(history_file):
        open(history_file, "a").close()

    toml_file = os.path.join(base_dir, "grads_monan.toml")
    if force or not os.path.exists(toml_file):
        setup = dict(DEFAULT_SETUP)
        setup["mappath"] = base_dir + os.sep
        with open(toml_file, "w") as f:
            f.write(toml.dumps(setup))
            f.write("\n")
        print("Configuracao criada em: " + toml_file)

    return base_dir


def main():
    """Ponto de entrada do comando 'grads-monan-setup' (reinicializa a config)."""
    base_dir = ensure_config(force=True)
    print("Pronto! Configuracao do grads_monan em: " + base_dir)


if __name__ == "__main__":
    main()
