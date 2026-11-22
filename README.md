# yarburart.github.io

Hugo site for yarburart.github.io. Writeups live in a separate repo, `ctf-worksheet`, and a script copies them into the site.

## Run it locally

Install Hugo extended 0.169.0. On Fedora:

```bash
mkdir -p ~/.local/bin
curl -fsSL https://github.com/gohugoio/hugo/releases/download/v0.169.0/hugo_extended_0.169.0_linux-amd64.tar.gz | tar -xz -C ~/.local/bin hugo
```

For other systems, see the [Hugo install guide](https://gohugo.io/installation/).

The theme is a git submodule, so clone with submodules:

```bash
git clone --recurse-submodules https://github.com/YarBurArt/yarburart.github.io.git
cd yarburart.github.io
hugo server --source ./site
```

Open http://localhost:1313/.

If you cloned without submodules:

```bash
git submodule update --init --recursive
```

## Update writeups

Pages under `site/content/writeup/` are generated from `../ctf-worksheet`. Clone it next to the site if you do not have it:

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

