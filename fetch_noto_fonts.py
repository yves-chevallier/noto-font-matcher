#!/usr/bin/env python3
"""
Fetch all Noto font files referenced on https://notofonts.github.io and
add CJK fonts from https://github.com/notofonts/noto-cjk, then build a
YAML database describing their Unicode coverage.

Usage:
    python fetch_noto_fonts.py

Outputs:
    - fonts/ directory containing downloaded TTFs (keeps family subfolders)
    - fonts.yaml describing files per family and their shared Unicode ranges
"""

import argparse
import itertools
import pathlib
import re
import sys
from typing import Dict, Iterable, List, Sequence, Tuple

import requests
import yaml
from fontTools.ttLib import TTFont




CJK_API = "https://api.github.com/repos/notofonts/noto-cjk/contents"
EMOJI_API = "https://api.github.com/repos/googlefonts/noto-emoji/contents/fonts"
JSDELIVR_BASE = "https://cdn.jsdelivr.net/gh/notofonts/notofonts.github.io/fonts"
INDEX_URL = "https://notofonts.github.io/"
ROOT = pathlib.Path(__file__).resolve().parent
FONTS_DIR = ROOT / "fonts"
DB_PATH = ROOT / "fonts.yaml"


class HexInt(int):
    """Marker int so PyYAML dumps codepoints in hex."""


class HexDumper(yaml.SafeDumper):
    """Safe dumper that renders tuples in flow style and HexInt as hex."""


def _represent_hexint(dumper: yaml.SafeDumper, data: HexInt):
    return dumper.represent_scalar("tag:yaml.org,2002:int", f"0x{int(data):04X}")


def _represent_tuple(dumper: yaml.SafeDumper, data: Sequence):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


HexDumper.add_representer(HexInt, _represent_hexint)
HexDumper.add_representer(tuple, _represent_tuple)


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = "noto-font-scraper/1.0"
    return session


def scrape_ttf_urls(session: requests.Session) -> List[str]:
    """Grab all jsDelivr TTF URLs from the main dashboard page."""
    resp = session.get(INDEX_URL)
    resp.raise_for_status()
    # Keep the pattern readable: escape dots once, and collect any path ending with .ttf
    pattern = r"https://cdn\.jsdelivr\.net/gh/notofonts/notofonts\.github\.io/[^\"'\s]+?\.ttf"
    urls = sorted(set(re.findall(pattern, resp.text)))
    return urls


def list_cjk_dir(session: requests.Session, path: str) -> List[Dict]:
    url = CJK_API if not path else f"{CJK_API}/{path}"
    resp = session.get(url)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def iter_cjk_fonts(session: requests.Session) -> Iterable[Tuple[str, str, str]]:
    """
    Yield (family, filename, url) for selected CJK fonts from noto-cjk repo.
    We take OTF static fonts under Sans/OTF/* and Serif/OTF/*.
    """
    for root in ("Sans/OTF", "Serif/OTF"):
        regions = [item for item in list_cjk_dir(session, root) if item.get("type") == "dir"]
        for region in regions:
            region_path = f"{root}/{region['name']}"
            files = list_cjk_dir(session, region_path)
            for entry in files:
                name = entry.get("name", "")
                if entry.get("type") == "file" and name.lower().endswith(".otf"):
                    family = name.split("-", 1)[0]  # e.g. NotoSansCJKjp
                    yield family, name, entry["download_url"]


def list_emoji_dir(session: requests.Session) -> List[Dict]:
    resp = session.get(EMOJI_API)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def iter_emoji_fonts(session: requests.Session) -> Iterable[Tuple[str, str, str]]:
    """
    Yield (family, filename, url) for emoji fonts in googlefonts/noto-emoji/fonts.
    """
    for entry in list_emoji_dir(session):
        name = entry.get("name", "")
        if entry.get("type") != "file" or not name.lower().endswith((".ttf", ".otf")):
            continue
        if name.startswith("Noto-COLRv1"):
            family = "NotoColorEmoji"
        elif name.startswith("NotoColorEmoji"):
            family = "NotoColorEmoji"
        elif name.startswith("NotoEmoji"):
            family = "NotoEmoji"
        else:
            family = name.split("-", 1)[0]
        yield family, name, entry["download_url"]


