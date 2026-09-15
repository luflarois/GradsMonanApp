# Manual do `grads_monan`

Ferramenta de linha de comando interativa (estilo GrADS/COLA) para abrir e
plotar saídas do modelo **MONAN/MPAS** (grade de Voronoi não estruturada),
incluindo interpolação, cortes verticais, perfis, vento e campos escalares.

---

## 1. Como rodar

Estando no ambiente criado (conda ou venv - veja na instalação), por exemplo, usando o conda:

```bash
conda activate grads-monan
```

Execute o comando abaixo:

```bash
grads_monan
```

Ao iniciar, o programa carrega a configuração padrão de
`~/.config/grads_monan/grads_monan.toml` (gerada por `install.py`) e abre um
prompt `>` interativo, com histórico de comandos (setas para cima/baixo) e
autocompletar de linha via `readline`.

Todo comando é digitado no prompt, uma linha por vez. Comandos com scripts
prontos podem ser executados com `run <arquivo>`.

---

## 2. Comandos do prompt (nível superior)

| Comando | Descrição |
|---|---|
| `open <arquivo.nc> [grade.nc]` | Abre um arquivo NetCDF de saída do MONAN/MPAS. O segundo argumento (opcional) é um arquivo de grade externo — necessário quando o arquivo de dados não traz `latCell`/`lonCell`/`nCells` embutidos (comum em grades regionais e em saídas de diagnóstico/pós-processadas). Ver seção 9 para o detalhe de como cada caso é tratado. Qualquer falha (arquivo/grade não encontrados, incompatibilidade de nº de células) avisa e **mantém a sessão anterior**, sem encerrar o programa. |
| `reinit` | Fecha o arquivo aberto, apaga toda a configuração associada a ele e volta ao estado inicial (pronto para um novo `open`). Também limpa a janela de gráficos. |
| `run <script>` | Executa, em sequência, os comandos contidos no arquivo de script informado (um comando por linha). |
| `c` | Limpa o gráfico atual. Se houver múltiplos painéis ativos (`set pages`), limpa **só o painel selecionado**; caso contrário, limpa a janela inteira. |
| `gxprint <arquivo_saida>` | Salva a figura atual em disco (PNG, PDF, etc., conforme a extensão), usando `fig_dpi`/`fig_inches`/`fig_transparency` do `setup`. |
| `show <opção>` | Consulta informações da sessão/arquivo atual — ver tabela na seção 4. |
| `set <opção> <valores>` | Ajusta uma configuração de plotagem/sessão — ver tabela na seção 5. |
| `draw <opção>` | Desenha um elemento adicional sobre o gráfico atual — ver tabela na seção 6. |
| `d <variavel>` / `display <variavel>` | Plota uma variável do arquivo aberto — ver sintaxes na seção 7. |
| `! <comando>` / `exec <comando>` | Executa um comando de shell do sistema operacional. |
| `q` / `exit` / `quit` | Encerra o programa. |

Qualquer comando (exceto `!`/`exec`, `open`, `reinit`, `run` e `q`/`exit`/`quit`)
exige um arquivo aberto; sem isso, o programa avisa e volta ao prompt.

---

## 3. Sintaxe do comando `d` / `display`

| Forma | Efeito |
|---|---|
| `d <variavel>` | Plota a variável diretamente do arquivo (mapa, corte vertical ou perfil, dependendo de `lat`/`lon`/`lev` selecionados — ver seção 7). |
| `d (<expressão>)` | Avalia uma expressão aritmética (`+ - * / **` e parênteses) substituindo os nomes de variáveis do arquivo, e plota o resultado. Ex.: `d (t2m - 273.15)`. Avaliação restrita (sem acesso a funções do Python) — variáveis não encontradas são reportadas com sugestões, sem travar o programa. |
| `d mag(<var_u>,<var_v>)` (ou `d mag <var_u> <var_v>`) | Calcula a magnitude `sqrt(u²+v²)` das duas variáveis e a trata como uma variável escalar comum: obedece `shaded`/`contour`/`voronoi`, corte vertical e perfil. |
| `d <var_u>;<var_v>` | Plotagem de **vento**: sempre desenha vetores/streamlines/barbelas (conforme `set gxout`), nunca `shaded`/`contour`. Não limpa a figura — sobrepõe a um campo escalar já plotado. |

