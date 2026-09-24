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
| `open <arquivo.nc> [grade.nc]` | Abre um arquivo NetCDF de saída do MONAN/MPAS. Pode ser chamado **mais de uma vez na mesma sessão**, para trabalhar com vários arquivos ao mesmo tempo — ver seção 2.1. `<arquivo.nc>` também aceita **wildcards** (`*`, `?`, `[...]`), abrindo em sequência todos os arquivos que derem match (ordem alfabética dos nomes — ver seção 2.1). O segundo argumento (opcional) é um arquivo de grade externo — necessário quando o arquivo de dados não traz `latCell`/`lonCell`/`nCells` embutidos. Ver seção 10 para o detalhe de cada caso. Qualquer falha (inclusive um arquivo com malha diferente da já aberta) avisa e **mantém a sessão anterior intacta**, sem encerrar o programa. |
| `load limits <arquivo.csv>` | Carrega uma área fechada (polígono) a partir de um arquivo de pontos lat/lon, marca quais células da malha aberta caem dentro dela e plota um mapa de conferência — ver seção 2.2. |
| `sum`/`mean`/`min`/`max`/`p10`..`p90` `all\|inlimits\|point <variavel>` | Imprime uma estatística (soma, média, mínimo, máximo ou percentil) da variável — em todas as células da malha, só nas de dentro da última área de `load limits`, ou (`point`) reduzindo também sobre a faixa de níveis selecionada, mesmo sem um ponto/corte fixado; agregando todos os arquivos do intervalo de `set t`, quando houver mais de um — ver seção 2.3. |
| `d sum\|mean\|min\|max\|p10..p90 all\|inlimits\|point <variavel>` | Como acima, mas plota o resultado **ponto a ponto** (um mapa, perfil ou corte), em vez de reduzir a um único número — ver seção 2.3. |
| `reinit` | Fecha **todos** os arquivos abertos na sessão, apaga toda a configuração associada a eles (inclusive os caches de triangulação em memória) e volta ao estado inicial, pronto para um novo `open`. Também limpa a janela de gráficos. |
| `reset` | Volta a seleção de **latitude/longitude/nível/corte (`set cut`)/arquivo (`set t`)** para a condição inicial (toda a malha, nível padrão da configuração, corte desligado, arquivo 1, série/animação desligada) e **limpa** título, rótulo de linha/legenda, rótulo da colorbar, o mapa de fundo automático (`draw map`) e o gráfico atual — mas **mantém os arquivos abertos** (ao contrário de `reinit`). Ver detalhes abaixo. |
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
exige um arquivo aberto; sem isso, o programa avisa e volta ao prompt (`reset`
inclusive — sem nenhum arquivo aberto, avisa e não faz nada).

**`reset` vs. `reinit`**: `reinit` fecha os arquivos e começa do zero (é
preciso um novo `open`); `reset` é mais leve — mantém o(s) arquivo(s) já
aberto(s) (e tudo o que foi lido deles: variáveis, malha, arquivos
adicionais de `open`/`set t`), só devolvendo à condição inicial a
**seleção espacial** (`set lat`/`set lon`/`set lev`, que voltam a cobrir
toda a malha, no nível padrão da configuração; `set cut`, que é
desligado; e `set t`, que volta ao arquivo 1 e desliga a série/animação
entre arquivos) e **limpando** o que foi desenhado/rotulado (`draw title`,
`set label`, `draw label`, `draw map`, e o próprio gráfico na tela —
equivalente a um `c`). Útil para recomeçar uma nova análise nos mesmos
arquivos, sem o custo de reabri-los:

```
> set lat -22
> set lon -46
> set lev 5
> set cut -5 5
> set t 8
> draw title Perfil em Sao Paulo
> draw label Vento (m/s)
> reset
Reset: lat/lon voltaram para toda a malha, nivel 0, arquivo 1; titulo, rotulos, corte (cut) e mapa limpos. Arquivos abertos mantidos.
> d t2m
```

**Importante**: antes desta correção, `set cut` **não** era desligado por
`reset` — um corte estreito deixado ligado ao testar uma variável (ex.
`set cut -5 5` para uma temperatura em °C) continuava filtrando
silenciosamente **todas as variáveis seguintes**, mesmo depois de um
`reset`, fazendo campos com valores fora dessa faixa (como ozônio em
ppmv) aparecerem quase todos como `NaN`/vazios — um mapa com apenas o
contorno da malha e uma cor quase constante (colorbar num intervalo
minúsculo, tipo ±1e-14), sem nenhum erro impresso. Se isso já aconteceu
com você, o `reset` atualizado resolve; se persistir mesmo com `cut`
desligado (`show setup` mostra `'cut': None`), pode ser a própria variável
que não tem dado válido naquele nível específico — experimente `d o3` em
outros níveis (`set lev <n>`) para comparar.

`load limits` (seção 2.2), `set clevs`/`set gxout`/`set cmap` e as marcas
de `draw mark` **não** são alterados por `reset` (só a seleção espacial —
incluindo `cut` e `set t`, arquivo/série — e os elementos de rótulo/mapa
listados acima).

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
- **Wildcards**: `open <padrão>` aceita `*`, `?` e `[...]` no nome do
  arquivo. Nesse caso, todos os arquivos que derem match são abertos em
  sequência, em ordem alfabética (que normalmente corresponde à ordem
  cronológica, já que os nomes trazem a data/hora), cada um recebendo o
  próximo número disponível. A mesma validação de malha (abaixo) vale para
  cada arquivo do lote: um arquivo do padrão com grade diferente é pulado
  (com aviso), sem interromper a abertura dos demais. Exemplo:
  ```
  > open SP_O_2022071400_2022071400.00.00.x40962L55.nc  grade.nc
  > open SP_O_2022071400_20220714*.nc                   grade.nc
  ```
  (o argumento de grade externo, se necessário, é opcional e vale igual
  para todos os arquivos do padrão.)
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

### Escolhendo um arquivo entre vários abertos (`d <var>.N` e `set t <n>`)

Com mais de um arquivo aberto (seção 2.1), há **duas formas equivalentes**
de escolher qual arquivo `d`/`d3` (ou as estatísticas da seção 2.3) usam
quando não estiver no modo de série/animação (abaixo):

- **Pontual, só para uma chamada**: o sufixo `.N` na própria variável —
  `d o3.8` mostra o arquivo número 8 uma única vez, sem afetar chamadas
  seguintes.
- **Persistente, para as próximas chamadas**: `set t <n>` (ou
  `set time <n>`, um único argumento) seleciona o arquivo número `<n>`
  como o arquivo **padrão** — toda variável **sem** sufixo `.N` (`d o3`,
  `d t2m`, `mean all o3`, etc.) passa a usar esse arquivo, até o próximo
  `set t <n>` (ou um `reset`/`reinit`, que voltam ao arquivo 1):

```
> open SP_O_2022071400_20220714*.nc
> set lev 45
> set t 8
Arquivo 8 selecionado: SP_O_2022071400_2022071407.00.00.x40962L55.nc (2022-07-14T07).
> d o3
> d co2
```

(as duas chamadas de `d` acima usam o arquivo 8; um sufixo `.N` explícito,
se usado numa delas, vale só para aquela chamada, sem mudar a seleção de
`set t`.) Sem nenhum `set t`/sufixo, o padrão é o arquivo 1 (o primeiro
aberto). `set t <n>` fora do intervalo de arquivos abertos (ex: `set t 30`
com só 24 abertos) avisa com uma mensagem clara e não altera a seleção
anterior.

