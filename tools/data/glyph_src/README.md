# 1.6.0 glyph sources

Pictures for glyphs whose items have no icon in this repository. `tools/glyphs.py` reads them (16×16)
and copies them into the resource pack's `font/glyph_*.png`.

| Folder | From |
| --- | --- |
| `kaleidoscope_harvest/` | Kaleidoscope Harvest's own item icons (`packs/RP/textures/kaleidoscope_harvest/items/`, 2026-11-17), unchanged: the nine Harvest ingredients of the Harvest dishes |

Vanilla and Kaleidoscope Cookery ingredients have no picture here yet: `tools/glyphs.py` draws a simple
placeholder for each (`python tools/glyphs.py list`).
