.PHONY: sync serve build

sync:
	python3 scripts/sync_writeups.py --source ../ctf-worksheet --output site/content/writeup

serve:
	hugo server --source ./site

build:
	hugo --gc --minify --source ./site