`set t <arquivo_inicial> <arquivo_final>` (**dois** argumentos — inclusive
iguais, ex: `set t 3 3`) é um comando **diferente**: liga o modo de
**série temporal/animação** entre um intervalo de arquivos, descrito no
restante desta seção — não confundir com `set t <n>` (um argumento),
acima, que só troca o arquivo padrão de uma chamada simples.

**As duas formas são modos mutuamente exclusivos** — vale sempre o último
`set t` usado: um `set t <n>` (um argumento) **desliga** o modo de série,
mesmo que um `set t <inicio> <fim>` tenha ligado ele antes na mesma
sessão. Isso é necessário porque, no modo de série, `d`/`d3` só aceitam
**uma** dentre latitude/longitude/nível como faixa (as outras duas
precisam ser um ponto/nível único — ver a tabela abaixo); pedir um
arquivo/tempo único com `set t <n>` normalmente vem acompanhado de um
corte de verdade (lat/lon fixa **e** uma faixa de níveis, por exemplo),
que só faz sentido fora do modo de série:

```
> set t 1 24          (liga o modo serie/animacao)
> set t 5              (pontual: desliga a serie, seleciona so o arquivo 5)
> set lat -22
> set lev 1 54
> d o3                 (corte normal no arquivo 5, sem restricao de serie)
```

A partir daí, `d <variavel>` (ou `d3 <variavel>`) — em forma simples ou
como **expressão aritmética** (mas ainda sem `mag(...)` nem `<u>;<v>`) —
passa a considerar todos os arquivos do intervalo, em vez de um só. O que
ele plota depende de `set lat`/`set lon`/`set lev`:

```
> open SP_O_2022071400_20220714*.nc
> set t 1 24
> set lat -22
> set lon -55
> set lev 0
> d t2m-273.15
```

| Seleção de lat/lon/nível | Resultado de `d <variavel>` |
|---|---|
| Latitude **e** longitude fixadas num ponto único | **Gráfico de linha**: valor da variável (na célula mais próxima do ponto) x tempo, um ponto por arquivo do intervalo. |
| Latitude, longitude ou nível como uma **faixa única** (as outras duas num ponto/nível fixo) | **Diagrama tipo Hovmöller**: tempo no eixo X, a dimensão em faixa (latitude, longitude ou nível — com a mesma hierarquia pressão/altura/índice da seção 8) no eixo Y, valor da variável na cor, com barra de cores. |
| Nem latitude nem longitude fixadas num ponto (mapa horizontal "normal") | **Animação**: plota o mapa de cada arquivo do intervalo, em sequência, na mesma janela, aguardando `set tint <segundos>` entre cada quadro (ver abaixo). O timestamp de cada arquivo aparece anexado ao título do gráfico, quadro a quadro. |
| Mais de uma das três (lat, lon, nível) como faixa ao mesmo tempo — exceto o caso do mapa acima | Não suportado: avisa e não plota (ambíguo demais para um único gráfico). |

`d3 <variavel>` no modo de série temporal sempre anima (precisa de faixas
reais em lat/lon/nível de qualquer forma — regra normal do `d3`, seção 4):
plota o quadro de cada arquivo do intervalo, em sequência, na mesma janela
3D, aguardando `set tint` entre cada um.

`set tint <segundos>` define o intervalo, em segundos, entre os quadros da
animação (`d`/`d3` no modo mapa/3D acima). Padrão: 1 segundo. Fica
guardado no `setup` da sessão (seção 11), valendo para toda animação
seguinte até ser trocado. Exemplo:

```
> set tint 0.5
> d t2m
```

Um sufixo `.N` na variável simples (`d t2m.2`, por exemplo) é **ignorado**
nesse modo, com um aviso — o arquivo já vem do intervalo de `set t`.

### Expressões aritméticas no modo de série temporal

`d <expressão>` também funciona no modo de série temporal — por exemplo,
para converter unidades ao longo do tempo:

```
> set t 1 24
> d t2m-273.15
> d (t2m - 273.15) * 1.0
```

Dentro da expressão, cada nome de variável **sem** sufixo `.N` é resolvido
no arquivo do **próprio quadro** (o arquivo daquele instante da série) —
não sempre no arquivo 1. Um nome **com** sufixo `.N` explícito continua
fixo naquele arquivo específico em todos os quadros — útil para calcular
uma anomalia contra um arquivo de referência:

```
> d t2m - t2m.1        (anomalia de cada arquivo em relação ao primeiro)
```

### Título e rótulo da barra de cores entre quadros/plots

**Mapa de fundo e níveis de cor**: `set clevs` (faixas de cor fixas) já
vale automaticamente para qualquer plot seguinte, animado ou não — é uma
configuração de sessão como outra qualquer, e não é resetada em nenhum
momento. O mapa de fundo (`draw map`), por sua vez, antes precisava ser
chamado de novo a cada plot para continuar visível (cada novo `d`/`d3`
reaproveita ou limpa o mesmo eixo); agora, `draw map` liga um modo
persistente (ver tabela da seção 7) que o redesenha automaticamente em
cima de cada plot seguinte — inclusive quadro a quadro na animação — até
um `draw map off`.

**Título** (`draw title <texto>`) e **rótulo da barra de cores**
(`draw label <texto>`), definidos antes de um `d`/`d3`, também ficam
**preservados** em todo plot seguinte, incluindo quadro a quadro na
animação (cada eixo é limpo e redesenhado a cada quadro — sem essa
persistência, o título/rótulo sumiriam depois do primeiro quadro). No caso
do título, durante a animação o timestamp de cada arquivo é anexado a ele,
quadro a quadro, voltando ao texto original ao final:

```
> draw title Temperatura a 2m
> draw label Temp. (C)
> set t 1 24
> d t2m-273.15
```

Não é preciso que já exista um gráfico para usar `draw title`/`draw
label`: se chamados antes de qualquer `d`/`d3`, o texto fica guardado e
passa a valer automaticamente assim que o primeiro gráfico (com barra de
cores, no caso do `draw label`) for criado.

### Título da janela (barra superior)

Não confundir com `draw title` (o título **do gráfico**, acima): o
título da **janela** do matplotlib (a barra no topo da janela do
sistema operacional) já é atualizado automaticamente ao **abrir** o(s)
arquivo(s) (`open`, seção 2.1 — cobrindo toda a malha, no nível padrão,
sem precisar de nenhum `set` antes), e sempre que a seleção de
tempo/arquivo (`set t`), latitude (`set lat`), longitude (`set lon`) ou
nível (`set lev`) muda depois disso — inclusive por um `reset`. Formato:

```
GradsMonan: <timestamp>,<latitude(s)>,<longitude(s)>,L<nível(is)>
```

- **Timestamp**: o do arquivo/tempo atualmente selecionado (o primeiro
  do intervalo, no modo de série/animação; o arquivo pontual de `set t
  <n>`, fora dele).
- **Latitude(s)**: um valor único, sempre com **2 casas decimais** (ex.
  `22.00S`) quando um ponto está selecionado, ou uma faixa
  `x<suf>-y<suf>` (ex. `10.00S-5.00N`) quando há uma faixa — sufixo `S`
  para negativo (sul), `N` para positivo (norte).