def iter_ttfs(urls: Iterable[str]) -> Iterable[Tuple[str, str, str]]:
    """
    Yield (family, filename, url) for each discovered TTF.
    Family is derived from the first path segment after /fonts/.
    """
    for url in urls:
        path_parts = pathlib.PurePosixPath(url.split("github.io", 1)[1]).parts
        try:
            fonts_idx = path_parts.index("fonts")
            family = path_parts[fonts_idx + 1]
        except (ValueError, IndexError):
            continue
        filename = path_parts[-1]
        yield family, filename, url


def download_file(session: requests.Session, url: str, dest: pathlib.Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    with session.get(url, stream=True) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)


def to_ranges(codepoints: Iterable[int]) -> List[Tuple[int, int]]:
    """Convert a sorted iterable of codepoints to compact ranges."""
    ranges: List[Tuple[int, int]] = []
    for key, group in itertools.groupby(enumerate(codepoints), lambda ic: ic[0] - ic[1]):
        group_list = [cp for _, cp in group]
        start, end = group_list[0], group_list[-1]
        ranges.append((start, end))
    return ranges


def unicode_ranges(ttf_path: pathlib.Path) -> List[Tuple[int, int]]:
    font = TTFont(ttf_path, recalcBBoxes=False, lazy=True)
    cmap = font["cmap"]
    codepoints = sorted({cp for table in cmap.tables for cp in table.cmap.keys()})
    font.close()
    return to_ranges(codepoints)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limiter le nombre de TTF téléchargés (utile pour tester).",
    )
    parser.add_argument(
        "--skip-main",
        action="store_true",
        help="Ne pas télécharger les fontes listées sur notofonts.github.io.",
    )
    parser.add_argument(
        "--skip-cjk",
        action="store_true",
        help="Ne pas télécharger les fontes CJK depuis notofonts/noto-cjk.",
    )
    parser.add_argument(
        "--skip-emoji",
        action="store_true",
        help="Ne pas télécharger les fontes emoji depuis googlefonts/noto-emoji.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session = build_session()
    if not args.skip_main:
        print("Scraping TTF links from notofonts.github.io…")
        urls = scrape_ttf_urls(session)
        if not urls:
            print("Aucun TTF trouvé sur la page. Abandon.")
            return 1

        if args.limit:
            urls = urls[: args.limit]
            print(f"Découvert {len(urls)} fichiers TTF (limités à {args.limit}). Téléchargement…")
        else:
            print(f"Découvert {len(urls)} fichiers TTF. Téléchargement…")

        for family, filename, url in iter_ttfs(urls):
            dest = FONTS_DIR / family / filename
            download_file(session, url, dest)

    if not args.skip_cjk:
        print("Fetching CJK fonts from noto-cjk (OTF)…")
        for family, filename, url in iter_cjk_fonts(session):
            dest = FONTS_DIR / family / filename
            download_file(session, url, dest)

    if not args.skip_emoji:
        print("Fetching emoji fonts from googlefonts/noto-emoji…")
        for family, filename, url in iter_emoji_fonts(session):
            dest = FONTS_DIR / family / filename
            download_file(session, url, dest)

    print("Building coverage database…")
    grouped: Dict[Tuple[str, Tuple[Tuple[int, int], ...]], Dict] = {}
    for font_path in sorted(FONTS_DIR.rglob("*.*")):
        if font_path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
            continue
        family = font_path.parent.name  # fonts/<family>/file
        ranges = unicode_ranges(font_path)
        key = (family, tuple(ranges))
        entry = grouped.setdefault(
            key,
            {
                "family": family,
                "files": [],
                "unicode_ranges": ranges,
            },
        )
        entry["files"].append(str(font_path.relative_to(ROOT)))

    entries: List[Dict] = []
    for (family, ranges), entry in grouped.items():
        entries.append(
            {
                "family": family,
                "files": sorted(dict.fromkeys(entry["files"])),
                "unicode_ranges": [(HexInt(start), HexInt(end)) for start, end in ranges],
            }
        )

    entries.sort(key=lambda e: (e["family"], e["unicode_ranges"]))
    with DB_PATH.open("w", encoding="utf-8") as fh:
        yaml.dump(entries, fh, Dumper=HexDumper, sort_keys=False, allow_unicode=False, width=120)

    print(f"Done. Fonts saved under {FONTS_DIR} and metadata in {DB_PATH}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
