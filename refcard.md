# GradsMonanApp — Guia rápido

*A4 paisagem, 3 painéis por face (dobrar em 3). Letra 8 pt. Detalhes: `userManual.md`; no programa: `help [comando]`.*

## 1 · Sessão e arquivos

```
open a.nc [grade.nc]  abre (aceita * ? [..])
open dir/*.nc         abre vários, ordem alfab.
reset   limpa seleções e gráfico (mantém abertos)
reinit  fecha tudo, volta ao início
run s.txt     executa script (1 cmd/linha)
load limits p.csv   polígono p/ "inlimits"
debug on|off  off = só erros e resultados
help [cmd]    ajuda (ex.: help sel)
! cmd | exec cmd    comando do shell
q | exit | quit     sai
```

**Arquivos (vários abertos)**
```
show files        lista nº, nome, timestamp
show timestamp 5  timestamp do arquivo 5
show times        tempos selecionados
set t 3           arquivo padrão = 3
set t 2 9         série/animação 2 a 9
set tint 0.5      s entre quadros
d t2m.4           variável do arquivo 4
```

**Prompts**
```
>    ok     E>  erro     ?>  não reconhecido
```

**Variáveis do usuário**
```
let tg = temp.2/geo.2
tc = t2m-273.15       (let é opcional)
let        lista      undef tc   remove
```
Funções: `sqrt abs log exp sin cos mag`…

## 2 · Plotar (d, d3)

```
d t2m            mapa 2D (set lev = nível)
d t2m-273.15     expressão
d u;v            vento (set gxout vect)
d temp           perfil, se lat e lon fixos
d temp           corte, se só lat OU lon fixo
d3 temp          3D (faixas em lat, lon, lev)
c                limpa o gráfico
gxprint f.png    salva (png, pdf, …)
write csv f      grava todas as curvas em CSV
```

**O que `d` plota (lat × lon × lev)**
```
lat, lon intervalos   → mapa (nível único)
lat e lon fixos       → perfil vertical
só uma fixa           → corte vertical
set t a b + ponto     → série temporal
set t a b + faixa     → Hovmöller (cor)
```

**set gxout**
```
shaded contour voronoi hex     (escalar)
vect stream barb               (vento)
```

**Páginas**
```
set pages 1 2    painéis (lin col)
set page 1 2     painel ativo
```
Marker, plot, legend, ranges/div/tics, grid, títulos e rótulos valem só no painel ativo.

**CSV** (`write csv nome`): todas as curvas na tela, 1 coluna cada; série → 1ª coluna = tempo; perfil → 1ª = nível. Só gráfico de **linha** ainda na tela.

## 3 · set — domínio e show

```
set lat -30 10   intervalo     set lat -22  ponto
set lon -80 -30  intervalo     set lon -46  ponto
set lat | set lon  (sem args) = domínio completo
set lev 5        nível (índice)
set lev 0 9      faixa (inclusiva)
set cut -5 5     só plota nesta faixa
set cut          desliga o cut
```
Nível: pressão, altura do modelo ou solo — depende da variável (`show levels`).

**show**
```
show info       arquivo, dims, variáveis,
                set e sel atuais
show variables  show levels [tipo]
show lev        show lat   show lon
show files      show times
show timestamp [n]
show sel        show limits
show title|label|map|cmap
show setup      show fonts
```

**Grade regular lat×lon**: detectada pelo conteúdo do arquivo; cada ponto vira uma "célula".

**Muitos arquivos** (milhares): abertos sob demanda; use `debug off`.

## 4 · Estatísticas, sel e acum

```
sum|mean|min|max|p10..p90  ESCOPO  var
```
ESCOPO:
```
all       toda a malha
inlimits  dentro de "load limits"
point     + faixa de níveis
```
```
mean all t2m          → 1 número
d mean all t2m        → mapa ponto a ponto
d mean point temp     → perfil (set lat/lon)
```

**Região e período (sel, não set!)**
```
sel                 mostra
sel lat 10 30       faixa de latitude
sel lon 350 10      cruza o meridiano 0
sel t 2 8           arquivos 2 a 8
sel lat|lon|t clear parte    sel clear  tudo
```

**Estatística no tempo (um valor/arquivo)**
```
sum sel t2m         tabela
d sum sel t2m       curva no tempo
d mean sel temp     usa set lev (ou faixa)
d acum sum sel chuva  acumulado no tempo
acum sum sel chuva  tabela acumulada
d max sel t2m-273.15  aceita expressão/let
```
`acum` soma célula a célula no tempo, ignora NaN, depois aplica a estatística na região.

## 5 · set — eixos, texto, marcadores

**Eixos**
```
set xrange 0 30    limites X (off = auto)
set xrange 2024-01-01T00 2024-01-02T00  (tempo)
set yrange 0 1000  limites Y (off = auto)
set xdiv 5         divisão em X (tempo: horas)
set ydiv 100       divisão em Y
set xtics on|off   marcas/valores do eixo X
set ytics on|off   idem Y
```
`reset` volta range/div ao automático.

**Marcadores (gráficos de linha)**
```
set marker on|off
set marker type D|auto  o s D * ^ v < > p h + x
set marker size 8
set marker color red   (default = da linha)
set marker text on|off  valor em cada ponto
```

**Curvas e legenda** (plot1, plot2…)
```
cada gráfico de linha = plot1, plot2…
  cores ANSI 30–37 + marcadores o s D * ^ v < > p h + x
  em sequência; `c` recomeça em plot1
set plot 2 color blue|marker D|markersize 9
set plot 2 linetype tracejada|linesize 2
set plot 2 label Controle   set plot 2 default
set legend on|off           legenda do PAINEL atual
set legend position L|R|U|D esq. dir. acima abaixo
draw legend title Título
set legend title size 12    color red
set legend line 2           linetype pontilhada
show plots   tabela Plot # / Variable / Color / Marker
```

**Grade**
```
set grid on|off    color <cor>   size <n>
set grid type tracejada
 cheia tracejada traco-ponto pontilhada
 ou dash:6,2,1,2 e estilos do matplotlib
```

**Textos** (`label` `title` `xlabel` `ylabel`)
```
set title font Arial    set title size 14
set xlabel color blue   set ylabel style bold
(style: bold italic normal)  show fonts
```

## 6 · draw, cores e mapa

```
draw title Meu título
draw label K            barra de cores
draw xlabel Hora        draw ylabel T (K)
draw mark -23 -46 3     símbolo 1–11 no mapa
draw map  /  draw map off   mapa de fundo
draw legend
```

**Cores**
```
set cmap jet|viridis|…
set clevs 0 10 20 30 40   fronteiras de cor
set background black      fundo (default)
set bar position U|D|L|R  barra de cores
```

**Contorno** (`set gxout contour`)
```
set contour line size 0.5
set contour line bw|color
set contour font Arial
set contour font color|size|style <v>
```

**Mapa de fundo**
```
set mappat /dir/shapes   diretório
set mpdset Brasil.shp    shapefile
set mpt black 0.3        cor e espessura
```

**Figura**
```
set fig_dpi 300
set fig_inches tight
set fig_transparency true
gxprint fig.png
```

**Exemplo**
```
open dir/*.nc
sel lat -25 -20
sel lon -48 -42
set xdiv 12
d acum sum sel chuva
write csv chuva_acum
```
