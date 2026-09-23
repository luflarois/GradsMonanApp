# Manual do GradsMonanApp

Um clone do GrADS/COLA para abrir e plotar saídas do modelo **MONAN/MPAS**
(grade de Voronoi não estruturada), incluindo interpolação, cortes
verticais, perfis, vento, campos escalares em 2D e 3D — com desempenho
pensado para malhas grandes (testado até a resolução operacional,
~5,9 milhões de células).

---

## 1. Instalação e como rodar

```bash
conda env create -f environment.yml   # ou: pip install .
conda activate grads-monan
grads-monan
```

Na primeira execução, a pasta de configuração (`~/.config/grads_monan/`) e
o `grads_monan.toml` são criados automaticamente — não é preciso rodar
nenhum script de instalação à parte. Para recriar a configuração do zero:
`grads-monan-setup`.

Ao iniciar, abre um prompt `>` interativo, com histórico de comandos (setas
para cima/baixo) via `readline`. Comandos com scripts prontos podem ser
executados com `run <arquivo>`.

---

## 2. Comandos do prompt (nível superior)

| Comando | Descrição |
|---|---|
| `open <arquivo.nc> [grade.nc]` | Abre um arquivo NetCDF de saída do MONAN/MPAS. Pode ser chamado **mais de uma vez na mesma sessão**, para trabalhar com vários arquivos ao mesmo tempo — ver seção 2.1. O segundo argumento (opcional) é um arquivo de grade externo — necessário quando o arquivo de dados não traz `latCell`/`lonCell`/`nCells` embutidos. Ver seção 10 para o detalhe de cada caso. Qualquer falha (inclusive um arquivo com malha diferente da já aberta) avisa e **mantém a sessão anterior intacta**, sem encerrar o programa. |
| `reinit` | Fecha **todos** os arquivos abertos na sessão, apaga toda a configuração associada a eles (inclusive os caches de triangulação em memória) e volta ao estado inicial, pronto para um novo `open`. Também limpa a janela de gráficos. |
| `run <script>` | Executa, em sequência, os comandos contidos no arquivo de script informado (um comando por linha). |
| `c` | Limpa o gráfico ativo no momento. Se o `d3` foi o último a plotar, limpa a **janela 3D** (recriando o eixo); se foi o `d`, limpa a janela 2D (só o painel atual, se `set pages` estiver ativo). |
| `gxprint <arquivo_saida>` | Salva a figura atual em disco (PNG, PDF, etc.), usando `fig_dpi`/`fig_inches`/`fig_transparency` do `setup`. |
| `show <opção>` | Consulta informações da sessão/arquivo atual — ver tabela na seção 5. |
| `set <opção> <valores>` | Ajusta uma configuração de plotagem/sessão — ver tabela na seção 6. |
| `draw <opção>` | Desenha um elemento adicional sobre o gráfico atual — ver tabela na seção 7. |
| `d <variavel>` / `display <variavel>` | Plota uma variável em **2D**, na janela principal — ver sintaxes na seção 3. |
| `d3 <variavel>` | Plota uma variável em **3D**, numa janela separada — ver seção 4. |
| `! <comando>` / `exec <comando>` | Executa um comando de shell do sistema operacional. |
| `q` / `exit` / `quit` | Encerra o programa. |

Qualquer comando (exceto `!`/`exec`, `open`, `reinit`, `run` e `q`/`exit`/`quit`)
exige um arquivo aberto; sem isso, o programa avisa e volta ao prompt.

---

## 2.1 Abrindo mais de um arquivo (`open`, `show files`, sufixo `.N`)

O `open` pode ser chamado várias vezes na mesma sessão, para trabalhar com
mais de um arquivo ao mesmo tempo (por exemplo, comparar dois horários de
previsão, ou dois membros de um ensemble):

```
> open SP_O_2022071400_2022071400.00.00.x40962L55.nc
> open SP_O_2022071400_2022071412.00.00.x40962L55.nc
> show files
Num  Arquivo                                        Timestamp
---------------------------------------------------------------
1    SP_O_2022071400_2022071400.00.00.x40962L55.nc   2022-07-14T00
2    SP_O_2022071400_2022071412.00.00.x40962L55.nc    2022-07-14T12
```