- **Longitude(s)**: mesma ideia (2 casas decimais), sufixo `W` para
  negativo (oeste), `E` para positivo (leste) — ex. `60.00W-30.00W`.
- **Nível(is)**: sempre prefixado com `L` — um único índice (ex. `L3`),
  ou `L<inicial>-<final>` (ambos inclusivos, ex. `L1-45`) quando há uma
  faixa de níveis.

Exemplo:

```
> open SP_O_2022071400_2022071404.00.00.x40962L55.nc
> set t 5
> set lat -22
> set lon -60 -30
> set lev 1 45
```

deixa o título da janela como
`GradsMonan: 2022-07-14T04,22.00S,60.00W-30.00W,L1-45`.

---

## 2.2 Área de limites para estatísticas (`load limits`)

`load limits <arquivo.csv>` carrega uma **área fechada** (polígono) a
partir de um arquivo de texto/CSV com uma lista de pontos — um por linha,
no formato `latitude<separador>longitude` — e marca quais células da
malha aberta (os mesmos centros de `latCell`/`lonCell`) caem **dentro**
dela. Essa seleção fica pronta para ser reaproveitada pelas próximas
funções estatísticas dentro da área (média, mínimo, máximo, etc.), que
não precisarão refazer esse cálculo.

O separador entre latitude e longitude, em cada linha, pode ser vírgula,
ponto-e-vírgula ou espaço (e combinações deles, como `", "`). Linhas
vazias e comentários (iniciados por `#`) são ignorados; uma linha que não
resulte em exatamente dois números (por exemplo, um cabeçalho `lat,lon`)
é ignorada com um aviso, sem interromper a leitura do restante do
arquivo. O polígono não precisa repetir o primeiro ponto no final — ele é
sempre tratado como fechado (o último ponto liga de volta ao primeiro).

Exemplo de arquivo (`bacia.csv`):

```
lat,lon
-22.0,-55.0
-22.0,-45.0
-15.0,-45.0
-15.0,-55.0
```

Uso:

```
> open SP_O_2022071400_2022071400.00.00.x40962L55.nc
> load limits bacia.csv
Limites carregados de 'bacia.csv': 4 ponto(s) no poligono, 8532 celula(s) da malha dentro da area.
```

O comando plota, na hora, um **mapa de conferência**: o contorno do
polígono lido (linha preta) e todos os centros de célula da malha,
destacando em vermelho os que caíram dentro da área (os demais aparecem
em cinza claro, só para dar contexto espacial) — assim dá para checar
visualmente se a área foi lida corretamente antes de rodar qualquer
estatística sobre ela. `show limits` (seção 5) resume o que está
carregado sem replotar o mapa.

O resultado fica guardado no `setup` da sessão (seção 11):
`limits_poligono`, `limits_mask`, `limits_indices`, `limits_arquivo`. Um
novo `load limits` **substitui** a área anterior; se o arquivo informado
não existir, não puder ser lido, ou não tiver pelo menos 3 pontos válidos,
a área anterior (se houver) é **preservada** — o comando avisa e não
altera nada.

---

## 2.3 Funções estatísticas (`sum`, `mean`, `min`, `max`, `p10`..`p90`)

O módulo `estatistics.py` reúne funções estatísticas sobre a variável (ou
uma **expressão aritmética** sobre variáveis, ex: `t2m-273.15` — seção
3), usando **exatamente a mesma seleção espacial que `d`/`d3` usariam
para plotar agora mesmo** (seção 8), conforme `set lat`/`set lon`/`set
lev`:

- **Mapa horizontal** (nem latitude nem longitude fixadas num único
  ponto — o caso comum): todas as células da malha, no **nível único**
  selecionado (`set lev <nivel>`).
- **Ponto** (`set lat <x>` + `set lon <y>`, fixando os dois no mesmo
  valor): a estatística vira um **perfil vertical**, calculado na célula
  mais próxima desse ponto, ao longo da **faixa de níveis** selecionada
  (`set lev <nivel_inicial> <nivel_final>`).
- **Corte** (só `set lat` OU só `set lon` fixada, sem a outra): a
  estatística usa todas as células da malha, também ao longo da faixa de
  níveis selecionada.

Nos modos **ponto** e **corte**, se nenhuma faixa de níveis tiver sido
definida explicitamente (`set lev <inicial> <final>`) — ou seja, `set
lev` só selecionou um nível único —, a estatística usa exatamente esse
nível (comportamento igual ao do modo mapa, um só nível por vez).

Há duas formas de usar cada estatística:

- **Escalar** (`<estatística> all|inlimits|point <variável>`, sem `d` na
  frente): reduz a variável a **um único número**, impresso na tela antes
  do próximo prompt; nenhum gráfico é alterado.
- **Espacial** (`d <estatística> all|inlimits|point <variável>`): calcula
  o resultado célula a célula (ou nível a nível, nos modos ponto/corte) e
  plota exatamente como `d`/`d3` plotariam a própria variável agora —
  mapa, perfil vertical ou corte vertical, conforme a seleção acima
  (mesmas regras de `gxout`, mapa de fundo, título e colorbar do `d`
  normal). Exceção: com `point` e nenhum ponto/corte fixado (mapa
  horizontal) mais uma faixa de níveis selecionada, não há um mapa nem um
  corte bem definido para plotar (ver complemento `point`, abaixo) — a
  forma espacial avisa e não plota; use a forma escalar nesse caso.

### O complemento `point` — estatística sobre o perfil temporal/vertical

Além de `all`/`inlimits`, todo comando de estatística aceita o
complemento **`point`** (ex.: `max point <variável>`, `d sum point
<variável>`): pede explicitamente a estatística sobre o **perfil
temporal e vertical** da seleção atual — reduzindo também sobre a **faixa
de níveis** selecionada (`set lev <inicial> <final>`), mesmo quando nem
latitude nem longitude estão fixadas (mapa horizontal). Isso permite
combinar **qualquer variação** dos quatro componentes de seleção
(latitude, longitude, nível, tempo) — por exemplo:

- Um ponto (lat e lon fixos) e um único nível, com vários arquivos/tempos
  (`set t <inicio> <fim>`).
- Um único tempo, uma latitude e várias longitudes (corte), ou uma lat e
  uma lon (ponto).
- Um único tempo, com vários níveis, no mapa inteiro (nem lat nem lon
  fixa) — combinação que só `point` cobre, já que `all`/`inlimits` olham
  para um nível só nesse caso.

Nos modos **ponto** e **corte**, `point` se comporta exatamente como
`all` (a única diferença que `point` acrescenta é ativa apenas no modo
mapa, sem lat/lon fixados). No **modo mapa com uma faixa genuína de
níveis selecionada**, `point` reduz também sobre os níveis — um modo
interno chamado aqui de "mapa com níveis": a forma escalar (`mean point
u10`, por exemplo) funciona normalmente, reduzindo células, níveis e
tempos a um único número; a forma espacial (`d mean point u10`) **não
tem como plotar** esse resultado (não há uma direção de corte definida
sem lat ou lon fixada) e avisa em vez de arriscar um gráfico incorreto —
use a forma escalar, ou fixe `set lat`/`set lon` (num único ponto, para
um perfil, ou só um dos dois, para um corte) para poder plotar.

