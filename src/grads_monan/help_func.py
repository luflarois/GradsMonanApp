#!/usr/bin/python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Comando 'help' do GradsMonanApp: lista sucinta de todos os comandos, com um
# comentario curto. 'help' mostra tudo; 'help <comando>' (ex.: 'help set',
# 'help marker', 'help sel') mostra so as entradas relacionadas.
# ----------------------------------------------------------------------------

AJUDA = [
    ("Arquivos e sessao", [
        ("open <arq.nc> [grade.nc]", "abre um arquivo (aceita * ? [..]); pode abrir varios"),
        ("reinit", "fecha tudo e volta ao estado inicial"),
        ("reset", "volta selecoes (lat/lon/lev/t/cut/sel/eixos) e limpa o grafico"),
        ("run <script>", "executa comandos de um arquivo, um por linha"),
        ("load limits <arq.csv>", "carrega um poligono (area) para as estatisticas inlimits"),
        ("debug <on|off>", "off = comandos silenciosos (so erros e resultados)"),
        ("! <cmd> | exec <cmd>", "executa um comando do shell"),
        ("help [comando]", "esta ajuda"),
        ("q | exit | quit", "encerra o programa"),
    ]),
    ("Plotagem", [
        ("d <var>[.N]", "mapa 2D, perfil ou corte (conforme lat/lon/lev); .N = arquivo N"),
        ("d <expr>", "expressao, ex.: d t2m-273.15"),
        ("d <u>;<v>", "vento (set gxout vect|stream|barb)"),
        ("d3 <var>", "grafico 3D em janela propria"),
        ("c", "limpa o grafico ativo"),
        ("gxprint <arq.png>", "salva a figura (png, pdf...)"),
        ("write csv <arq>", "grava todas as curvas (graficos de linha) em CSV"),
        ("write animation <var> <arq.gif> [seg]", "GIF animado do mapa em set t <ini> <fim> (gxout shaded|contour|voronoi|hex)"),
    ]),
    ("Variaveis do usuario", [
        ("let <nome> = <expr>", "cria variavel, ex.: let tg = temp.2/geo.2"),
        ("<nome> = <expr>", "idem, sem 'let'"),
        ("let", "lista as variaveis criadas"),
        ("undef <nome>", "remove variavel criada"),
    ]),
    ("Estatisticas", [
        ("sum|mean|min|max|pXX all <var>", "valor unico sobre toda a malha"),
        ("... inlimits <var>", "somente dentro da area de 'load limits'"),
        ("... point <var>", "reduz tambem sobre a faixa de niveis"),
        ("d <estat> all|inlimits|point <var>", "plota o resultado ponto a ponto"),
        ("sel [lat a b | lon a b | t a [b]]", "regiao/periodo para estatistica no tempo; sel clear"),
        ("<estat> sel <var>", "tabela da estatistica na regiao, por arquivo"),
        ("d <estat> sel <var>", "curva da estatistica no tempo"),
        ("acum <estat> sel <var>", "idem, sobre o campo acumulado no tempo (d acum ...)"),
    ]),
    ("set - dominio e dados", [
        ("set lat [<v>|<min> <max>]", "latitude (ponto/intervalo; sem args = dominio completo)"),
        ("set lon [<v>|<min> <max>]", "longitude (ponto/intervalo; sem args = dominio completo)"),
        ("set lev <n>|<n1> <n2>", "nivel (indice) ou faixa de niveis"),
        ("set t <n>|<ini> <fim>", "arquivo n, ou serie/animacao (aceita first e last)"),
        ("set tint <seg>", "intervalo da animacao"),
        ("set cut <min> <max>", "so plota valores nesta faixa (sem args: desliga)"),
    ]),
    ("set - cores, mapa, grade", [
        ("set gxout <tipo>", "shaded|contour|voronoi|hex|vect|stream|barb"),
        ("set cmap <nome>", "colormap"),
        ("set clevs <v0> ... <vn>", "fronteiras dos intervalos de cor"),
        ("set minmax <var> <min> <max> [int]", "escala de cor fixa p/ a variavel (d, d3, animacao); sem args = automatico"),
        ("set background <cor>", "cor de fundo da janela (default)"),
        ("set bar position <U|D|L|R>", "posicao da barra de cores"),
        ("set mappat <dir> | set mpdset <arq.shp> | set mpt <cor> <esp>", "mapa de fundo"),
        ("set contour line size|<bw|color>", "linhas de contorno"),
        ("set contour font [color|size|style] <v>", "rotulos do contorno"),
        ("set grid on|off|color|size|type <v>", "grade (cheia, tracejada, traco-ponto, pontilhada...)"),
        ("set plot_line <esp> <cor>", "linha dos perfis"),
    ]),
    ("set - eixos e textos", [
        ("set xrange|yrange <min> <max>", "limites dos eixos (off = automatico)"),
        ("set xdiv|ydiv <valor>", "tamanho de cada divisao (X de tempo: horas)"),
        ("set xtics|ytics <on|off>", "marcacoes dos eixos"),
        ("set label|title|xlabel|ylabel font|color|size|style <v>", "estilo de textos"),
        ("set label <texto>", "rotulo da barra de cores"),
    ]),
    ("set - marcadores", [
        ("set marker <on|off>", "marcadores dos graficos de linha"),
        ("set marker type <tipo|auto>", "o D s * ^ v < > p h + x ... (auto = sequencia por curva)"),
        ("set marker size <n> | color <cor>", "tamanho e cor"),
        ("set marker text <on|off>", "escreve o valor em cada ponto"),
    ]),
    ("set - curvas (plot1, plot2...) e legenda", [
        ("(cada grafico de linha vira plot1, plot2...)", "cor ANSI 30-37 e marcador o s D * ^ v < > p h + x em sequencia"),
        ("set plot <n> color|markercolor <cor>", "cor da curva n / do seu marcador"),
        ("set plot <n> marker <tipo|auto>", "marcador da curva n"),
        ("set plot <n> linetype <tipo> | linesize <n>", "tipo e espessura da linha"),
        ("set plot <n> markersize <n> | label <texto>", "tamanho do marcador / texto na legenda"),
        ("set plot <n> default", "volta ao estilo automatico"),
        ("set legend <on|off>", "caixa de legenda (padrao: a esquerda do grafico)"),
        ("set legend position <L|R|U|D>", "esquerda, direita, acima ou abaixo"),
        ("draw legend title <titulo>", "titulo da caixa de legenda"),
        ("set legend title size <n> | color <cor>", "tamanho do titulo / cor (texto e borda)"),
        ("set legend line <esp> | linetype <tipo>", "espessura e tipo da borda da caixa"),
        ("show plots", "tabela: Plot #, Variable, Color, Marker"),
    ]),
    ("set - figura", [
        ("set pages <lin> <col> | set page <lin> <col>", "paineis da janela 2D"),
        ("set fig_dpi <n> | fig_inches <modo> | fig_transparency <bool>", "opcoes de gxprint"),
    ]),
    ("draw", [
        ("draw title <texto>", "titulo do grafico"),
        ("draw label <texto>", "rotulo da barra de cores"),
        ("draw xlabel|ylabel <texto>", "rotulo dos eixos"),
        ("draw mark <lat> <lon> <simbolo 1-11>", "simbolo no mapa"),
        ("draw map [off]", "mapa de fundo (persistente ate 'off')"),
        ("draw legend", "mostra a legenda (liga set legend on se ha curvas)"),
    ]),
    ("show", [
        ("show info", "arquivo, dimensoes, variaveis, set e sel atuais"),
        ("show variables | levels [tipo] | lev", "variaveis e niveis"),
        ("show files | times | timestamp [n]", "arquivos abertos e seus tempos"),
        ("show lat | lon | latitudes | longitudes", "dominio"),
        ("show sel | limits | setup | fonts", "selecao, area, estado interno, fontes"),
        ("show title | label | map | cmap ...", "valores atuais"),
    ]),
]


