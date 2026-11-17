# 1.5.0 icon sources

Untouched 16×16 pictures the 1.5.0 item icons start from. `tools/icons_1_5.py` reads them and writes the
finished icons (outline, margin, recolours), so these stay as they came.

| File | From |
| --- | --- |
| `emperor_tuna_fin.png` | Retro Diffusion, 1.4 work (branch history `f6824fd`) |
| `lobster_tomalley.png`, `salted_shrimp.png`, `dried_shell_shrimp.png`, `xo_sauce.png`, `crab_leg.png`, `boiled_shrimp.png`, `steamed_crab_leg.png`, `grilled_crab_leg.png`, `dried_shrimp_greens.png` | Retro Diffusion (`rd_fast__mc_item`, 16×16, background removed), 2026-11-17; one picked out of three each |

| everything else (squid, tuna cuts, gutted fish, purged clam, fertilized roe, star sand, nine dishes, eight new fish) | Retro Diffusion, 2026-11-17; one picked out of four each |

Not here, or not final:
- 2026-11-17, second round: Shrimp Head (from a hand drawing, image to image), Peeled Shrimp, Shrimp Shells, Crab Shell,
  Crab Roe, Jellyfish Strips, Dried Shell-on Shrimp, Whole Squid and Squid Tentacles were generated again (six or
  twelve each) and replaced. The hand drawing of the Shrimp Head is still `shrimp_head()` in tools/icons_1_5.py.
- `chutoro.png`, `otoro.png`, `bonito_sashimi.png` all came out as the same red block: the finished icons recolour
  them (medium pink with fat lines, pale pink marbled, dark red with a silver skin edge) so the three tell apart.