Em ambas as formas, **quando houver mais de um arquivo aberto com um
intervalo definido por `set t <arquivo_inicial> <arquivo_final>`**
(seção 2.1), a estatística usa **todos os arquivos (tempos) desse
intervalo** — cada arquivo conta como um "tempo" a mais na conta. Sem
`set t` ativo (ou com um só arquivo aberto), a estatística usa só o
arquivo/instante atual, como antes (o sufixo `.N` de arquivo, seção 2.1,
continua funcionando nesse caso — inclusive dentro de uma expressão, ex:
`mean all (t2m.1 - t2m.2)`; dentro do modo de série, o sufixo é ignorado
com aviso — quem manda é o intervalo de `set t`, igual ao `d`/`d3` em
série).

As estatísticas disponíveis:

| Comando | O que calcula |
|---|---|
| `sum` | Soma. |
| `mean` | Média. |
| `min` | Mínimo. |
| `max` | Máximo. |
| `p10`, `p20`, ..., `p90` | Percentis 10 a 90 (de 10 em 10). |

Todas as estatísticas acima têm as duas formas (escalar e espacial) e os
três complementos abaixo.

E as três variantes de seleção espacial, para todas as estatísticas acima:

- `all` — usa **todas** as células da malha aberta (ou, no modo ponto, o
  próprio ponto selecionado, sem restrição).
- `inlimits` — usa apenas as células dentro da **última área carregada**
  com `load limits` (seção 2.2). Sem nenhuma área carregada, o comando
  avisa e não calcula nada. Nos modos mapa/corte, na forma espacial
  (`d ... inlimits ...`), as células de fora da área ficam com **NaN** no
  mapa/corte (não aparecem plotadas, igual a um `set cut`); no modo
  ponto, `inlimits` apenas confere se o ponto selecionado cai dentro da
  área — se não cair, avisa e não calcula nada (não há mais células para
  restringir).
- `point` — estatística sobre o perfil temporal/vertical (ver seção
  acima): igual a `all` nos modos ponto/corte; no modo mapa, reduz
  também sobre a faixa de níveis selecionada, quando houver uma (a forma
  espacial não plota esse caso — só a escalar).

Se a variável (ou expressão) for bidimensional (sem dimensão de nível,
ex: `t2m`), a seleção de ponto/corte não se aplica (mesma regra do
`d`/`d3` — só faz sentido para variáveis com nível) e o nível não aparece
na mensagem. Se for tridimensional (ex: `u10`), a estatística usa o
nível (mapa) ou a faixa de níveis (ponto/corte) atualmente selecionados,
e a mensagem indica qual foi usado.

Exemplos (forma escalar, mapa horizontal):

```
> open SP_O_2022071400_2022071400.00.00.x40962L55.nc
> sum all t2m
Soma de 't2m' (todos os 8532 ponto(s) da malha): 2394871.5

> mean all t2m-273.15
Media de 't2m-273.15' (todos os 8532 ponto(s) da malha): 12.4

> set lev 5
> mean all u10
Media de 'u10' (todos os 8532 ponto(s) da malha, nivel 5 = 850.0 hPa): 4.92

> load limits bacia.csv
Limites carregados de 'bacia.csv': 4 ponto(s) no poligono, 812 celula(s) da malha dentro da area.
> max inlimits t2m
Maximo de 't2m' (dentro dos limites, 812 celula(s)): 305.1

> p90 all t2m
Percentil 90 de 't2m' (todos os 8532 ponto(s) da malha): 301.4
```

Exemplo com vários arquivos (série temporal, seção 2.1) — a estatística
passa a considerar todos os tempos do intervalo:

```
> open SP_O_2022071400_2022071400.00.00.x40962L55.nc
> open SP_O_2022071400_2022071406.00.00.x40962L55.nc
> open SP_O_2022071400_2022071412.00.00.x40962L55.nc
> set t 1 3
> mean all t2m
Media de 't2m' (todos os 8532 ponto(s) da malha, 3 tempo(s)): 296.7
```

Exemplo com um **ponto** selecionado (perfil vertical) e um **corte**
(só latitude fixa):

```
> set lat -22
> set lon -46
> set lev 0 19
> mean all u10
Media de 'u10' (ponto lat -22, lon -46, niveis 0-19): 3.7

> set lon -180 180
> max all u10
Maximo de 'u10' (todos os 8532 ponto(s) da malha, niveis 0-19): 41.2
```

Exemplo da forma espacial — plota a média (ponto a ponto, ao longo dos 3
tempos acima) como um mapa comum; com um ponto ou corte selecionados
(como acima), plota um perfil ou corte vertical no lugar do mapa. `sum`
também tem forma espacial:

```
> d mean all t2m
> d min inlimits t2m
> d sum all t2m
```

Exemplo do complemento `point` — perfil temporal/vertical, em qualquer
combinação de ponto/lon/lat/nível/tempo:

```
> set lat -22
> set lon -46
> set lev 3
> set t 1 3
> mean point u10
Media de 'u10' (ponto lat -22, lon -46, 3 tempo(s), niveis 3-3): 4.1

> set lat -90 90
> set lon -180 180
> set lev 0 19
> mean point u10
Media de 'u10' (todos os 8532 ponto(s) da malha, 3 tempo(s), niveis 0-19): 3.8
> d mean point u10
Aviso: nao e possivel plotar a estatistica espacial com uma faixa de niveis
sem fixar latitude e/ou longitude (perfil ou corte) - use a forma escalar
('mean point <variavel>'), ou fixe 'set lat'/'set lon' num unico ponto
(perfil) ou so um dos dois (corte).
```

---

## 3. Sintaxe do comando `d` / `display` (2D)

| Forma | Efeito |
|---|---|
| `d <variavel>` | Plota a variável diretamente do arquivo (mapa, corte vertical ou perfil, dependendo de `lat`/`lon`/`lev` selecionados — ver seção 8). |
| `d (<expressão>)` | Avalia uma expressão aritmética (`+ - * / **` e parênteses) substituindo os nomes de variáveis do arquivo, e plota o resultado. Ex.: `d t2m-273.15`, `d (t2m - 273.15)`, ou cruzando arquivos: `d (t2m.2 - t2m.1)`. Avaliação restrita (sem acesso a funções do Python) — variáveis/arquivos não encontrados são reportados com sugestões. Também funciona no modo de série temporal entre arquivos (seção 2.1), onde cada nome sem sufixo `.N` é lido do arquivo do próprio quadro. |
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
| `show files` | Tabela com **todos** os arquivos abertos na sessão: número, nome do arquivo e timestamp (data/hora, quando disponível) — ver seção 2.1. Se nenhum arquivo estiver aberto, informa isso. |
| `show times` | Tabela (número + timestamp) só com o(s) tempo(s) **atualmente selecionado(s)** por `set t` (seção 2.1/6): todos os arquivos do intervalo, um por linha, se o modo de série/animação estiver ligado (`set t <inicio> <fim>`); senão, uma única linha, o arquivo/tempo pontual selecionado (`set t <n>`, padrão o arquivo 1). |
| `show latitudes` / `show longitudes` | Lista de coordenadas da malha, ordenada. |
| `show levels` | Lista de níveis (pressão em hPa, ou índice de nível). |
| `show lev` | Nível/intervalo de nível atualmente selecionado. |
| `show variables` | Lista de variáveis do arquivo com sua descrição (`long_name`). |
| `show time_variable` / `show time_units` / `show Date` | Informações de tempo do arquivo (com valores de reserva se ausentes). |
| `show title` / `show label` | Título do gráfico / rótulo da barra de cores atuais. |
| `show map` | Lista os shapefiles disponíveis em `mappath`, marcando o selecionado. |
| `show map_color` / `show map_line` | Cor/espessura da linha do mapa de fundo. |
| `show lat` / `show lon` | Intervalo de latitude/longitude atualmente selecionado. |
| `show cmap` | Colormap atual. |
| `show setup` | Imprime o dicionário `setup` inteiro (debug). |
| `show limits` | Resumo da área de limites carregada por `load limits` (seção 2.2): arquivo, número de pontos do polígono e quantas células da malha caem dentro dela. Avisa se nenhuma área foi carregada ainda. |

