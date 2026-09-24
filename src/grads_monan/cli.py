#!/usr/bin/python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# Created Date: 13Jun2025
# ---------------------------------------------------------------------------
""" Ponto de entrada do GRADS-MONAN APP (comando 'grads-monan'). """
# ---------------------------------------------------------------------------
import os
import toml
import matplotlib.pyplot as plt

from .utils import custom_input, load_history, save_command_to_history
from .exec_func import exec_cmd
from .setup_config import ensure_config


def main():
    print("")
    print("+----------------------------------------------------+")
    print("|                  GRADS-MONAN APP                   |")
    print("|        (a Grads/Cola clone for MONAN Model)        |")
    print("| Author: Luiz Flávio Rodrigues : luflarois@pm.me    |")
    print("| Revision: 0.3.0                                    |")
    print("| Licence: \U0001F12F GPLv3 \U0001F12F                                 |")
    print("+----------------------------------------------------+\n")

    # Cria ~/.config/grads_monan/ e o grads_monan.toml automaticamente na
    # primeira execucao - o usuario nao precisa mais rodar nenhum script de
    # instalacao separado antes de usar o programa.
    base_dir = ensure_config()

    history_file = os.path.join(base_dir, "grads_monan.history")
    setup_toml = toml.load(os.path.join(base_dir, "grads_monan.toml"))

    setup = {"openFile": False}
    dataset = {}
    ax = 0
    cbar = 0

    load_history(history_file)

    while True:
        cmd_user = custom_input()
        cmd_split = cmd_user.split()
        try:
            cmd = cmd_split[0]
        except IndexError:
            continue
        setup, dataset, ax, cbar = exec_cmd(cmd_user, cmd, cmd_split, setup, dataset, ax, cbar, setup_toml)
        save_command_to_history(cmd_user, history_file)
        # Forca o redesenho/atualizacao da janela: algumas funcoes de plotagem
        # usam metodos do eixo (ax.contourf, ax.tricontourf, etc.) em vez das
        # funcoes de nivel 'pyplot' (plt.contourf), e essas nao disparam o
        # redesenho automatico do modo interativo (plt.ion()) sozinhas.
        plt.draw()
        plt.pause(0.001)


if __name__ == "__main__":
    main()