Em qualquer forma:
- se a variável não existir no arquivo, o programa mostra sugestões de nomes
  parecidos (ou lista todas as disponíveis) e volta ao prompt sem travar;
- se o número de pontos da variável **não bater** com o número de pontos da
  malha aberta (`latCell`/`lonCell` — ver seção 9.2), avisa claramente em vez
  de deixar o `matplotlib`/`scipy` travar com um erro críptico.

---

## 4. Comandos `show <opção>`

| Opção | Mostra |
|---|---|
| `show info` | Nome do arquivo NetCDF (e da grade, se houver), dimensões (nº de células, níveis verticais, tempos) e a lista completa de variáveis, com nº de níveis, descrição e unidade de cada uma. |
| `show latitudes` | Lista de latitudes da malha, ordenada. |
| `show longitudes` | Lista de longitudes da malha, ordenada. |
| `show levels` | Lista de níveis (pressão em hPa, índice de nível, conforme o arquivo). |
| `show lev` | Nível/intervalo de nível atualmente selecionado (`set lev`). |
| `show variables` | Lista de variáveis do arquivo com sua descrição (`long_name`). |
| `show time` | Array bruto da variável de tempo (`xtime`), ou `[0]` se o arquivo não tiver essa variável. |
| `show time_variable` | Objeto da variável `initial_time` do NetCDF, ou `None` se não existir. |
| `show time_units` | Unidades de tempo declaradas no arquivo, ou `"desconhecida"`. |
| `show Date` | Data/hora inicial do arquivo, já formatada, ou `"desconhecida"`. |
| `show title` | Título atual do gráfico (`set title`, via `draw title`). |
| `show label` | Rótulo atual da barra de cores. |
| `show map` | Lista os shapefiles disponíveis em `mappath`, marcando o selecionado. |
| `show map_color` / `show map_line` | Cor/espessura da linha do mapa de fundo. |
| `show lat` / `show lon` | Intervalo de latitude/longitude atualmente selecionado. |
| `show cmap` | Colormap atual. |
| `show setup` | Imprime o dicionário `setup` inteiro (debug). |

---

## 5. Comandos `set <opção>`

Todos os termos numéricos são validados: se algum não for um número válido,
ou faltar um argumento, o comando avisa o erro e **mantém a configuração
anterior**, sem travar o programa.

| Comando | Efeito |
|---|---|
| `set lev <n>` | Seleciona um único nível (índice). Imprime a informação do nível: pressão em hPa (se houver `t_iso_levels`), senão a altura geométrica média (`zgrid`, se existir), senão apenas o índice. |
| `set lev <n1> <n2>` | Seleciona um intervalo de níveis (usado em corte vertical/perfil). |
| `set lat <valor>` | Fixa a latitude num único ponto. |
| `set lat <min> <max>` | Define um intervalo de latitude (domínio do mapa). |
| `set lon <valor>` | Fixa a longitude num único ponto. |
| `set lon <min> <max>` | Define um intervalo de longitude (domínio do mapa). |
| `set gxout <tipo>` | Tipo de plotagem: `shaded`/`contour`/`voronoi` (variáveis escalares); `vect` (padrão)/`stream`/`barb` (vento, comando `d u;v` ou `d mag(...)`). |
| `set clevs <v0> <v1> ... <vn>` | Define as fronteiras exatas dos intervalos de cor/contorno (ex.: `0 100 200 ... 1500` cria faixas 0–100, 100–200, etc.), usadas em todos os tipos de plotagem com barra de cores. Lista vazia volta ao padrão automático (20 níveis). |
| `set cmap <nome>` | Colormap do matplotlib (ex.: `jet`, `viridis`). |
| `set pages <linhas> <colunas>` | Define a grade de painéis da janela (ex.: `set pages 1 2` = 2 painéis lado a lado). Limpa a janela e seleciona o primeiro painel. |
| `set page <linha> <coluna>` | Seleciona em qual painel as próximas plotagens serão feitas. |
| `set label <texto>` | Rótulo da barra de cores. |
| `set label_fs <n>` | Tamanho de fonte do rótulo da barra de cores. |
| `set label_fw <peso>` | Peso de fonte do rótulo (ex.: `bold`, `normal`). |
| `set mappat <caminho>` | Diretório onde estão os shapefiles do mapa de fundo. |
| `set mpdset <arquivo.shp>` | Shapefile a usar como mapa de fundo. |
| `set mpt <cor> <espessura>` | Cor e espessura da linha do mapa de fundo. |
| `set plot_line <espessura> <cor>` | Espessura/cor de linha usada em perfis. |
| `set grid on|off` | Liga/desliga a grade (gridlines) do gráfico. |
| `set time <n>` (ou `set t <n>`) | Índice de tempo selecionado no arquivo. |
| `set mark <x> <y> <cor> <tamanho> <legenda>` | Mecanismo antigo de acumular pontos de marcação. **Legado**: não é mais usado por `draw mark` (ver seção 6), que hoje tem sua própria sintaxe autossuficiente. |
| `set fig_dpi <n>` | Resolução (DPI) ao salvar figuras (`gxprint`). |
| `set fig_inches <modo>` | Ajuste de bordas ao salvar (`bbox_inches`, ex.: `tight`). |
| `set fig_transparency <bool>` | Fundo transparente ao salvar. |
| `set title_color <cor>` | Cor do título do gráfico. |
| `set title_fs <n>` | Tamanho de fonte do título. |
| `set title_fw <peso>` | Peso de fonte do título. |

