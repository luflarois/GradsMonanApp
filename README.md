# GRADS-MONAN APP

Um clone do GrADS/COLA para abrir e plotar saídas do modelo MONAN/MPAS
(grade de Voronoi não estruturada).

## Instalação

Duas formas prontas — escolha uma. As dependências (numpy, scipy,
matplotlib, netCDF4, geopandas, toml) são resolvidas automaticamente; não é
preciso instalar nada manualmente.

### Opção 1 — conda/mamba (recomendada)

`geopandas` depende de bibliotecas de sistema (GDAL, GEOS, PROJ). O conda
resolve isso sozinho; via `pip` puro, em algumas máquinas (principalmente
Windows) pode falhar ou exigir passos extras.

```bash
conda env create -f environment.yml
conda activate grads-monan
```

(ou `mamba env create -f environment.yml`, se tiver o mamba — é bem mais rápido)

### Opção 2 — pip

Se seu ambiente já tem GDAL/GEOS/PROJ instalados (comum em máquinas
científicas Linux), funciona direto:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install .
```

## Uso

Depois de instalado (qualquer uma das duas opções), o comando fica
disponível no terminal:

```bash
grads-monan
```

Na primeira execução, a pasta de configuração (`~/.config/grads_monan/`) e
o arquivo `grads_monan.toml` são criados automaticamente — não é mais
necessário rodar nenhum script de instalação à parte.

Para recriar a configuração do zero (ex.: depois de uma atualização):

```bash
grads-monan-setup
```

### Shapefiles do mapa de fundo (`draw map`)

Os shapefiles `Continents.*`, usados pelo comando `draw map`, precisam estar
em `src/grads_monan/data/` **antes de instalar o pacote** (são copiados
automaticamente para `~/.config/grads_monan/` na primeira execução). Se você
ainda não os colocou lá, copie-os manualmente para `~/.config/grads_monan/`
a qualquer momento — o `draw map` vai avisar se não encontrar.

## Gerando um instalador único (sem precisar de Python)

Para distribuir a um usuário que não tem (e não quer instalar) Python, dá
para empacotar tudo — interpretador Python e dependências inclusos — num
único executável, com o [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller --onefile --name grads-monan --collect-all geopandas --collect-all netCDF4 src/grads_monan/cli.py
```

Isso gera um `dist/grads-monan` (ou `.exe` no Windows) que roda sozinho,
sem precisar de `pip install` nem de Python instalado na máquina de quem for
usar. É o caminho mais indicado para distribuir a colegas que só querem
"baixar e rodar". Prós/contras:

- **Prós**: instalação = copiar um arquivo; nenhuma dependência manual.
- **Contras**: o executável fica grande (o `geopandas`/GDAL pesam bastante,
  facilmente 300–600 MB); precisa gerar um executável separado para cada
  sistema operacional (Linux, Windows, macOS) — não dá para gerar o `.exe`
  do Windows rodando em Linux.

  