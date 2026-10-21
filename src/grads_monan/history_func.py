"""
Historico de comandos (secao 2.9 do manual): 'show commands', 'exec <ini>
[<fin>]', 'history backup <arquivo>' e 'history clean'.

O historico e o arquivo ~/.config/grads_monan/grads_monan.history (um
comando por linha, gravado por cli.py a cada comando dado). Linhas em
branco sao ignoradas: a numeracao (1, 2, 3...) e a de 'show commands' e a
de 'exec' e sempre a mesma - a das linhas NAO vazias do arquivo.

Este modulo nao importa nada do resto do pacote (e usa 'tkinter' so dentro
da janela, que roda em um processo proprio - ver 'abrir_janela').
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

_RE_BACKUP = re.compile(r"^history_backup(\d+)$")


def diretorio_config():
    return os.path.join(os.path.expanduser("~"), ".config", "grads_monan")


def arquivo_historico():
    return os.path.join(diretorio_config(), "grads_monan.history")


def ler_historico(caminho=None):
    """Lista de comandos (linhas nao vazias do arquivo de historico)."""
    caminho = caminho or arquivo_historico()
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8", errors="replace") as f:
        return [l.strip() for l in f if l.strip()]


def texto_numerado(linhas):
    """'  1  comando' - numeros alinhados a direita, de 1 ate o fim."""
    larg = len(str(len(linhas)))
    return "\n".join("{0:>{w}}  {1}".format(i, c, w=larg) for i, c in enumerate(linhas, 1))


# --- exec <ini> [<fin>] -------------------------------------------------------
def eh_exec_historico(cmd_split):
    """True para 'exec <n>' ou 'exec <n> <m>' com numeros inteiros nao
    negativos; qualquer outra forma de 'exec' continua sendo o comando de
    shell (secao 2.1)."""
    return (cmd_split[0] == "exec" and 2 <= len(cmd_split) <= 3
            and all(a.isdigit() for a in cmd_split[1:]))


def intervalo_exec(cmd_split, total):
    """(ini, fin) validado contra o total de comandos, ou None (ja imprimiu o erro)."""
    ini = int(cmd_split[1])
    fin = int(cmd_split[2]) if len(cmd_split) == 3 else ini
    if total == 0:
        print("Erro: o historico esta vazio.")
        return None
    if ini < 1 or fin < 1 or ini > total or fin > total:
        print("Erro: os numeros de comando vao de 1 a {0} (use 'show commands').".format(total))
        return None
    if ini > fin:
        print("Erro: o comando inicial ({0}) nao pode ser maior que o final ({1}).".format(ini, fin))
        return None
    return ini, fin


def motivo_pular(linha):
    """Texto do motivo se a linha do historico nao deve ser reexecutada por
    'exec' (evita recursao e efeitos colaterais), senao None."""
    t = linha.split()
    if not t:
        return "linha vazia"
    if eh_exec_historico(t):
        return "'exec <n>' nao e reexecutado"
    if t[0] == "history":
        return "'history' nao e reexecutado"
    if t[0] == "show" and len(t) > 1 and t[1] == "commands":
        return "'show commands' nao e reexecutado"
    if t[0] in ("q", "exit", "quit"):
        return "nao encerra o programa"
    return None


# --- history backup / history clean -------------------------------------------
def _destino_backup(nome):
    nome = os.path.expanduser(nome.strip().strip('"').strip("'"))
    if os.path.isabs(nome) or os.sep in nome or (os.altsep and os.altsep in nome):
        return nome
    return os.path.join(diretorio_config(), nome)


def proximo_backup():
    """Caminho de history_backup<n>, n = (maior n existente no diretorio) + 1."""
    base = diretorio_config()
    maior = 0
    if os.path.isdir(base):
        for nome in os.listdir(base):
            m = _RE_BACKUP.match(nome)
            if m:
                maior = max(maior, int(m.group(1)))
    return os.path.join(base, "history_backup{0}".format(maior + 1))


def cmd_history(cmd_split):
    uso = "Uso: history backup <arquivo>  |  history clean"
    if len(cmd_split) < 2:
        print(uso)
        return
    sub = cmd_split[1].lower()
    hist = arquivo_historico()
    if sub == "backup":
        if len(cmd_split) != 3:
            print("Uso: history backup <arquivo>")
            return
        linhas = ler_historico(hist)
        if not linhas:
            print("Historico vazio; nada a salvar.")
            return
        destino = _destino_backup(cmd_split[2])
        if os.path.exists(destino):
            print("Erro: '{0}' ja existe; escolha outro nome.".format(destino))
            return
        try:
            os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
            shutil.copyfile(hist, destino)
        except OSError as e:
            print("Erro ao salvar o historico em '{0}': {1}".format(destino, e))
            return
        print("Historico salvo em '{0}' ({1} comandos).".format(destino, len(linhas)))
    elif sub == "clean":
        if len(cmd_split) != 2:
            print("Uso: history clean")
            return
        linhas = ler_historico(hist)
        if not linhas:
            print("Historico ja esta vazio.")
            return
        destino = proximo_backup()
        try:
            shutil.copyfile(hist, destino)
            open(hist, "w").close()
        except OSError as e:
            print("Erro ao limpar o historico: {0}".format(e))
            return
        try:                                  # tambem esquece as setas do readline
            import readline
            readline.clear_history()
        except Exception:
            pass
        print("Historico salvo em '{0}' ({1} comandos) e limpo.".format(destino, len(linhas)))
    else:
        print(uso)


# --- show commands --------------------------------------------------------------
def _tem_display():
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def abrir_janela(texto):
    """Abre a janela editavel (processo separado, para nao interferir no
    loop de eventos do matplotlib e deixar o prompt livre). Devolve True se a
    janela abriu; False se faltou tkinter/display ou o processo falhou."""
    if importlib.util.find_spec("tkinter") is None or not _tem_display():
        return False
    fd, tmp = tempfile.mkstemp(prefix="grads_monan_hist_", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(texto)
    kw = {"start_new_session": True} if os.name == "posix" else {}
    try:
        proc = subprocess.Popen([sys.executable, "-m", "grads_monan.history_func", tmp],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    except OSError:
        os.unlink(tmp)
        return False
    try:
        rc = proc.wait(timeout=0.8)           # ainda rodando = janela aberta
    except subprocess.TimeoutExpired:
        return True
    if rc != 0 and os.path.exists(tmp):
        os.unlink(tmp)
    return rc == 0


def cmd_show_commands():
    linhas = ler_historico()
    if not linhas:
        print("Historico vazio.")
        return
    texto = texto_numerado(linhas)
    if abrir_janela(texto):
        print("Janela do historico aberta ({0} comandos). Use 'exec <ini> [<fin>]' para reexecutar.".format(len(linhas)))
    else:
        print("Nao foi possivel abrir a janela (tkinter/display indisponivel); historico no terminal:")
        print(texto)


def _main_janela(arquivo):
    import tkinter as tk
    with open(arquivo, "r", encoding="utf-8") as f:
        texto = f.read()
    try:
        os.unlink(arquivo)
    except OSError:
        pass
    root = tk.Tk()
    root.title("GradsMonanApp - Command history")
    root.geometry("760x520")
    quadro = tk.Frame(root)
    quadro.pack(fill="both", expand=True)
    barra = tk.Scrollbar(quadro)
    barra.pack(side="right", fill="y")
    txt = tk.Text(quadro, wrap="word", undo=True, font="TkFixedFont", yscrollcommand=barra.set)
    txt.pack(side="left", fill="both", expand=True)
    barra.config(command=txt.yview)
    txt.insert("1.0", texto)
    txt.mark_set("insert", "end-1c")          # cursor no fim do ultimo comando
    txt.see("insert")
    txt.focus_set()
    rodape = tk.Frame(root)
    rodape.pack(fill="x")
    tk.Button(rodape, text="Close", command=root.destroy).pack(side="right", padx=8, pady=6)
    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()


if __name__ == "__main__":
    _main_janela(sys.argv[1])