---

## 6. Comandos `draw <opção>`

| Comando | Efeito |
|---|---|
| `draw title <texto>` | Define e desenha o título do gráfico. |
| `draw mark <lat> <lon> <simbolo>` | Desenha um símbolo de marca na coordenada geográfica informada, sobre o gráfico atual. `simbolo` é um inteiro de 1 a 11, conforme a tabela clássica do GrADS (seção 6.1). `lat`/`lon` inválidos ou símbolo fora de 1–11 avisam o erro e voltam ao prompt, sem travar. |
| `draw legend` | Mostra a legenda do gráfico atual. |
| `draw map` | Desenha o mapa de fundo (fronteiras/contornos) sobre o gráfico. |
| `draw label <texto>` | Define o rótulo da barra de cores atual. |

### 6.1 Tabela de símbolos (`draw mark`)

| Nº | Símbolo | Descrição | `marker` / `fillstyle` |
|---|---|---|---|
| 1 | `+` | Cruz | `+` |
| 2 | `○` | Círculo vazio | `o` / `none` |
| 3 | `●` | Círculo cheio | `o` / `full` |
| 4 | `□` | Quadrado vazio | `s` / `none` |
| 5 | `■` | Quadrado cheio | `s` / `full` |
| 6 | `×` | X | `x` |
| 7 | `◇` | Losango vazio | `D` / `none` |
| 8 | `△` | Triângulo vazio | `^` / `none` |
| 9 | `▲` | Triângulo cheio | `^` / `full` |
| 10 | ◐ | Círculo meio-preenchido (esquerda/direita) | `o` / `left` |
| 11 | ◑ | Círculo meio-preenchido (cima/baixo) | `o` / `top` |

Exemplo:
```
> d t2m
> draw mark -23.5 -46.6 3
> draw mark -22.9 -43.2 9
```

---

## 7. Como o `d <variavel>` decide o que plotar

A decisão é automática, a partir de `lat_min`/`lat_max`/`lon_min`/`lon_max`/`lev`/`levf`:

| Condição | Resultado |
|---|---|
| Latitude e longitude fixas no mesmo ponto | **Perfil vertical** no ponto, ao longo do intervalo de níveis selecionado. |
| Apenas latitude fixa (longitude com intervalo), ou vice-versa | **Corte vertical** (longitude×nível ou latitude×nível), interpolando a malha sobre uma linha na coordenada fixada. Exige um intervalo de níveis (`lev != levf`). |
| Nem latitude nem longitude fixas | **Mapa horizontal** no nível único selecionado, conforme `gxout` (`shaded`, `contour` ou `voronoi`). |