- O primeiro `open` bem-sucedido da sessão vira o **arquivo 1**; cada `open`
  seguinte que for aceito vira o próximo número em sequência (2, 3, ...).
- **Mesma malha é obrigatória**: um novo arquivo só é aceito se tiver
  exatamente a mesma malha (mesmo número de células e mesmas coordenadas
  `latCell`/`lonCell`) do(s) arquivo(s) já aberto(s) — a mesma técnica de
  assinatura (nº de células + hash) usada no cache de Delaunay (seção 10.2).
  Se a malha for diferente, o `open` é **rejeitado**, com uma mensagem de
  erro, e a sessão anterior (com todos os arquivos já abertos e as
  configurações feitas até então) permanece **intacta**. Para trocar de
  malha, rode `reinit` primeiro.
- `show files` (ver também seção 5) lista, em forma de tabela, todos os
  arquivos abertos na sessão: número, nome do arquivo e o timestamp
  (data/hora), quando disponível — "desconhecida" caso contrário.
- Abrir um novo arquivo **não reseta** as configurações já feitas na sessão
  (`set lev`, `set gxout`, `title`, etc.) — elas continuam valendo; só o(s)
  arquivo(s) adicional(is) entram na lista.
- `reinit` fecha todos os arquivos abertos e reinicia a sessão do zero.

### Referenciando o arquivo de uma variável (sufixo `.N`)

Em qualquer lugar onde uma variável é referenciada para plotagem — `d`/
`display`, `d3`, `mag(...)`, a forma vetorial `<u>;<v>`, ou dentro de uma
expressão aritmética — ela pode trazer um sufixo `.N` indicando de qual
arquivo aberto ler:

```
> d t2m         (sem sufixo -> le do arquivo 1)
> d t2m.1       (equivalente ao de cima, arquivo 1 explicito)
> d t2m.2       (le a variavel t2m do arquivo 2)
```

Isso permite comparar diretamente dois arquivos numa mesma expressão
aritmética — por exemplo, a diferença entre os dois horários abertos:

```
> d (t2m.2 - t2m.1)
```

e também funciona com `mag(...)` e com a forma vetorial `u;v`:

```
> d mag(u10.2,v10.2)
> d u10.1;v10.1
> d3 t2m.2
```

Se o número do arquivo referenciado não estiver aberto, ou a variável não
existir naquele arquivo, o programa avisa (com sugestões por similaridade,
quando aplicável) e **não trava** — nem interrompe a sessão.

---

## 3. Sintaxe do comando `d` / `display` (2D)

| Forma | Efeito |
|---|---|
| `d <variavel>` | Plota a variável diretamente do arquivo (mapa, corte vertical ou perfil, dependendo de `lat`/`lon`/`lev` selecionados — ver seção 8). |
| `d (<expressão>)` | Avalia uma expressão aritmética (`+ - * / **` e parênteses) substituindo os nomes de variáveis do arquivo, e plota o resultado. Ex.: `d (t2m - 273.15)`, ou cruzando arquivos: `d (t2m.2 - t2m.1)`. Avaliação restrita (sem acesso a funções do Python) — variáveis/arquivos não encontrados são reportados com sugestões. |
| `d mag(<var_u>,<var_v>)` (ou `d mag <var_u> <var_v>`) | Calcula a magnitude `sqrt(u²+v²)` das duas variáveis e a trata como uma variável escalar comum: obedece `shaded`/`contour`/`voronoi`, corte vertical e perfil. |
| `d <var_u>;<var_v>` | Plotagem de **vento**: sempre desenha vetores/streamlines/barbelas (conforme `set gxout`), nunca `shaded`/`contour`. Não limpa a figura — sobrepõe a um campo escalar já plotado. |

Em qualquer forma:
- cada nome de variável pode trazer o sufixo `.N` apontando para o
  N-ésimo arquivo aberto (seção 2.1); sem sufixo, assume o arquivo 1;