---

## 6. Comandos `set <opção>`

Todos os termos numéricos são validados: erro de conversão ou argumento
faltando avisa e **mantém a configuração anterior**, sem travar.

| Comando | Efeito |
|---|---|
| `set lev <n>` | Nível único. Imprime a informação do nível: pressão em hPa, senão altura média (`zgrid`), senão só o índice. |
| `set lev <n1> <n2>` | Intervalo de níveis, **ambos inclusivos** (corte vertical, perfil, `d3`) — `<n1>` e `<n2>` são índices de nível válidos, de `0` a `n_niveis-1` (a mesma faixa aceita por `set lev <n>`), e o nível `<n2>` **entra** na seleção. `<n1>` não pode ser maior que `<n2>`. Um corte vertical/`d3` precisa de pelo menos 2 níveis na faixa; um perfil (seção 8) aceita também uma faixa de 1 nível só (equivalente a `set lev <n1>`, com `<n1> == <n2>`). |
| `set lat <valor>` / `set lat <min> <max>` | Latitude fixa num ponto, ou intervalo (domínio do mapa). |
| `set lon <valor>` / `set lon <min> <max>` | Longitude fixa num ponto, ou intervalo. |
| `set gxout <tipo>` | `shaded`/`contour`/`voronoi`/`hex` (2D, variáveis escalares — também vale `shaded` no `d3`); `vect` (padrão)/`stream`/`barb` (vento, `d u;v` ou `d mag(...)`). |
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
| `set time <n>` (ou `set t <n>`) | Seleciona o arquivo número `<n>` (entre os vários abertos) como o arquivo padrão para as próximas `d`/`d3`/estatísticas sem sufixo `.N` — ver seção 2.1. |
| `set time <ini> <fim>` (ou `set t <ini> <fim>`) | Com mais de um arquivo aberto: intervalo de arquivos (pelo número de abertura) para a série temporal entre arquivos — ver seção 2.1. |
| `set tint <segundos>` | Intervalo, em segundos, entre os quadros da animação da série temporal (`d`/`d3` no modo mapa/3D — seção 2.1). Padrão: 1 segundo. |
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
| `draw map` | Desenha o mapa de fundo e **liga** o modo "mapa persistente": a partir daqui, o mapa é **redesenhado automaticamente** em todo `d`/`d3` seguinte — inclusive quadro a quadro na animação da série temporal (seção 2.1) — até um `draw map off`. Se a janela **3D** (`d3`) for a ativa no momento, desenha projetado na "superfície" da caixa 3D em vez do comportamento 2D padrão. Pode ser chamado antes de qualquer `d`/`d3` (garante sozinho uma janela/eixo 2D válidos). |
| `draw map off` | Desliga o modo "mapa persistente": os próximos `d`/`d3` (e a animação) deixam de redesenhar o mapa automaticamente. |
| `draw label <texto>` | Define o rótulo da barra de cores. Se já existe uma barra de cores no gráfico atual, escreve o texto nela **na hora**. O texto também fica guardado na sessão e é **reaplicado automaticamente** toda vez que uma nova barra de cores for criada — inclusive quadro a quadro na animação (seção 2.1), onde a colorbar é recriada a cada quadro — e pode ser chamado mesmo antes de qualquer `d`/`d3` (o texto entra em vigor assim que a primeira barra de cores for criada). |

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
| Latitude e longitude fixas no mesmo ponto | **Perfil vertical**, no intervalo de níveis selecionado (`set lev <n1> <n2>` — seção 6) — ou só no nível único de `set lev <n>`, se nenhuma faixa tiver sido escolhida. |
| Apenas latitude fixa (ou só longitude) | **Corte vertical**, interpolando a malha sobre uma linha. Exige uma faixa de **pelo menos 2 níveis** (`set lev <n1> <n2>`, com `<n2>` maior que `<n1>`) — um nível único (de `set lev <n>`, ou uma faixa `set lev <n> <n>`) avisa e não plota, pois não há como desenhar um corte 2D com um só nível. |
| Nem latitude nem longitude fixas | **Mapa horizontal**, conforme `gxout` (`shaded`/`contour`/`voronoi`), sempre no **nível único** de `set lev <n>` (ou no primeiro nível de uma faixa, se uma estiver selecionada). |

No **eixo vertical** do corte/perfil (e no eixo Z do `d3`):
1. **Pressão** (hPa), se houver `t_iso_levels` — maior pressão embaixo.
2. **Altura real** (m), se houver `zgrid` — interpolada ao longo do corte (acompanha o terreno); menor embaixo.
3. **Índice do nível**, se nenhum dos dois existir; menor embaixo.

Áreas sem dado válido (corte/superfície abaixo da topografia) aparecem
**hachuradas** no corte vertical 2D.

### 8.1 Os quatro modos de `gxout` para mapa 2D