No **eixo vertical** do corte/perfil, a fonte dos valores segue esta ordem de prioridade:

1. **Pressão** (hPa), se o arquivo tiver `t_iso_levels` — maior pressão embaixo, menor em cima.
2. **Altura geométrica** (m), se não houver `t_iso_levels` mas houver `zgrid` — interpolada ao longo do corte (acompanha o terreno); menor embaixo, maior em cima.
3. **Índice do nível do modelo**, se nenhum dos dois existir; menor embaixo, maior em cima.

Áreas sem dado válido (tipicamente abaixo da topografia local, na grade
seguindo o terreno) aparecem **hachuradas** no corte vertical.

---

## 8. Arquivo de configuração (`grads_monan.toml`)

Gerado por `install.py` em `~/.config/grads_monan/grads_monan.toml`, define os
valores padrão de sessão (usados sempre que um arquivo é aberto):
`xmark`, `ymark`, `colormark`, `sizemark`, `legend`, `lev`, `levf`, `gxout`,
`title`, `label`, `map`, `map_color`, `map_line`, `cmap`, `lw`, `lc`, `clevs`,
`lat_min`, `lat_max`, `lon_min`, `lon_max`, `time_sel`, `mappath`, `fig_dpi`,
`fig_inches`, `fig_transparency`, `label_fontsize`, `label_fontweight`,
`title_color`, `title_fs`, `title_fw`.

---

## 9. Abertura de arquivo: malha, tempo e níveis ausentes

Nem todo arquivo de saída do MONAN/MPAS traz a mesma estrutura — saídas de
diagnóstico/pós-processadas costumam ser mais enxutas que a saída direta do
modelo. O `open` trata isso de forma resiliente, em vez de travar:

### 9.1 Dimensão `nCells` (malha)

| Situação | Comportamento |
|---|---|
| Arquivo de dados tem `nCells` **e** `latCell`/`lonCell`, sem grade informada | Usa a malha do próprio arquivo (comportamento padrão). |
| Arquivo de dados tem `nCells`, mas não tem `latCell`/`lonCell` | Procura (ou usa, se informado) um arquivo de grade; adivinha o nome padrão `x1.<nCells>.grid.nc` se nenhum for informado. |
| Arquivo de dados **não tem** `nCells`, e nenhuma grade foi informada | Avisa e pede explicitamente um arquivo de grade (`open <arquivo> <grade.nc>`); volta ao prompt sem travar. |
| Arquivo de dados **não tem** `nCells`, mas uma grade foi informada | Busca `nCells`/`latCell`/`lonCell` **na grade**. Se a grade também não tiver `nCells`, avisa e volta ao prompt. |
| `nCells` do arquivo de dados e da grade divergem | Avisa a incompatibilidade e volta ao prompt (grades e dados são de resoluções diferentes). |

### 9.2 Compatibilidade variável × malha

Mesmo com a malha aberta com sucesso, uma variável específica pode ter um
número de pontos diferente do número de células da malha (ex.: arquivo de
diagnóstico numa malha reduzida/reamostrada). Nesse caso, ao tentar plotar
(`d <variavel>`), o programa avisa:

```
Erro: a variavel '<nome>' tem N ponto(s), mas a malha aberta (latCell/lonCell) tem M ponto(s).
Isso indica que esta variavel nao esta na mesma malha do arquivo de grade usado no 'open'.
```

em vez de deixar o `matplotlib`/`scipy` travar com um erro interno.

### 9.3 Variáveis de tempo (`xtime`/`initial_time`)

Se `xtime` não existir no arquivo, avisa e lista quaisquer variáveis com
"time" no nome disponíveis (para ajudar a identificar uma alternativa);
`DataDado` fica `"desconhecida"`. Se `initial_time` não existir, avisa e
`time_units` fica `"desconhecida"`. Em nenhum caso o programa trava.

### 9.4 Níveis verticais

Se `t_iso_levels` (níveis de pressão) não existir, usa o índice de uma
dimensão vertical identificada pelo nome (contendo "lev" ou "vert"); se
nenhuma dimensão vertical for identificada, assume nível único (dado 2D).