- variável (ou arquivo `.N`) não encontrado → sugestões/mensagem clara por
  similaridade, sem travar;
- número de pontos da variável diferente do número de pontos da malha
  aberta → aviso claro (seção 10.2), sem travar.

---

## 4. Comando `d3` (3D) — janela separada

```
d3 <variavel>
```

Assim como no `d`/`display`, `<variavel>` aceita o sufixo `.N` (seção 2.1)
para escolher de qual arquivo aberto ler — ex.: `d3 t2m.2`. Sem sufixo,
assume o arquivo 1.

Exige **faixas reais** (não pontos únicos) nas três dimensões:

```
> set lat <min> <max>
> set lon <min> <max>
> set lev <n1> <n2>
> d3 <variavel>
```

Sem isso, avisa e não plota. Filtra as células da malha dentro dessa caixa
lat×lon, e os níveis dentro do intervalo escolhido. O eixo Z segue a mesma
hierarquia do corte 2D (pressão → altura real `zgrid` → índice de nível —
seção 8).

Abre numa **janela própria**, separada da 2D, e a **reaproveita** entre
chamadas sucessivas de `d3` (não acumula uma janela nova a cada vez).
`c` limpa a janela que estiver ativa no momento (a 3D, se foi a última
usada).

| `set gxout` | Efeito no `d3` |
|---|---|
| `vect` (padrão) ou qualquer valor não listado abaixo | *Scatter* 3D: um ponto por célula/nível, colorido pelo valor. |
| `shaded` | Uma superfície triangulada **por nível**, empilhada no eixo Z, colorida pelo valor da variável (não pela altura). |

`set clevs` (faixas de cor discretas) e `set cut <min> <max>` (transparência
fora do intervalo) funcionam igual ao 2D. Valores exatamente zero também
ficam sempre transparentes no `d3`.

`draw map`, quando a janela 3D é a ativa, desenha o mapa de fundo projetado
na "superfície" da caixa (o nível mais próximo do solo), em vez do
comportamento 2D padrão — ver seção 7.

**Limitações conhecidas**: só aceita `d3 <variavel>` simples (não há
`d3 mag(...)` nem `d3 <u>;<v>` ainda); e, por operar em coordenadas planas,
pode haver artefatos perto da costura de ±180° de longitude em domínios
globais muito amplos.

---

## 5. Comandos `show <opção>`

| Opção | Mostra |
|---|---|
| `show info` | Nome do arquivo NetCDF (e da grade, se houver), dimensões e a lista completa de variáveis, com nº de níveis, descrição e unidade — sempre referente ao **arquivo 1**. Se houver mais de um arquivo aberto, avisa e aponta para `show files`. |
| `show files` | Tabela com todos os arquivos abertos na sessão: número, nome do arquivo e timestamp (data/hora, quando disponível) — ver seção 2.1. Se nenhum arquivo estiver aberto, informa isso. |
| `show latitudes` / `show longitudes` | Lista de coordenadas da malha, ordenada. |
| `show levels` | Lista de níveis (pressão em hPa, ou índice de nível). |
| `show lev` | Nível/intervalo de nível atualmente selecionado. |
| `show variables` | Lista de variáveis do arquivo com sua descrição (`long_name`). |
| `show time` / `show time_variable` / `show time_units` / `show Date` | Informações de tempo do arquivo (com valores de reserva se ausentes). |
| `show title` / `show label` | Título do gráfico / rótulo da barra de cores atuais. |
| `show map` | Lista os shapefiles disponíveis em `mappath`, marcando o selecionado. |
| `show map_color` / `show map_line` | Cor/espessura da linha do mapa de fundo. |
| `show lat` / `show lon` | Intervalo de latitude/longitude atualmente selecionado. |
| `show cmap` | Colormap atual. |
| `show setup` | Imprime o dicionário `setup` inteiro (debug). |

---

## 6. Comandos `set <opção>`