| `gxout` | Como funciona | Quando usar |
|---|---|---|
| `shaded` | Interpola para uma **grade regular** (reaproveitando a triangulação de Delaunay em cache) e usa `contourf` de grade regular. | Campo suave, contínuo. Rápido mesmo em malhas grandes graças ao cache (seção 9). |
| `contour` | Igual ao `shaded`, mas com `contour` (linhas + rótulos) em vez de preenchido. | Mesma ideia, isolinhas. |
| `voronoi` | **Rasteriza** o diagrama de Voronoi por aproximação: para cada pixel da imagem, usa o valor da célula mais próxima (via `cKDTree`), sem interpolar. Mostra o valor real de cada célula, sem suavização — mas visualmente sai como "pixels" quadrados, não a forma real da célula. | Quando quer ver os dados "crus", célula por célula, e a malha for grande o suficiente para o modo `hex` (abaixo) ficar pesado. |
| `hex` | Desenha o **polígono real** de cada célula — o hexágono/pentágono de verdade da malha MPAS/MONAN (pentágonos aparecem nos poucos defeitos topológicos inevitáveis de qualquer malha icosaédrica/Voronoi) — usando a conectividade completa do arquivo de grade (`verticesOnCell`/`nEdgesOnCell`/`latVertex`/`lonVertex`). Exemplo: `set gxout hex` seguido de `d t2m`. Em domínios de área limitada, as células da borda saem automaticamente com o tamanho/formato real (tipicamente diferente das internas) — a geometria vem direto dos vértices do próprio arquivo, sem nenhum tratamento especial de borda. Precisa da conectividade completa; sem ela, avisa e sugere `voronoi`. Mais fiel que `voronoi`, porém mais pesado (constrói e desenha um polígono por célula) — recomendado para domínios regionais ou malhas de porte pequeno/médio; em malhas globais muito grandes (milhões de células), prefira `shaded`/`contour`/`voronoi`. |

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
| `arquivo_sel` | Número do arquivo (entre os abertos) usado por padrão em `d`/`d3`/estatísticas sem sufixo `.N` — selecionado por `set t <n>` (um argumento), padrão `1` — ver seção 2.1. |
| `time_ini`, `time_fim` | Intervalo de arquivos (pelo número de abertura) selecionado por `set t <ini> <fim>`, para a série temporal entre arquivos — ver seção 2.1. `None` se ainda não definido. |
| `tint` | Intervalo, em segundos, entre os quadros da animação da série temporal (`set tint`) — padrão 1.0. |
| `draw_map_on` | `True` depois de `draw map` (até um `draw map off`): o mapa de fundo é redesenhado automaticamente em todo `d`/`d3` seguinte, inclusive quadro a quadro na animação — ver seção 2.1. |
| `cbar_label` | Texto definido por `draw label <texto>` (ou `None`/ausente se nunca usado): reaplicado automaticamente toda vez que uma nova barra de cores é criada, inclusive quadro a quadro na animação — ver seção 2.1/7. |
| `limits_poligono` | Array `(n_pontos, 2)` com os vértices (longitude, latitude) lidos por `load limits` (seção 2.2), ou ausente se nenhuma área foi carregada. |
| `limits_mask` | Array booleano `(nCells,)`: `True` nas células cujo centro cai dentro da área carregada por `load limits`. Base para as futuras funções estatísticas dentro da área. |
| `limits_indices` | Índices (inteiros) das células dentro da área — equivalente a `np.nonzero(limits_mask)[0]`, já pronto para uso direto. |
| `limits_arquivo` | Caminho do último arquivo de limites carregado com sucesso por `load limits`. |
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
| `_malha_dataset` | Referência ao `dataset` do arquivo de grade (embutido ou externo) usado para extrair `latCell`/`lonCell` do arquivo 1 — reaproveitado para ler `verticesOnCell`/`nEdgesOnCell`/`latVertex`/`lonVertex` sob demanda, quando `gxout hex` é usado (uso interno — seção 8.1). |
| `_poligonos_celulas` | Lista com o polígono (lon/lat) de cada célula, para `gxout hex`, em cache de memória — ou `None` se o arquivo de grade não tiver a conectividade completa (uso interno). |

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
- `_resolver_variavel(setup, token)` — resolve um token de variável com sufixo opcional `.N` (seção 2.1): localiza o arquivo aberto correspondente e a variável nele, com mensagens de erro/sugestões (`difflib`) quando o arquivo não está aberto ou a variável não existe. Sem sufixo `.N`, usa `setup['arquivo_sel']` (padrão `1`, alterado por `set t <n>`) em vez de sempre o arquivo 1.
- `_arquivo_por_indice(setup, indice)` — retorna o registro do arquivo aberto com aquele índice, ou `None`.
- `_avaliar_expressao(setup, expr)` — avaliador seguro de expressões aritméticas (`d (expr)`), agora resolvendo cada variável via `_resolver_variavel` — aceita sufixos `.N` e expressões cruzando arquivos, ex. `t2m.2 - t2m.1`.
- `_modo_serie_ativo(setup)` — `True` quando `set t <ini> <fim>` está definido e há mais de um arquivo aberto (seção 2.1).
- `_dados_serie_temporal(setup, nome_var)` — reúne o array de `nome_var` de cada arquivo do intervalo `time_ini`/`time_fim`, com mensagens de erro/sugestões se a variável faltar em algum.
- `_resolver_variavel_serie(setup, info, token)` — como `_resolver_variavel`, mas para uso dentro do modo de série: um token sem sufixo `.N` resolve para o arquivo do quadro atual (`info`), não sempre o arquivo 1; com sufixo, continua fixo naquele arquivo.
- `_avaliar_expressao_serie(setup, info, expr)` — como `_avaliar_expressao`, mas usando `_resolver_variavel_serie` (expressões no modo série, ex. `t2m-273.15`).
- `_dados_serie_temporal_expr(setup, expr)` — como `_dados_serie_temporal`, mas para uma expressão aritmética: avalia `expr` arquivo a arquivo (via `_avaliar_expressao_serie`) dentro do intervalo `time_ini`/`time_fim`.
- `_dados_estatistica(setup, expr)` — reúne a lista de arrays "por arquivo/tempo" usada pelas funções estatísticas (seção 2.3): todos os arquivos do intervalo de `set t` quando o modo de série estiver ativo (sufixo `.N` ignorado, com aviso, se `expr` não tiver operador — quem manda é o intervalo), ou só o arquivo indicado por `expr` (com sufixo `.N`) caso contrário. Aceita tanto um nome de variável simples quanto uma expressão aritmética (ex: `t2m-273.15`), avaliada via `_avaliar_expressao`/`_dados_serie_temporal_expr`, igual ao `d`/`d3` (seção 3).
- Despacho escalar de `sum`/`mean`/`min`/`max`/`p10`..`p90` `all`/`inlimits`/`point <variavel_ou_expressao>` (seção 2.3): reúne os dados via `_dados_estatistica` e chama `calcular_valor` (`estatistics.py`), com `modo_point=True` quando o complemento for `point`.
- Despacho espacial de `d sum`/`mean`/`min`/`max`/`p10`..`p90` `all`/`inlimits`/`point <variavel_ou_expressao>` (seção 2.3; dentro do dispatch de `d`/`display`): reúne os dados via `_dados_estatistica`, chama `calcular_campo` (`estatistics.py`) — que também retorna o **modo** (mapa/ponto/corte/mapa_niveis, conforme a seleção atual de lat/lon/nível e o complemento `point`) — e plota o resultado com `plot_estatistica_campo` (`plot_func.py`); no modo `mapa_niveis`, `calcular_campo` já recusou e retornou `None`, então nada é plotado.

### `files.py` (antigo `files_nc.py`)
- `file_open(fileName, setup_toml, gridFile=None, setup_anterior=None)` — abre o arquivo (e a grade, se necessária). Se `setup_anterior` for passado (já há um arquivo aberto na sessão), valida a malha do novo arquivo contra a assinatura já registrada (seção 2.1): rejeita com `(None, None)` se forem diferentes (preservando `setup_anterior` intacto), ou adiciona o novo arquivo a `setup["files"]` com o próximo índice sequencial, se forem iguais. Sem `setup_anterior` (primeiro `open`), monta o `setup` do zero, como antes — inclusive guardando a referência ao `dataset` da malha (`setup["_malha_dataset"]`), usada sob demanda por `gxout hex` (seção 8.1) para ler a conectividade completa. Resiliente à ausência de `nCells`, malha, `xtime`/`initial_time`, `t_iso_levels`.
- `carregar_limites(setup, caminho_csv)` — comando `load limits <arquivo.csv>` (seção 2.2): lê o arquivo de pontos (lat/lon, um por linha), calcula a máscara de células da malha dentro do polígono formado por eles e guarda tudo em `setup["limits_*"]`, pronto para as futuras funções estatísticas dentro da área. Retorna `True`/`False`; em caso de falha, preserva os limites já carregados anteriormente (se houver).