def _casa(termo, sintaxe, comentario, grupo):
    termo = termo.lower()
    palavras = sintaxe.lower().replace("|", " ").replace("<", " ").replace(">", " ").split()
    return (termo in palavras or sintaxe.lower().startswith(termo)
            or termo in grupo.lower().split() or termo in comentario.lower().split())


def cmd_help(cmd_split):
    """'help' (tudo) ou 'help <termo>' (so o que se relaciona ao termo)."""
    termo = cmd_split[1] if len(cmd_split) > 1 else None
    if len(cmd_split) > 2:
        print("Uso: help [comando]")
        return
    achou = False
    largura = max(len(s) for _, itens in AJUDA for s, _ in itens)
    largura = min(largura, 46)
    for grupo, itens in AJUDA:
        sel = [(s, c) for s, c in itens if termo is None or _casa(termo, s, c, grupo)]
        if not sel:
            continue
        achou = True
        print("")
        print("[{0}]".format(grupo))
        for s, c in sel:
            if len(s) > largura:
                print("  {0}".format(s))
                print("  {0}  # {1}".format(" " * largura, c))
            else:
                print("  {0:<{w}}  # {1}".format(s, c, w=largura))
    if not achou:
        print("Nenhum comando relacionado a '{0}'. Use 'help' para ver todos.".format(termo))
    elif termo is None:
        print("")
        print("Detalhes: 'help <comando>' (ex.: help sel). Manual completo: userManual.md; guia rapido: refcard.md")
