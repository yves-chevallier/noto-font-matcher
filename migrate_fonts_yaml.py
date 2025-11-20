#!/usr/bin/env python3
"""
Migrate fonts.yaml from the legacy format (one entry per file with string
unicode ranges) to the new format:

- group files that share the exact same coverage under a single entry
- store unicode ranges as inline pairs written in hex, e.g. `[0x00A7, 0x00AB]`
"""

from __future__ import annotations

import argparse
import pathlib
from typing import Dict, Iterable, List, Sequence, Tuple

import yaml


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


def _parse_codepoint(value) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        val = value.strip()
        if val.upper().startswith("U+"):
            val = val[2:]
        val = val.replace("..", "-")
        base = 16 if val.lower().startswith("0x") else 16
        return int(val, base)
    raise TypeError(f"Unsupported codepoint value: {value!r}")


def _parse_range(item) -> Tuple[int, int]:
    if isinstance(item, str):
        if ".." in item:
            start_str, end_str = item.split("..", 1)
        elif "-" in item:
            start_str, end_str = item.split("-", 1)
        else:
            start_str = end_str = item
        start, end = _parse_codepoint(start_str), _parse_codepoint(end_str)
    elif isinstance(item, (list, tuple)):
        if len(item) == 1:
            start = end = _parse_codepoint(item[0])
        elif len(item) == 2:
            start, end = _parse_codepoint(item[0]), _parse_codepoint(item[1])
        else:
            raise ValueError(f"Range list must have 1 or 2 elements, got {item!r}")
    else:
        raise TypeError(f"Unsupported range type: {type(item)}")
    return (start, end) if start <= end else (end, start)


def _normalize_entry(entry: Dict) -> Tuple[str, List[str], List[Tuple[int, int]]]:
    family = entry["family"]
    files: List[str] = []
    if entry.get("file"):
        files.append(entry["file"])
    files.extend(entry.get("files", []))
    ranges = sorted((_parse_range(r) for r in entry["unicode_ranges"]), key=lambda r: (r[0], r[1]))
    return family, files, ranges


def migrate(entries: Iterable[Dict]) -> List[Dict]:
    grouped: Dict[Tuple[str, Tuple[Tuple[int, int], ...]], Dict] = {}
    for raw in entries:
        family, files, ranges = _normalize_entry(raw)
        key = (family, tuple(ranges))
        bucket = grouped.setdefault(key, {"family": family, "files": [], "unicode_ranges": ranges})
        bucket["files"].extend(files)

    result: List[Dict] = []
    for (family, ranges), bucket in grouped.items():
        files = sorted(dict.fromkeys(bucket["files"]))
        result.append(
            {
                "family": family,
                "files": files,
                "unicode_ranges": [(HexInt(start), HexInt(end)) for start, end in ranges],
            }
        )

    result.sort(key=lambda e: (e["family"], e["unicode_ranges"]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert fonts.yaml to grouped, numeric range format.")
    parser.add_argument("input", nargs="?", default="fonts.yaml", help="Path to the legacy fonts.yaml.")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output path (defaults to overwriting the input file).",
    )
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    output_path = pathlib.Path(args.output) if args.output else input_path

    entries = yaml.safe_load(input_path.read_text(encoding="utf-8"))
    migrated = migrate(entries)

    with output_path.open("w", encoding="utf-8") as fh:
        yaml.dump(migrated, fh, Dumper=HexDumper, sort_keys=False, allow_unicode=False)

    print(f"Écrit {len(migrated)} entrées dans {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