### `estatistics.py`
- `calcular_valor(setup, nome_funcao, arrays, mask, rotulo, modo_point=False)` — forma **escalar** de todas as estatísticas (`sum`/`mean`/`min`/`max`/`p10`..`p90`, seção 2.3): empilha `arrays` (ver `_empilhar`) e reduz a **um único número**, sobre todos os tempos selecionados e, conforme o modo espacial atual (mapa/ponto/corte/mapa_niveis — ver `_modo_espacial`/`_fatia`): todas as células (ou só as de `mask`) no nível único (modo mapa) ou na faixa de níveis (modo corte, ou mapa com `modo_point=True` e faixa genuína — modo `mapa_niveis`), ou toda a faixa de níveis na célula mais próxima (modo ponto — `mask` aí só confere se esse ponto está dentro da área). Imprime o resultado e o retorna (`float`), ou `None` em caso de erro/aviso (variável com formato inesperado, máscara não batendo com a malha atual, nenhuma célula disponível, ou ponto fora da área de limites).
- `calcular_campo(setup, nome_funcao, arrays, mask, rotulo, modo_point=False)` — forma **espacial**: como `calcular_valor`, mas reduz **só sobre os tempos**, mantendo a forma do modo atual — `(nCells,)` no mapa, `(nCells, nLevels)` no corte, `(nLevels,)` no ponto (perfil) — pronta para plotar via `plot_estatistica_campo` (`plot_func.py`). Com `mask`, as células de fora ficam com `NaN` (mapa/corte) ou o cálculo é recusado (ponto fora da área). Retorna `(campo, modo)`, ou `None` em caso de erro/aviso — inclusive no modo `mapa_niveis` (nem lat nem lon fixada, com `modo_point=True` e faixa genuína de níveis), onde a função sempre recusa a plotar (não há mapa nem corte bem definido) e retorna `None` com um aviso.
- `levf_efetivo(lev, levf)` (`utils.py`, compartilhada com `plot_func.py`) — devolve o limite superior efetivo da fatia de níveis: `levf` quando já define uma faixa genuína (`levf > lev`), senão `lev + 1` — evita que `var[..., lev:levf]` fique **vazio** quando `lev == levf` (nível único, sem `set lev <ini> <fim>` explícito), usado nos modos ponto/corte/mapa_niveis (`estatistics.py`) e nos mesmos modos da plotagem direta `d`/`d3` (`plot_func.py`).
- `_fatia(setup, var, rotulo)` — extrai, de UM array (um arquivo/tempo), a MESMA fatia que `d`/`d3` extrairiam para plotar agora (ver `plot_var`/`plot_perfil`/`plot_corte` em `plot_func.py`), conforme o modo espacial atual: `var[time_sel,:]` (2D), `var[time_sel,:,lev]` (3D, mapa), `var[time_sel,indice_mais_proximo,lev:levf]` (3D, ponto) ou `var[time_sel,:,lev:levf]` (3D, corte). Retorna `(dados, modo, indice_mais_proximo)`.
- `_empilhar(setup, arrays, rotulo, modo_point=False)` — fatia (`_fatia`) cada array de `arrays` (ver `_dados_estatistica` em `exec_func.py`) e empilha o resultado num eixo extra (o dos "tempos") na frente: `(n_tempos, nCells)` no mapa, `(n_tempos, nCells, nLevels)` no corte/mapa_niveis, ou `(n_tempos, nLevels)` no ponto. Retorna `(matriz, modo, indice_mais_proximo)`.
- `_modo_espacial(setup)` — decide, a partir de `setup["lat_min"]`/`["lat_max"]`/`["lon_min"]`/`["lon_max"]`, o modo atual: `"ponto"` (lat e lon fixadas no mesmo valor), `"corte"` (só uma das duas fixa) ou `"mapa"` (nenhuma fixa) — mesma decisão que `plot_var` usa para escolher entre `plot_perfil`/`plot_corte`/mapa (seção 8).
- `_indice_mais_proximo(setup)` — índice da célula da malha mais próxima do ponto de lat/lon selecionado (mesma fórmula usada por `plot_perfil`).
- `_preparar_mascara(mask, n_cells, ...)` — confere se `mask` bate com o número de células da matriz empilhada (ex: após um `reinit` com outra malha, sem recarregar `load limits`).
- `_descricao_nivel(setup)` / `_descricao_intervalo_niveis(setup)` — texto curto do nível único (modo mapa) ou da faixa de níveis (modo ponto/corte) atualmente selecionados, para anexar às mensagens de resultado — pressão em hPa quando disponível (`setup["eixo_pressao"]`), senão só o(s) índice(s).
- `sum_all`/`sum_inlimits`/`mean_all`/`mean_inlimits` — atalhos nomeados equivalentes a `calcular_valor` com o nome da função já fixado (úteis para chamar diretamente, ex. em testes).
- `NOMES_ESTATISTICA_ESCALAR`, `NOMES_ESTATISTICA_ESPACIAL` — tuplas com os nomes de comando reconhecidos por `exec_func.py` (todas as estatísticas têm tanto a forma escalar quanto a espacial, incluindo `sum`).

### `set_func.py`
- `cmd_set(...)` / `_cmd_set_dispatch(...)` — comando `set` (tabela da seção 6), com validação numérica segura. `set lev <n1> <n2>` valida `<n1>`/`<n2>` como índices de nível **inclusivos** (0 a `n_niveis-1`, com `<n1> <= <n2>`) e guarda internamente `setup["levf"] = <n2> + 1` — o limite EXCLUSIVO usado por toda fatia de nível do resto do código (`var[..., lev:levf]` — ver `levf_efetivo` em `utils.py`); sem esse `+1`, incluir o último nível pedido exigiria um índice inválido.
- `_print_level_info(setup, l)` — informação do nível ao usar `set lev <n>`.

### `show_func.py`
- `cmd_show(setup, cmd_split)` / `_mostrar_info_arquivo(setup)` — comando `show` (tabela da seção 5).
- `_mostrar_arquivos(setup)` — `show files`: tabela com os arquivos abertos na sessão (seção 2.1).
- `_mostrar_tempos(setup)` — `show times`: mesma tabela de `_mostrar_arquivos`, restrita ao(s) tempo(s) atualmente selecionado(s) por `set t` (o intervalo inteiro no modo série, ou só o arquivo pontual de `setup['arquivo_sel']` fora dele) — seção 2.1/5.
- `show_legend()` — `draw legend`.

### `draw_func.py`
- `draw_title(setup)` — `draw title <texto>`: desenha direto no eixo atual (`plt.title`).
- `draw_map(setup, ax=None)` — `draw map`: garante uma figura/eixo 2D de verdade (via `_ativar_figura_2d`, de `plot_func.py`) antes de desenhar — não depende do `ax` recebido do chamador, que pode ainda ser o inteiro inicial `0` (de `cli.py`) se nenhum `d`/`d3` tiver rodado ainda na sessão. Se a janela 3D estiver ativa, desenha via `plot_map_3d` na superfície da caixa.
- `draw_label(setup, cbar, lbl)` — `draw label <texto>`: se `cbar` já é uma barra de cores de verdade, aplica o texto na hora (e força o redesenho); senão (nenhum `d`/`d3` rodou ainda), não faz nada aqui — o texto já foi guardado em `setup["cbar_label"]` por quem chamou (`exec_func.py`) e é reaplicado sozinho pela primeira colorbar criada (`_aplicar_rotulo_cbar`, em `plot_func.py`).
- `draw_mark(cmd_split)` — `draw mark <lat> <lon> <simbolo>` (seção 7.1).
- `_SIMBOLOS_MARK` — tabela símbolo → `marker`/`fillstyle`.

