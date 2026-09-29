#!/usr/bin/python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Rodrigues, L.F [LFR]
# Created Date: 13Jun2025
# ---------------------------------------------------------------------------
""" Ponto de entrada do GRADS-MONAN APP (comando 'grads-monan'). """
# ---------------------------------------------------------------------------
import os
import sys
import io
import toml
import matplotlib.pyplot as plt

from .utils import custom_input, load_history, save_command_to_history
from .exec_func import exec_cmd
from .setup_config import ensure_config
from .estatistics import NOMES_ESTATISTICA_ESCALAR

# Todo comando de PRIMEIRO NIVEL reconhecido pelo programa (o primeiro
# token da linha) - usado so para decidir o prompt da PROXIMA linha
# (secao 1 do manual: '> '/'E> '/'?> ') e NAO para decidir o que
# 'exec_cmd' de fato executa (que continua sendo a unica fonte de verdade
# sobre o que cada comando faz) - mantido em sincronia manualmente com a
# cadeia de 'if'/'elif' de 'exec_cmd' (exec_func.py).
_COMANDOS_CONHECIDOS = {
    "!", "exec", "q", "exit", "quit", "run", "open", "reinit",
    "gxprint", "show", "c", "reset", "load", "set", "draw", "d3", "display", "d",
} | set(NOMES_ESTATISTICA_ESCALAR)

# Marcadores de texto (secao 1 do manual) usados para reconhecer, na saida
# impressa por 'exec_cmd', que o comando (reconhecido no primeiro token)
# ainda assim falhou ao executar - mesmo prefixo/convencao ja usado em
# todo o programa para mensagens de erro/uso incorreto (ver set_func.py,
# exec_func.py, files.py, estatistics.py, plot_func.py). 'Aviso:' e
# deliberadamente EXCLUIDO desta lista - e usado para notas informativas
# que nao impedem o comando de ter funcionado (ex: abrir um arquivo sem
# 'xtime').
_MARCADORES_ERRO = ("Erro:", "Erro ao ", "Falha ")
_MARCADOR_DESCONHECIDO = "Command not recognized!"


class _TeeStdout:
    """
    Encaminha toda escrita para o stdout real (o usuario continua vendo a
    saida do comando na hora, normalmente) e, ao mesmo tempo, guarda uma
    copia em memoria - usada so para decidir, DEPOIS que o comando
    terminou, se ele imprimiu algum marcador de erro (ver
    '_status_comando'), sem esconder nada do usuario nem exigir mudar
    nenhuma mensagem existente.
    """
    def __init__(self, stdout_real):
        self._stdout_real = stdout_real
        self._capturado = []

    def write(self, texto):
        self._stdout_real.write(texto)
        self._capturado.append(texto)

    def flush(self):
        self._stdout_real.flush()

    def getvalue(self):
        return "".join(self._capturado)


def _status_comando(texto_impresso):
    """
    Classifica a saida impressa por um comando reconhecido (ver
    '_executar_com_status') em 'ok', 'erro' ou 'desconhecido' - usado
    para escolher o prompt da proxima linha (secao 1 do manual). Um
    sub-comando nao reconhecido (ex: 'set xyz', que imprime 'Command not
    recognized!') conta como 'desconhecido', nao 'erro' - mesmo com o
    comando de primeiro nivel ('set') reconhecido.
    """
    if _MARCADOR_DESCONHECIDO in texto_impresso:
        return "desconhecido"
    if any(marcador in texto_impresso for marcador in _MARCADORES_ERRO):
        return "erro"
    return "ok"


def _executar_com_status(cmd_user, cmd, cmd_split, setup, dataset, ax, cbar, setup_toml):
    """
    Executa 'exec_cmd' normalmente (o usuario ve a saida em tempo real,
    igual a antes), mas tambem guarda uma copia dela para decidir o
    status do comando (ver '_status_comando') - e, alem disso, protege o
    loop principal contra uma excecao nao tratada em algum comando
    (qualquer bug futuro num comando especifico nao devia derrubar a
    sessao inteira; 'q'/'exit'/'quit', que terminam o programa de
    proposito via 'sys.exit()', continuam funcionando normalmente).
    Retorna (setup, dataset, ax, cbar, status).
    """
    stdout_real = sys.stdout
    tee = _TeeStdout(stdout_real)
    try:
        sys.stdout = tee
        try:
            setup, dataset, ax, cbar = exec_cmd(cmd_user, cmd, cmd_split, setup, dataset, ax, cbar, setup_toml)
        except SystemExit:
            raise
        except Exception as e:
            sys.stdout = stdout_real
            print("Erro: falha inesperada ao executar '{0}': {1}".format(cmd_user, e))
            return setup, dataset, ax, cbar, "erro"
    finally:
        sys.stdout = stdout_real

    return setup, dataset, ax, cbar, _status_comando(tee.getvalue())


_PROMPT_POR_STATUS = {"ok": "> ", "erro": "E> ", "desconhecido": "?> "}


def main():
    print("")
    print("+----------------------------------------------------+")
    print("|                  GRADS-MONAN APP                   |")
    print("|        (a Grads/Cola clone for MONAN Model)        |")
    print("| Author: Luiz Flávio Rodrigues : luflarois@pm.me    |")
    print("| Revision: 0.1.0                                    |")
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

    # Prompt da PROXIMA linha (secao 1 do manual): '> ' (comando anterior
    # reconhecido e executado sem erro - tambem o valor inicial, antes de
    # qualquer comando), 'E> ' (comando anterior reconhecido, mas a
    # execucao falhou) ou '?> ' (comando/sub-comando anterior nao
    # reconhecido).
    prompt_atual = "> "

    while True:
        cmd_user = custom_input(prompt_atual)
        cmd_split = cmd_user.split()
        try:
            cmd = cmd_split[0]
        except IndexError:
            continue

        if cmd not in _COMANDOS_CONHECIDOS:
            print("Comando nao reconhecido: '{0}'.".format(cmd))
            prompt_atual = "?> "
            save_command_to_history(cmd_user, history_file)
            continue

        setup, dataset, ax, cbar, status = _executar_com_status(
            cmd_user, cmd, cmd_split, setup, dataset, ax, cbar, setup_toml)
        prompt_atual = _PROMPT_POR_STATUS[status]
        save_command_to_history(cmd_user, history_file)
        # Forca o redesenho/atualizacao da janela: algumas funcoes de plotagem
        # usam metodos do eixo (ax.contourf, ax.tricontourf, etc.) em vez das
        # funcoes de nivel 'pyplot' (plt.contourf), e essas nao disparam o
        # redesenho automatico do modo interativo (plt.ion()) sozinhas.
        plt.draw()
        plt.pause(0.001)


if __name__ == "__main__":
    main()