---

## 10. Dicionário `setup` (estado da sessão)

Além dos valores vindos do `.toml` (seção 8), o `setup` é enriquecido no
`open` com:

| Chave | Conteúdo |
|---|---|
| `openFile` | `True` se há um arquivo aberto. |
| `openFileName` | Caminho do arquivo NetCDF aberto. |
| `gridFileName` | Caminho do arquivo de grade usado, ou `None` se a malha veio embutida no próprio arquivo de dados. |
| `variables` | Referência a `dataset.variables` (acesso direto às variáveis do NetCDF). |
| `latitudes` / `longitudes` | Coordenadas de cada célula da malha (graus, longitude normalizada para -180/180). |
| `levels` | Lista de níveis (pressão em hPa, ou índices do modelo). |
| `eixo_pressao` | `True` se `levels` representa pressão (`t_iso_levels`); `False` se são índices de modelo. |
| `vertices_on_cell`, `n_edges_on_cell`, `lat_vertex`, `lon_vertex`, `tem_conectividade_voronoi` | Conectividade da malha (para `gxout voronoi`); `None`/`False` se indisponível. |
| `lat_min`, `lat_max`, `lon_min`, `lon_max` | Domínio geográfico selecionado (via `set lat`/`set lon`; inicialmente o domínio total do arquivo). |
| `lev`, `levf` | Índice de nível (único ou intervalo) selecionado. |
| `time`, `time_variable`, `time_units`, `time_str`, `DataDado` | Informações de tempo do arquivo (com valores de reserva se ausentes — ver seção 9.3). |
| `pages_rows`, `pages_cols`, `page_row`, `page_col` | Grade de painéis da janela (`set pages`/`set page`). |

---

## 11. Referência de módulos e funções

### `grads_monan.py`
Laço principal: carrega config/histórico, lê comandos (`custom_input`),
despacha via `exec_cmd`, e força o redesenho da janela (`plt.draw()` +
`plt.pause()`) após cada comando — necessário porque parte das funções de
plotagem usa métodos do eixo (`ax.contourf`, `ax.tricontourf` etc.), que não
disparam o redesenho automático do modo interativo (`plt.ion()`) sozinhas.

### `exec_func.py`
- `exec_cmd(...)` — despachante central de todos os comandos do prompt.
- `run_file(...)` — executa um script de comandos linha a linha.
- `_var_not_found(dataset, varname)` — mensagem de variável não encontrada, com sugestões por similaridade (`difflib`).
- `_avaliar_expressao(dataset, expr)` — avaliador seguro de expressões aritméticas sobre variáveis do arquivo (usado por `d (expr)`).

### `files_nc.py`
- `file_open(fileName, setup_toml, gridFile=None)` — abre o arquivo NetCDF (e a grade, se necessária), monta o `setup` completo da sessão. Lida com ausência de `nCells`, malha, `xtime`/`initial_time` e `t_iso_levels` de forma resiliente (seção 9). Retorna `(None, None)` em qualquer falha irrecuperável, sem encerrar o programa.

### `set_func.py`
- `cmd_set(cmd_split, setup, cmd_user)` — ponto de entrada público do comando `set`; captura erros de conversão numérica/argumentos faltando.
- `_cmd_set_dispatch(...)` — implementação de cada subcomando `set` (tabela da seção 5).
- `_print_level_info(setup, l)` — imprime a informação do nível ao usar `set lev <n>` (pressão/zgrid/índice).

### `show_func.py`
- `cmd_show(setup, cmd_split)` — implementação de cada subcomando `show` (tabela da seção 4).
- `_mostrar_info_arquivo(setup)` — implementação de `show info`.
- `show_legend()` — implementação de `draw legend`.

### `draw_func.py`
- `draw_title(setup)` — implementação de `draw title`.
- `draw_map(setup, ax)` — implementação de `draw map`.
- `draw_mark(cmd_split)` — implementação de `draw mark <lat> <lon> <simbolo>` (seção 6.1); valida os argumentos e desenha o símbolo escolhido.
- `draw_label(setup, cbar, lbl)` — implementação de `draw label`.
- `_SIMBOLOS_MARK` — tabela de conversão símbolo → `marker`/`fillstyle` do matplotlib.

