"""Workstation particle sheet (textures/particle/kfv_station.png): four white 8x8 sprites the kfv_station_* particles tint.
  python tools/gen_station_particle_tex.py
"""
# kfv_station.png: 32x8, four white 8x8 sprites tinted by each particle:
#  u0 soft dot   u8 sparkle star   u16 flake   u24 droplet
from PIL import Image
import sys
im = Image.new('RGBA', (32, 8), (0, 0, 0, 0))
px = im.load()
def put(x, y, a): px[x, y] = (255, 255, 255, a)
# soft dot (4x4 rounded, soft rim)
for (x, y) in [(3,2),(4,2),(2,3),(3,3),(4,3),(5,3),(2,4),(3,4),(4,4),(5,4),(3,5),(4,5)]: put(x, y, 255)
for (x, y) in [(2,2),(5,2),(2,5),(5,5)]: put(x, y, 110)
# sparkle: 4-point star
cx, cy = 8 + 3, 3
for d, a in [(0,255),(1,230),(2,150),(3,70)]:
    for (dx, dy) in [(d,0),(-d,0),(0,d),(0,-d)]: put(cx+dx, cy+dy, a)
for (dx, dy) in [(1,1),(-1,1),(1,-1),(-1,-1)]: put(cx+dx, cy+dy, 90)
# flake: irregular sliver
for (x, y) in [(18,2),(19,2),(20,2),(17,3),(18,3),(19,3),(20,3),(21,3),(18,4),(19,4),(20,4),(19,5)]: put(x, y, 255)
for (x, y) in [(21,2),(17,4),(21,4)]: put(x, y, 140)
# droplet: teardrop, point up
for (x, y) in [(27,1)]: put(x, y, 150)
for (x, y) in [(27,2),(26,3),(27,3),(28,3),(26,4),(27,4),(28,4),(26,5),(27,5),(28,5),(27,6)]: put(x, y, 255)
for (x, y) in [(25,4),(29,4),(25,5),(29,5),(26,6),(28,6)]: put(x, y, 120)
im.save(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))), "Kaleidoscope Fishing Voyage [RP]", "textures", "particle", "kfv_station.png"))
