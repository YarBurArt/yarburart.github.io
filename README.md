# yarburart.github.io

## Install 
[Hugo install guide](https://gohugo.io/installation/).

The theme is a git submodule, so clone with submodules:

```bash
git clone --recurse-submodules https://github.com/YarBurArt/yarburart.github.io.git
```
run local server
```bash
hugo server --source ./site
```

Open http://localhost:1313/

If you cloned without submodules:

```bash
git submodule update --init --recursive
```

## Update writeups

Pages under `site/content/writeup/` are generated from `../ctf-worksheet`

```bash
git clone https://github.com/YarBurArt/ctf-worksheet.git ../ctf-worksheet
```

Edit the README there, then run:

```bash
make sync
```

If the repo is somewhere else:

```bash
python3 scripts/sync_writeups.py --source /path/to/ctf-worksheet
```

## Build

```bash
hugo --gc --minify --source ./site
```

The output goes to `site/public/`.

