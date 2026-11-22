.PHONY: sync

sync:
	python3 scripts/sync_writeups.py --source ../ctf-worksheet --output site/content/writeup
