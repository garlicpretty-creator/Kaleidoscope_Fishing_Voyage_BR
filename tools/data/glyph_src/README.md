# 1.6.0 glyph sources

Pictures for glyphs. `tools/glyphs.py` reads them (16×16) and puts each into its existing cell of the
resource pack's `font/glyph_*.png` (cells never move; a picture here replaces a drawn placeholder in place).

Names: an item id `ns:item` is `<ns>/<item>.png`; any other glyph is `<glyph name>.png` (`water.river.png`,
`moon.3.png`). `python tools/glyphs.py list` prints the glyphs that are still drawn placeholders (none, 2026-11-18).

| Pictures | From |
| --- | --- |
| `kaleidoscope_harvest/` | Kaleidoscope Harvest's own item icons (`packs/RP/textures/kaleidoscope_harvest/items/`, 2026-11-17), unchanged: the nine Harvest ingredients of the Harvest dishes |
| `kaleidoscope_cookery/` | Kaleidoscope Cookery 1.6.6's own item icons (`textures/items/kc_<item>.png` in its `.mcaddon`), unchanged: the ten Cookery ingredients |
| `minecraft/`, `fish.unknown`, `item.unknown`, water, time, weather, stations, `bowl.empty`, `ui.gear` / `recipes` / `merchant` | Retro Diffusion, drawn for this pack (`tools/art/rd_glyphs.py`, prompts in `tools/art/glyph_prompts.json`, choices in `tools/art/glyph_picks.json`); not copies of vanilla textures |
| `bowl.half` / `bowl.full`, moons, tides, meteor, aurora, dots, marks, arrows, tiers, `mark.sep`, `ui.animation` | Drawn in code by `tools/art/derive_glyphs.py` (too small or too exact for Retro Diffusion, or one family) |