### `plot_func.py`
**Plotagem 2D:**
- `plot_var(setup, var, cbar=None)` — despacha mapa/corte/perfil (seção 8) e `shaded`/`contour`/`voronoi`. No mapa horizontal, redesenha o mapa de fundo (`plot_map`) automaticamente se `setup["draw_map_on"]` estiver ligado (seção 7/2.1), e reaplica título (`_aplicar_titulo`) e rótulo da colorbar (`_aplicar_rotulo_cbar`), se definidos.
- `plot_perfil(setup, var)` / `plot_corte(setup, var, cbar=None)` — resolvem a fatia bruta (`var[...]`) da variável comum e delegam o desenho a `_plotar_perfil_dados`/`_plotar_corte_dados`.
- `_plotar_perfil_dados(setup, vertical_profile, closest_index)` / `_plotar_corte_dados(setup, data, cbar=None)` — desenham o perfil vertical/corte a partir de dados JÁ resolvidos (fatiados e, no caso do perfil, já na célula certa) — com hachura em áreas sem dado; reaproveitados tanto por `plot_perfil`/`plot_corte` (variável comum) quanto por `plot_estatistica_campo` (estatísticas num ponto/corte — seção 2.3); `_plotar_corte_dados` também reaplica o rótulo customizado da colorbar.
- `plot_voronoi(setup, data)` — rasterização por aproximação (nearest-neighbor) via `cKDTree` (seção 8.1, `gxout voronoi`).
- `plot_hexagonos(setup, data)` — desenha o polígono real de cada célula (`gxout hex`, seção 8.1) via `matplotlib.collections.PolyCollection`; avisa e retorna `None` (sem travar) se a malha não tiver a conectividade completa.
- `_obter_poligonos_celulas(setup)` — polígonos de cada célula para `gxout hex`, em cache de memória (`setup["_poligonos_celulas"]`); construído uma única vez por sessão via `construir_poligonos_celulas` (utils.py), a partir de `setup["_malha_dataset"]`.
- `plot_limites(setup)` — `load limits <arquivo.csv>` (seção 2.2): plota o contorno do polígono lido e destaca os centros de célula dentro dele (`setup["limits_mask"]`), com os demais em cinza claro para contexto.
- `plot_estatistica_campo(setup, campo, modo, cbar=None)` — `d mean|min|max|p10..p90 all|inlimits <variavel>` (seção 2.3): plota `campo`, já reduzido por `calcular_campo` (`estatistics.py`), no formato indicado por `modo` ("mapa"/"ponto"/"corte" — mesma decisão que `plot_var` tomaria para a própria variável, seção 8): mapa (`(nCells,)`, embrulhado como `(1, nCells)` e passado a `plot_var` com `time_sel` forçado a 0 só durante a chamada), perfil (`(nLevels,)`, via `_plotar_perfil_dados`) ou corte (`(nCells, nLevels)`, via `_plotar_corte_dados`).
- `_indice_mais_proximo_estatistica(setup)` — índice da célula mais próxima do ponto de lat/lon selecionado, usado por `plot_estatistica_campo` no modo "ponto" (mesma fórmula de `_indice_mais_proximo` em `estatistics.py`).
- `plot_wind`, `plot_vector_field`, `plot_barbs`, `plot_streams` — vento (`vect`/`barb`/`stream`); `plot_wind` também redesenha o mapa e reaplica o título automaticamente se definidos.
- `plot_marks(setup)` — mecanismo antigo de `set mark` (legado).
- `_aplicar_titulo(setup, ax)` — desenha/redesenha `setup["title"]` (definido por `draw title`) no eixo, com o estilo de `title_fs`/`title_fw`/`title_color`; chamada em todo plot cujo eixo pode ter sido limpo entre uma chamada e outra (ex.: quadro a quadro na animação de mapa), para o título não se perder.
- `_aplicar_rotulo_cbar(setup, cbar)` — reaplica `setup["cbar_label"]` (definido por `draw label`) numa colorbar recém-criada, com o tamanho/peso de `label_fontsize`/`label_fontweight`; chamada em toda criação de colorbar (2D e 3D), para o rótulo customizado não se perder quando a colorbar é recriada (ex.: a cada quadro da animação).

**Plotagem 3D:**
- `plot_var_3d(setup, var)` — `d3` (seção 4): *scatter* ou superfícies empilhadas (`shaded`). Redesenha o mapa (`plot_map_3d`) automaticamente se `setup["draw_map_on"]` estiver ligado, e reaplica o rótulo customizado da colorbar (`_aplicar_rotulo_cbar`), se definido.

**Série temporal entre arquivos (seção 2.1):**
- `plot_serie(setup, var_name, dados, cbar=None)` — despachante de `d <variavel>` no modo de série temporal: decide entre linha/Hovmöller (`plot_serie_temporal`) e animação de mapa (`plot_serie_mapa`).
- `plot_serie_temporal(setup, var_name, dados, cbar=None)` — linha (ponto único) ou diagrama Hovmöller (uma faixa entre lat/lon/nível); no Hovmöller, também reaplica o rótulo customizado da colorbar.
- `plot_serie_mapa(setup, var_name, dados, cbar=None)` — animação 2D (mapa completo), quadro a quadro, pausando `tint` segundos entre cada um.
- `plot_serie_mapa_3d(setup, var_name, dados)` — mesma animação, para `d3`.
- `_eixo_x_tempo(dados)` / `_formatar_eixo_x_tempo(...)` — monta o eixo X (tempo) a partir do `DataDado` de cada arquivo selecionado (datas reais, ou eixo posicional como recurso).

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
- `set_window_title(titulo)` / `set_ion()` — título da janela (bruto) / modo interativo.
- `atualizar_titulo_janela(setup)` — monta e aplica o título da janela no formato `GradsMonan: <timestamp>,<lat>,<lon>,L<nivel>` (lat/lon com 2 casas decimais; nível prefixado com `L` — seção 2.1), chamada por `files.py` logo após cada `open`, por `set_func.py` ao final de `set t`/`set lat`/`set lon`/`set lev`, e por `exec_func.py` no `reset`.
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
- `construir_poligonos_celulas(mesh)` — monta o polígono (lon/lat) de cada célula a partir da conectividade completa do arquivo de grade (`verticesOnCell`/`nEdgesOnCell`/`latVertex`/`lonVertex`), incluindo o formato/tamanho real das células de borda em domínios regionais — usado por `gxout hex` (seção 8.1). Retorna `None` se a malha não tiver essa conectividade.
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
- **`voronoi`/`shaded`/`contour`/corte/`streamlines`**: só precisam de `latCell`/`lonCell` — não é necessária a conectividade completa (`verticesOnCell` etc.).
- **`hex`** (seção 8.1): precisa da conectividade completa da malha — `verticesOnCell`, `nEdgesOnCell`, `latVertex`, `lonVertex` — presente no arquivo de grade padrão do MPAS/MONAN (`x1.<nCells>.grid.nc`), mas tipicamente ausente em saídas de diagnóstico/pós-processadas. Sem essa conectividade, o programa avisa e sugere `voronoi` em vez de travar.
