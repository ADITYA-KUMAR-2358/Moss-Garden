"""Rasterize public/favicon.svg into the PNG and ICO files browsers ask for.

Run from the repo root: python frontend/scripts/build_favicons.py
Needs PyMuPDF.
"""

import struct
from pathlib import Path

import pymupdf as fitz

PUBLIC = Path(__file__).resolve().parents[1] / "public"
SVG = (PUBLIC / "favicon.svg").read_bytes()


def png(size: int) -> bytes:
    page = fitz.open("svg", SVG)[0]
    zoom = size / page.rect.width
    return page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True).tobytes("png")


def ico(sizes: list[int]) -> bytes:
    images = [png(size) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries = b""
    for size, data in zip(sizes, images):
        edge = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", edge, edge, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return header + entries + b"".join(images)


(PUBLIC / "favicon-32.png").write_bytes(png(32))
(PUBLIC / "apple-touch-icon.png").write_bytes(png(180))
(PUBLIC / "favicon.ico").write_bytes(ico([16, 32, 48]))
print("wrote favicon-32.png, apple-touch-icon.png, favicon.ico")