Todos os termos numéricos são validados: erro de conversão ou argumento
faltando avisa e **mantém a configuração anterior**, sem travar.

| Comando | Efeito |
|---|---|
| `set lev <n>` | Nível único. Imprime a informação do nível: pressão em hPa, senão altura média (`zgrid`), senão só o índice. |
| `set lev <n1> <n2>` | Intervalo de níveis (corte vertical, perfil, `d3`). |
| `set lat <valor>` / `set lat <min> <max>` | Latitude fixa num ponto, ou intervalo (domínio do mapa). |
| `set lon <valor>` / `set lon <min> <max>` | Longitude fixa num ponto, ou intervalo. |
| `set gxout <tipo>` | `shaded`/`contour`/`voronoi` (2D, variáveis escalares — também vale `shaded` no `d3`); `vect` (padrão)/`stream`/`barb` (vento, `d u;v` ou `d mag(...)`). |
| `set cut <minimo> <maximo>` | Só plota valores dentro de `[minimo, maximo]`; fora disso fica transparente. Vale para `d` (mapa, corte, perfil) e `d3`. `set cut` sem valores desliga. |
| `set clevs <v0> <v1> ... <vn>` | Fronteiras exatas dos intervalos de cor/contorno (ex.: `0 100 200 ... 1500`). Usadas em todo tipo de plotagem com barra de cores, inclusive `d3`. Lista vazia volta ao padrão automático (20 níveis). |
| `set cmap <nome>` | Colormap do matplotlib. |
| `set pages <linhas> <colunas>` | Grade de painéis da janela 2D (ex.: `set pages 1 2`). Limpa a janela e seleciona o primeiro painel. |
| `set page <linha> <coluna>` | Seleciona em qual painel plotar. |
| `set label <texto>` | Rótulo da barra de cores. |
| `set label_fs <n>` / `set label_fw <peso>` | Tamanho/peso de fonte do rótulo. |
| `set mappat <caminho>` | Diretório dos shapefiles do mapa de fundo. |
| `set mpdset <arquivo.shp>` | Shapefile a usar como mapa de fundo. |
| `set mpt <cor> <espessura>` | Cor e espessura da linha do mapa de fundo. |
| `set plot_line <espessura> <cor>` | Espessura/cor de linha usada em perfis. |
| `set grid on\|off` | Liga/desliga a grade (gridlines) do gráfico. |
| `set time <n>` (ou `set t <n>`) | Índice de tempo selecionado. |
| `set mark <x> <y> <cor> <tamanho> <legenda>` | Mecanismo antigo de acumular pontos de marcação. **Legado**: não é mais usado por `draw mark` (seção 7), que hoje é autossuficiente. |
| `set fig_dpi <n>` / `set fig_inches <modo>` / `set fig_transparency <bool>` | Resolução/margens/transparência ao salvar (`gxprint`). |
| `set title_color <cor>` / `set title_fs <n>` / `set title_fw <peso>` | Aparência do título do gráfico. |

---

## 7. Comandos `draw <opção>`

| Comando | Efeito |
|---|---|
| `draw title <texto>` | Define e desenha o título do gráfico. |
| `draw mark <lat> <lon> <simbolo>` | Desenha um símbolo de marca na coordenada geográfica informada. `simbolo` é um inteiro de 1 a 11 (tabela abaixo). Entradas inválidas avisam sem travar. |
| `draw legend` | Mostra a legenda do gráfico atual. |
| `draw map` | Desenha o mapa de fundo. Se a janela **3D** (`d3`) for a ativa no momento, desenha projetado na "superfície" da caixa 3D em vez do comportamento 2D padrão. |
| `draw label <texto>` | Define o rótulo da barra de cores atual. |

### 7.1 Tabela de símbolos (`draw mark`)

