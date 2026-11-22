#!/usr/bin/env python3
"""Turn the ctf-worksheet READMEs into Hugo pages.

ctf-worksheet is the source: one README.md per page, no front matter.
This script adds the front matter Hugo needs, creates page bundles and
section pages, rewrites links between writeups, and copies assets.

Usage:
    python3 scripts/sync_writeups.py [--source ../ctf-worksheet]
                                     [--output site/content/writeup]
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT.parent / "ctf-worksheet"
DEFAULT_OUTPUT = REPO_ROOT / "site" / "content" / "writeup"

KNOWN_CATEGORIES = {
    "crypto", "web", "pwn", "rev", "reverse", "forensics", "forensic",
    "misc", "stego", "osint", "ppc", "coding", "ml", "android", "pentest",
    "attack-defense", "admin", "web3", "blockchain",
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LINK_RE = re.compile(r"(\[[^\]]*\]\()([^)]+)(\))")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def title_case(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").title()


def split_title(text: str, fallback: str) -> tuple[str, str]:
    """First heading outside a fenced code block is the page title."""
    lines = text.splitlines()
    fenced = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue

        title = MD_LINK_RE.sub(r"\1", match.group(2)).strip()
        for separator in (" — ", " – "):
            if separator in title:
                title = title.rsplit(separator, 1)[1].strip()
                break
        if title and title == title.lower():
            title = title[0].upper() + title[1:]
        body = "\n".join(lines[:index] + lines[index + 1 :]).lstrip("\n")
        return title, body

    return title_case(fallback), text.strip()


def toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def content_dirs(root: Path) -> set[Path]:
    """Directories that contain a README or a descendant with a README."""
    found: set[Path] = set()
    for readme in root.rglob("README.md"):
        if ".git" in readme.parts:
            continue
        for parent in readme.parents:
            if parent == root:
                break
            found.add(parent)
    return found


def child_content_dirs(directory: Path, dirs: set[Path]) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.is_dir() and p in dirs)


def display_title(directory: Path) -> str:
    readme = directory / "README.md"
    if readme.exists():
        title, _ = split_title(readme.read_text(encoding="utf-8"), directory.name)
        return title
    return title_case(directory.name)


def page_meta(directory: Path, source_root: Path, source_title: str) -> dict[str, str]:
    """Read source, event and category from the folder path."""
    parts = directory.relative_to(source_root).parts
    below = parts[1:]  # parts[0] is the source folder (ctf-ru, htb, ...)

    event = below[0] if below else ""
    category = ""
    if len(below) >= 3:
        category = below[1]
    elif len(below) == 2 and below[1].lower() in KNOWN_CATEGORIES:
        category = below[1]

    event_title = display_title(source_root / parts[0] / event) if event else source_title
    category_title = title_case(category) if category else ""

    tags = []
    for tag in (category_title, event_title, source_title):
        if tag and tag.lower() not in {t.lower() for t in tags}:
            tags.append(tag)

    return {
        "source": source_title,
        "event": event_title,
        "category": category_title,
        "categories": f"[{toml_string(category_title)}]" if category_title else "[]",
        "tags": "[" + ", ".join(toml_string(tag) for tag in tags) + "]",
    }


def build_url_map(root: Path, dirs: set[Path]) -> dict[Path, str]:
    return {d: "/writeup/" + d.relative_to(root).as_posix() + "/" for d in dirs}


def rewrite_links(body: str, directory: Path, root: Path, urls: dict[Path, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        target = match.group(2).strip()
        if (
            not target
            or target.startswith(("http://", "https://", "#", "mailto:", "data:", "/"))
            or target.startswith("<")
        ):
            return match.group(0)

        path_part, sep, anchor = target.partition("#")
        path_part = path_part.split("?", 1)[0]
        if not path_part:
            return match.group(0)

        candidate = (directory / path_part).resolve()
        if candidate.name == "README.md":
            candidate = candidate.parent

        url = urls.get(candidate)
        if url is None and path_part.endswith("/README.md"):
            url = urls.get((directory / path_part).resolve().parent)
        if url is None:
            return match.group(0)
        return match.group(1) + url + (sep + anchor if sep else "") + match.group(3)

    return LINK_RE.sub(replace, body)


def write_page(
    out: Path, title: str, meta: dict[str, str], body: str, *, section: bool = False
) -> None:
    lines = [
        "+++",
        f"title = {toml_string(title)}",
        f"source = {toml_string(meta['source'])}",
        f"event = {toml_string(meta['event'])}",
    ]
    if meta["category"]:
        lines.append(f"category = {toml_string(meta['category'])}")
    lines.append(f"categories = {meta['categories']}")
    if not section:
        lines.append(f"tags = {meta['tags']}")
    lines.append("showDate = false")
    if section:
        lines.append("excludeFromSearch = true")
    lines += ["+++", "", body.strip(), ""]
    out.write_text("\n".join(lines), encoding="utf-8")


def copy_assets(src: Path, dst: Path, dirs: set[Path]) -> None:
    for item in src.iterdir():
        if item.name in {"README.md", ".git", ".github"}:
            continue
        if item.is_dir() and item in dirs:
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def generate(source: Path, output: Path) -> int:
    dirs = content_dirs(source)
    urls = build_url_map(source, dirs)

    output.mkdir(parents=True, exist_ok=True)
    for item in output.iterdir():
        if item.name == "_index.md":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    sources = sorted(
        p for p in source.iterdir()
        if p.is_dir() and p in dirs and p.name not in {".git", ".github"}
    )
    count = 0

    def walk(directory: Path) -> None:
        nonlocal count
        rel = directory.relative_to(source)
        out = output / rel
        out.mkdir(parents=True, exist_ok=True)

        readme = directory / "README.md"
        if readme.exists():
            title, body = split_title(readme.read_text(encoding="utf-8"), directory.name)
        else:
            title, body = title_case(directory.name), ""

        body = rewrite_links(body, directory, source, urls)
        source_root = source / rel.parts[0]
        source_title = display_title(source_root)
        meta = page_meta(directory, source, source_title)

        children = child_content_dirs(directory, dirs)
        write_page(
            out / ("_index.md" if children else "index.md"),
            title,
            meta,
            body,
            section=bool(children),
        )
        if not children:
            count += 1

        copy_assets(directory, out, dirs)
        for child in children:
            walk(child)

    for source_dir in sources:
        walk(source_dir)

    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not (args.source / "README.md").exists():
        raise SystemExit(f"not a ctf-worksheet checkout: {args.source}")

    count = generate(args.source.resolve(), args.output.resolve())
    print(f"generated {count} writeups in {args.output}")


if __name__ == "__main__":
    main()