### `plot_func.py`
- `plot_var(setup, var, cbar=None)` — plotagem de variável escalar; decide entre mapa/corte/perfil (seção 7) e despacha para `shaded`/`contour`/`voronoi`.
- `plot_perfil(setup, var)` — perfil vertical num ponto fixo.
- `plot_corte(setup, var, cbar=None)` — corte vertical (longitude×nível ou latitude×nível), com hachura nas áreas sem dado válido.
- `plot_voronoi(setup, data)` — desenha o polígono real de cada célula da malha (via `PolyCollection`), sem interpolar.
- `plot_wind(setup, var1, var2, cbar)` — despacha a plotagem de vento (`vect`/`stream`/`barb`) conforme `gxout`.
- `plot_vector_field`, `plot_barbs`, `plot_streams` — implementações de vetor, barbela e linha de corrente, respectivamente.
- `plot_marks(setup)` — mecanismo antigo de desenhar os pontos acumulados via `set mark` (legado, não usado mais por `draw mark`).
- `clear_plots(setup=None)` — limpa o painel atual ou a janela inteira, conforme haja múltiplos painéis ativos.
- `set_window_title(titulo)` — define o título da janela do matplotlib (nome do arquivo aberto).
- `set_ion()` — ativa o modo interativo do matplotlib.
- `save_fig(fig_name, setup)` — salva a figura atual em disco (`gxprint`).
- `_niveis_cor(setup)` — resolve os níveis de cor/contorno a usar (`set clevs` ou padrão de 20 níveis).
- `_tamanho_malha_ok(label, tamanho_dado, tamanho_malha)` — confere se o número de pontos da variável bate com o da malha aberta antes de plotar; avisa com uma mensagem clara em vez de deixar o matplotlib/scipy travar (seção 9.2).

### `map_func.py`
- `plot_map(setup, ax)` — desenha o shapefile de fundo (fronteiras) sobre o eixo atual.

### `utils.py`
- `normalize_lon(lon)` — normaliza longitude para o intervalo (-180, 180].
- `mag(u, v)` — magnitude vetorial `sqrt(u²+v²)`.
- `load_zgrid_centers(variables, n_cells, n_levels)` — extrai e alinha a variável `zgrid` (altura geométrica) ao formato `(nCells, n_levels)`, tratando interfaces entre camadas e dimensões extras com segurança.
- `encontrar_posicao_mais_proxima(lista, valor)` — busca binária do ponto de inserção mais próximo numa lista ordenada.
- `custom_input()` — entrada de comando do prompt, com suporte a histórico via `readline`.
- `load_history(HISTORY_FILE)` / `save_command_to_history(cmd, HISTORY_FILE)` — carrega/grava o histórico de comandos em disco.

### `install.py`
Script de instalação: cria `~/.config/grads_monan/`, copia os shapefiles de
mapa (`Continents.*`) e gera o `grads_monan.toml` com os valores padrão de
sessão (seção 8). Deve ser executado uma vez antes do primeiro uso.

---

## 12. Requisitos de arquivo

- **Sempre necessário**: as variáveis a serem plotadas.
- **Malha**: `nCells` (dimensão) e `latCell`/`lonCell`, embutidos no arquivo
  de dados ou num arquivo de grade externo (segundo argumento do `open`) —
  ver seção 9.1 para o que acontece quando faltam.
- **Tempo** (opcional, com valores de reserva se ausente): `xtime`,
  `initial_time` — ver seção 9.3.
- **Níveis de pressão** (opcional): `t_iso_levels`. Sem essa variável, o
  programa usa o índice do nível do modelo (dimensão com "lev"/"vert" no
  nome).
- **Altura geométrica** (opcional, para corte/perfil por altura real):
  `zgrid`, no arquivo de dados ou na grade.
- **Voronoi** (opcional, para `set gxout voronoi`): `verticesOnCell`,
  `nEdgesOnCell`, `latVertex`, `lonVertex` — normalmente só presentes no
  arquivo de grade/estático completo do MPAS, não nas saídas de histórico.