| Nº | Símbolo | `marker` / `fillstyle` |
|---|---|---|
| 1 | `+` | `+` |
| 2 | `○` círculo vazio | `o` / `none` |
| 3 | `●` círculo cheio | `o` / `full` |
| 4 | `□` quadrado vazio | `s` / `none` |
| 5 | `■` quadrado cheio | `s` / `full` |
| 6 | `×` | `x` |
| 7 | `◇` losango vazio | `D` / `none` |
| 8 | `△` triângulo vazio | `^` / `none` |
| 9 | `▲` triângulo cheio | `^` / `full` |
| 10 | ◐ círculo meio (esq/dir) | `o` / `left` |
| 11 | ◑ círculo meio (cima/baixo) | `o` / `top` |

---

## 8. Como o `d`/`d3` decide o que plotar (2D)

| Condição | Resultado |
|---|---|
| Latitude e longitude fixas no mesmo ponto | **Perfil vertical**, no intervalo de níveis selecionado. |
| Apenas latitude fixa (ou só longitude) | **Corte vertical**, interpolando a malha sobre uma linha. Exige intervalo de níveis. |
| Nem latitude nem longitude fixas | **Mapa horizontal**, conforme `gxout` (`shaded`/`contour`/`voronoi`). |

No **eixo vertical** do corte/perfil (e no eixo Z do `d3`):
1. **Pressão** (hPa), se houver `t_iso_levels` — maior pressão embaixo.
2. **Altura real** (m), se houver `zgrid` — interpolada ao longo do corte (acompanha o terreno); menor embaixo.
3. **Índice do nível**, se nenhum dos dois existir; menor embaixo.

Áreas sem dado válido (corte/superfície abaixo da topografia) aparecem
**hachuradas** no corte vertical 2D.

### 8.1 Os três modos de `gxout` para mapa 2D

| `gxout` | Como funciona | Quando usar |
|---|---|---|
| `shaded` | Interpola para uma **grade regular** (reaproveitando a triangulação de Delaunay em cache) e usa `contourf` de grade regular. | Campo suave, contínuo. Rápido mesmo em malhas grandes graças ao cache (seção 9). |
| `contour` | Igual ao `shaded`, mas com `contour` (linhas + rótulos) em vez de preenchido. | Mesma ideia, isolinhas. |
| `voronoi` | **Rasteriza** o diagrama de Voronoi de verdade: pra cada pixel da imagem, usa o valor da célula mais próxima (via `cKDTree`), sem interpolar. Matematicamente exato — mostra o valor real de cada célula, sem suavização. | Quando quer ver os dados "crus", célula por célula, sem nenhuma interpolação. |

---

## 9. Área de configuração (`~/.config/grads_monan/`)

Criada automaticamente na primeira execução (`grads-monan` ou
`grads-monan-setup`). Contém:

| Arquivo | Conteúdo |
|---|---|
| `grads_monan.toml` | Configuração padrão de sessão (seção 9.1). |
| `grads_monan.history` | Histórico de comandos do prompt (setas para cima/baixo). |
| `Continents.*` | Shapefiles do mapa de fundo padrão. |
| `delaunay_cache.pkl` | **Cache persistente** da triangulação de Delaunay da última malha usada — ver seção 10. |
| `last_grid.info` | Arquivo texto legível com as **características** da malha desse cache (não o nome do arquivo — ver seção 10). |

### 9.1 `grads_monan.toml`

Define os valores padrão de sessão (usados sempre que um arquivo é aberto):
`xmark`, `ymark`, `colormark`, `sizemark`, `legend`, `lev`, `levf`, `gxout`,
`title`, `label`, `map`, `map_color`, `map_line`, `cmap`, `lw`, `lc`, `clevs`,
`lat_min`, `lat_max`, `lon_min`, `lon_max`, `time_sel`, `mappath`, `fig_dpi`,
`fig_inches`, `fig_transparency`, `label_fontsize`, `label_fontweight`,
`title_color`, `title_fs`, `title_fw`.

---

## 10. A triangulação de Delaunay (e por que ela é cacheada)

### 10.1 O que é

A malha do MONAN/MPAS é um conjunto de pontos (centros de célula)
espalhados irregularmente pelo globo — não uma grade regular. Para
interpolar essa malha (corte vertical, `streamlines` de vento, mapa
`shaded`/`contour`), o programa precisa de uma **triangulação de Delaunay**:
uma malha de triângulos conectando os pontos vizinhos, construída de forma
que nenhum ponto fique dentro do círculo circunscrito de outro triângulo
qualquer (a propriedade que garante uma interpolação bem-comportada,
sem triângulos "espremidos"). É o que o `scipy.spatial.Delaunay` calcula.

Uma vez triangulada, é possível interpolar qualquer variável para qualquer
ponto de destino (uma linha de corte, uma grade regular, os nós de uma
grade de `streamplot`) rapidamente — a parte cara é a **construção** da
triangulação em si, não o uso dela depois.

### 10.2 Por que isso importa aqui

Para a malha operacional (~5,9 milhões de células), construir essa
triangulação do zero leva dezenas de segundos. Refazer isso a cada `d`
(cada troca de variável) seria inviável. Por isso, o programa a mantém em
**cache em dois níveis**:

1. **Em memória, por sessão** (`setup["_delaunay_malha"]`): construída na
   primeira vez que é necessária (primeiro `shaded`/`contour`/corte/
   `streamlines`/`d3 shaded` depois de um `open`), e reaproveitada por
   todo o resto da sessão — trocar de variável, de tipo de plot, repetir
   o mesmo comando: tudo usa a mesma triangulação já pronta.

2. **Em disco, entre sessões** (`~/.config/grads_monan/delaunay_cache.pkl`):
   quando a triangulação é construída pela primeira vez numa sessão, ela
   também é salva em disco. Da próxima vez que o programa for aberto (nova
   execução) e um arquivo com a **mesma malha** for aberto, a triangulação
   é lida do disco em vez de reconstruída — mesmo sendo tecnicamente um
   arquivo `.nc` diferente (outra data/hora de rodada do modelo, por
   exemplo), desde que a malha em si seja a mesma.

O que identifica "a mesma malha" **não é o nome do arquivo** — é uma
assinatura calculada a partir do número de células e de um hash (`md5`) do
conteúdo real de `latitude`/`longitude` de cada célula, gravada em
`last_grid.info`. Se a assinatura do arquivo recém-aberto bater com a do
cache salvo, ele é reaproveitado; se não bater (malha diferente), o
programa reconstrói normalmente e substitui o cache em disco pelo novo.

Esse mesmo Delaunay em cache também é usado pelo `shaded`/`contour` do
`d3` no modo `vect`/`shaded` (via `_grade_regular_interpolada`) e pelo
corte vertical e `streamlines` (`d u;v` com `gxout stream`) — a primeira
dessas operações numa sessão "paga" o custo da triangulação; todas as
outras, incluindo em sessões futuras com a mesma malha, saem rápidas.

**Nota prática**: o arquivo `delaunay_cache.pkl` pode ficar grande (algumas
centenas de MB numa malha de milhões de células) — normal, não é um bug.

O `voronoi` (seção 8.1) **não** usa essa triangulação — ele usa uma árvore
`cKDTree` dos centros de célula, guardada só em cache de memória (não em
disco), pois sua construção já é rápida por natureza.

---

## 11. Dicionário `setup` (estado da sessão)

Além dos valores vindos do `.toml` (seção 9.1), o `setup` é enriquecido no
`open` com:

| Chave | Conteúdo |
|---|---|
| `openFile` / `openFileName` / `gridFileName` | Se há arquivo aberto; caminho do arquivo de dados; caminho do arquivo de grade usado (ou `None` se embutido no arquivo de dados) — sempre referentes ao **arquivo 1** (seção 2.1). |
| `variables` | Referência a `dataset.variables` do **arquivo 1**. |
| `files` | Lista com um registro por arquivo aberto na sessão (índice, nome do arquivo, arquivo de grade, `dataset`, informações de tempo) — ver seção 2.1. |
| `_malha_assinatura` | Assinatura (nº de células + hash `md5` de lat/lon) da malha da sessão, usada para validar que um novo `open` tem a mesma grade (uso interno — seção 2.1). |
| `latitudes` / `longitudes` | Coordenadas de cada célula da malha (graus, longitude normalizada). |
| `levels` / `eixo_pressao` | Lista de níveis; se representam pressão (`True`) ou índice de modelo (`False`). |
| `lat_min`, `lat_max`, `lon_min`, `lon_max` | Domínio geográfico selecionado. |
| `lev`, `levf` | Índice de nível (único ou intervalo) selecionado. |
| `cut` | `None`, ou `(minimo, maximo)` — ver `set cut`. |
| `time`, `time_variable`, `time_units`, `time_str`, `DataDado` | Informações de tempo (com valores de reserva se ausentes). |
| `pages_rows`, `pages_cols`, `page_row`, `page_col` | Grade de painéis 2D. |
| `fig2d`, `fig3d`, `ax3d` | Referências às figuras/eixo ativos de `d` e `d3` (uso interno). |
| `_delaunay_malha` | Triangulação de Delaunay em cache de memória (uso interno — seção 10). |
| `_arvore_celulas` | Árvore `cKDTree` em cache de memória, para `gxout voronoi` (uso interno). |

---

## 12. Referência de módulos e funções

### `cli.py`
- `main()` — laço principal: banner, `ensure_config()`, lê comandos
  (`custom_input`), despacha via `exec_cmd`, força o redesenho da janela
  (`plt.draw()` + `plt.pause()`) após cada comando.

### `setup_config.py`
- `ensure_config(force=False)` — cria `~/.config/grads_monan/` e o
  `grads_monan.toml` se ainda não existirem (chamado automaticamente pelo
  `main()`).
- `main()` — ponto de entrada de `grads-monan-setup` (reinicializa a config).

### `exec_func.py`
- `exec_cmd(...)` — despachante central de todos os comandos do prompt.
- `run_file(...)` — executa um script de comandos linha a linha.
- `_resolver_variavel(setup, token)` — resolve um token de variável com sufixo opcional `.N` (seção 2.1): localiza o arquivo aberto correspondente e a variável nele, com mensagens de erro/sugestões (`difflib`) quando o arquivo não está aberto ou a variável não existe.
- `_arquivo_por_indice(setup, indice)` — retorna o registro do arquivo aberto com aquele índice, ou `None`.
- `_avaliar_expressao(setup, expr)` — avaliador seguro de expressões aritméticas (`d (expr)`), agora resolvendo cada variável via `_resolver_variavel` — aceita sufixos `.N` e expressões cruzando arquivos, ex. `t2m.2 - t2m.1`.

### `files_nc.py`
- `file_open(fileName, setup_toml, gridFile=None, setup_anterior=None)` — abre o arquivo (e a grade, se necessária). Se `setup_anterior` for passado (já há um arquivo aberto na sessão), valida a malha do novo arquivo contra a assinatura já registrada (seção 2.1): rejeita com `(None, None)` se forem diferentes (preservando `setup_anterior` intacto), ou adiciona o novo arquivo a `setup["files"]` com o próximo índice sequencial, se forem iguais. Sem `setup_anterior` (primeiro `open`), monta o `setup` do zero, como antes. Resiliente à ausência de `nCells`, malha, `xtime`/`initial_time`, `t_iso_levels`.

### `set_func.py`
- `cmd_set(...)` / `_cmd_set_dispatch(...)` — comando `set` (tabela da seção 6), com validação numérica segura.
- `_print_level_info(setup, l)` — informação do nível ao usar `set lev <n>`.

### `show_func.py`
- `cmd_show(setup, cmd_split)` / `_mostrar_info_arquivo(setup)` — comando `show` (tabela da seção 5).
- `_mostrar_arquivos(setup)` — `show files`: tabela com os arquivos abertos na sessão (seção 2.1).
- `show_legend()` — `draw legend`.

### `draw_func.py`
- `draw_title`, `draw_map`, `draw_label` — demais subcomandos `draw`.
- `draw_mark(cmd_split)` — `draw mark <lat> <lon> <simbolo>` (seção 7.1).
- `_SIMBOLOS_MARK` — tabela símbolo → `marker`/`fillstyle`.

### `plot_func.py`
**Plotagem 2D:**
- `plot_var(setup, var, cbar=None)` — despacha mapa/corte/perfil (seção 8) e `shaded`/`contour`/`voronoi`.
- `plot_perfil`, `plot_corte` — perfil vertical e corte, com hachura em áreas sem dado.
- `plot_voronoi(setup, data)` — rasterização via `cKDTree` (seção 8.1).
- `plot_wind`, `plot_vector_field`, `plot_barbs`, `plot_streams` — vento (`vect`/`barb`/`stream`).
- `plot_marks(setup)` — mecanismo antigo de `set mark` (legado).

**Plotagem 3D:**
- `plot_var_3d(setup, var)` — `d3` (seção 4): *scatter* ou superfícies empilhadas (`shaded`).

**Triangulação e interpolação (seção 10):**
- `_obter_triangulacao(setup)` — Delaunay em cache (memória → disco → constrói).
- `_assinatura_grade(setup)` — nº de células + hash de lat/lon.
- `_carregar_delaunay_disco` / `_salvar_delaunay_disco` — cache persistente.
- `_interpolar(setup, valores, pontos_destino)` — interpolação linear reaproveitando a triangulação.
- `_grade_regular_interpolada(setup, ax, data)` — interpola para uma grade regular (usada por `shaded`/`contour`).
- `_obter_arvore_celulas(setup)` — `cKDTree` em cache, para `voronoi`.

**Utilitários de plotagem:**
- `_ativar_figura_2d` / `_ativar_figura_3d` — garantem a janela certa ativa antes de plotar.
- `clear_plots(setup=None)` — `c` (painel/janela 2D ou 3D, conforme a ativa).
- `set_window_title(titulo)` / `set_ion()` — título da janela / modo interativo.
- `save_fig(fig_name, setup)` — `gxprint`.
- `_niveis_cor(setup)` — níveis de cor/contorno (`set clevs` ou padrão).
- `_tamanho_malha_ok`, `_aplicar_corte`, `_mask_corte` — validações e aplicação de `set cut`.

### `map_func.py`
- `plot_map(setup, ax)` — mapa de fundo 2D.
- `plot_map_3d(setup, ax3d)` — mapa de fundo projetado na superfície 3D (`d3` + `draw map`).

### `utils.py`
- `normalize_lon(lon)` — normaliza longitude para (-180, 180].
- `mag(u, v)` — magnitude vetorial.
- `sem_mascara(arr)` — converte array mascarado do `netCDF4` (`numpy.ma.MaskedArray`) para array comum com `NaN`, evitando que `scipy`/`Delaunay`/`cKDTree` rejeitem o dado.
- `assinatura_malha(latitudes, longitudes)` — nº de células + hash `md5` de lat/lon, usada para validar que arquivos abertos na mesma sessão compartilham a mesma malha (seção 2.1).
- `load_zgrid_centers(...)` — extrai e alinha a variável `zgrid`.
- `encontrar_posicao_mais_proxima(...)` — busca binária.
- `custom_input()` / `load_history` / `save_command_to_history` — prompt com histórico.

---

## 13. Requisitos de arquivo

- **Sempre necessário**: as variáveis a serem plotadas.
- **Malha**: `nCells` e `latCell`/`lonCell`, embutidos ou num arquivo de grade externo (seção 10 do manual anterior mantém-se válida: vários cenários de ausência são tratados sem travar).
- **Tempo** (opcional, com valores de reserva): `xtime`, `initial_time`.
- **Níveis de pressão** (opcional): `t_iso_levels`. Sem isso, usa índice de nível do modelo.
- **Altura real** (opcional, corte/perfil/`d3` por altura): `zgrid`.
- **`voronoi`/`shaded`/`contour`/corte/`streamlines`**: só precisam de `latCell`/`lonCell` — não é mais necessária a conectividade completa (`verticesOnCell` etc.), que era usada por uma implementação antiga do `voronoi` já substituída pela rasterização via `cKDTree`.
