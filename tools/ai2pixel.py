"""Turn an AI-generated "pixel art" picture into a real pixel-art PNG.

AI images (usually 1024x1024) only *look* like a 16x16 grid: the cells are not exactly 64 px, the grid
may be offset, edges are soft and the colours are noisy. A plain nearest-neighbour shrink then lands on
cell borders and picks up noise. This tool instead:

  1. finds the real cell size and grid offset from where the colour changes line up;
  2. reads each cell from its centre (median colour), never from its border;
  3. makes the background transparent by flooding from the image edges (white or the given colour),
     so white highlights inside the object stay white;
  4. merges near-identical colours (JPEG noise) into a clean palette;
  5. splits a sheet into separate objects and writes each one, both at its native grid size and
     fitted into a 16x16 canvas.

  python tools/ai2pixel.py <image> <out_dir> [--cell N] [--bg ffffff] [--size 16] [--colors 32]
"""
import argparse, os
from collections import Counter, deque
from PIL import Image


def content_box(px, w, h, bg, tol):
    xs, ys = [], []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if not near(px[x, y], bg, tol):
                xs.append(x); ys.append(y)
    if not xs:
        return 0, 0, w, h
    return max(0, min(xs) - 4), max(0, min(ys) - 4), min(w, max(xs) + 5), min(h, max(ys) + 5)


def edge_profile(px, box, axis):
    """Sum of colour changes across every column (axis 0) or row (axis 1), inside the content box only."""
    x0, y0, x1, y1 = box
    a0, a1, b0, b1 = (x0, x1, y0, y1) if axis == 0 else (y0, y1, x0, x1)
    prof = [0.0] * (a1 - a0)
    for i in range(a0 + 1, a1):
        s = 0
        for j in range(b0, b1, 2):
            a = px[i, j] if axis == 0 else px[j, i]
            b = px[i - 1, j] if axis == 0 else px[j, i - 1]
            s += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
        prof[i - a0] = s
    return prof


def find_cell(prof, lo=4, hi=128):
    """Cell size from the autocorrelation of the edge profile: the first lag that repeats strongly
    (multiples of the cell repeat too, so the smallest good lag wins)."""
    n = len(prof)
    m = sum(prof) / n
    d = [p - m for p in prof]
    var = sum(v * v for v in d) or 1
    ac = {}
    for lag in range(lo, min(hi, n // 3) + 1):
        ac[lag] = sum(d[i] * d[i + lag] for i in range(n - lag)) / var
    # local maxima
    peaks = [l for l in ac if ac[l] >= ac.get(l - 1, -9) and ac[l] >= ac.get(l + 1, -9) and ac[l] > 0]
    if not peaks:
        return float(lo)
    top = max(ac[l] for l in peaks)
    return float(min(l for l in peaks if ac[l] >= 0.6 * top))


def fit_grid(prof, guess, start):
    """Refine cell size and offset around the guess so that cell borders sit on colour changes and cell
    middles are quiet. Returns (cell, offset in image coordinates)."""
    n = len(prof)
    mean = sum(prof) / n or 1
    best = (-1e9, guess, 0.0)
    c = guess - 1.5
    while c <= guess + 1.5:
        o = 0.0
        while o < c:
            xs = [int(round(o + k * c)) for k in range(int((n - o) / c) + 1)]
            mids = [int(round(o + (k + 0.5) * c)) for k in range(int((n - o) / c) + 1)]
            xs = [x for x in xs if 0 < x < n - 1]; mids = [x for x in mids if 0 < x < n - 1]
            if len(xs) >= 3 and mids:
                on = sum(max(prof[x - 1], prof[x], prof[x + 1]) for x in xs) / len(xs)
                off = sum(prof[x] for x in mids) / len(mids)
                score = (on - off) / mean
                if score > best[0]:
                    best = (score, c, o)
            o += 0.5
        c += 0.05
    return best[1], start + best[2]


def sample(px, x0, y0, x1, y1):
    """Median colour of the middle half of a cell."""
    mx, my = (x1 - x0) / 4, (y1 - y0) / 4
    cols = [px[x, y] for y in range(int(y0 + my), max(int(y0 + my) + 1, int(y1 - my)))
            for x in range(int(x0 + mx), max(int(x0 + mx) + 1, int(x1 - mx)))]
    return tuple(sorted(c[i] for c in cols)[len(cols) // 2] for i in range(3))


def near(a, b, tol):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) <= tol


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def shrink(obj, size):
    """Shrink a pixel-art object to fit size x size without nearest-neighbour's dropped lines:
    each target pixel takes the most common colour of the source cells it covers, and target pixels on
    the outline take the darkest colour there, so outlines stay unbroken."""
    k = size / max(obj.size)
    tw, th = max(1, round(obj.width * k)), max(1, round(obj.height * k))
    sx, sy = obj.width / tw, obj.height / th
    src = obj.load()
    out = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    blocks = {}
    for ty in range(th):
        for tx in range(tw):
            x0, x1 = int(tx * sx), max(int(tx * sx) + 1, int(round((tx + 1) * sx)))
            y0, y1 = int(ty * sy), max(int(ty * sy) + 1, int(round((ty + 1) * sy)))
            cells = [src[x, y] for y in range(y0, min(y1, obj.height)) for x in range(x0, min(x1, obj.width))]
            solid = [c for c in cells if c[3]]
            if len(solid) * 2 < len(cells):
                continue
            blocks[(tx, ty)] = solid
            out.putpixel((tx, ty), Counter(solid).most_common(1)[0][0])
    for (tx, ty), solid in blocks.items():
        edge = any((tx + dx, ty + dy) not in blocks for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            darkest = min(solid, key=lum)
            if lum(darkest) < lum(out.getpixel((tx, ty))) * 0.8:
                out.putpixel((tx, ty), darkest)
        else:
            # inside the shape, busy detail (legs, feelers) makes the outline colour win the vote and the
            # body turns to mush; use the most common lighter colour when it covers a fair share of the block
            top = max(lum(c) for c in solid)
            light = [c for c in solid if lum(c) >= 0.45 * top and lum(c) > 40]
            if light and lum(out.getpixel((tx, ty))) < 0.45 * top and len(light) * 3 >= len(solid):
                out.putpixel((tx, ty), Counter(light).most_common(1)[0][0])
    for (tx, ty) in blocks:                    # drop single stray pixels (broken feelers, specks)
        if not any((tx + dx, ty + dy) in blocks for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy):
            out.putpixel((tx, ty), (0, 0, 0, 0))
    return out


def to_diagonal(obj):
    """Turn a long object so its long axis runs from bottom-left to top-right (like vanilla fish).
    Rotation is done on the native grid with the RotSprite trick (Scale2x x3, nearest rotate, block vote)."""
    import math
    pts = [(x, y) for y in range(obj.height) for x in range(obj.width) if obj.getpixel((x, y))[3]]
    mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts); syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    axis = 0.5 * math.atan2(2 * sxy, sxx - syy)          # image coords: y down
    current = -math.degrees(axis)                       # counter-clockwise angle of the long axis
    if abs(current) < 10:
        return obj                                       # lying flat (a heap, a bowl, a plate): keep it upright
    turn = 45 - current
    if abs(turn) < 6:
        return obj
    big = obj
    for _ in range(3):
        big = _scale2x(big)
    big = big.rotate(turn, resample=Image.NEAREST, expand=True)
    kk = 8
    W, H = big.size
    small = Image.new('RGBA', (W // kk, H // kk), (0, 0, 0, 0))
    bp = big.load()
    for by in range(H // kk):
        for bx in range(W // kk):
            cols = [bp[bx * kk + i, by * kk + j] for j in range(kk) for i in range(kk)]
            solid = [c for c in cols if c[3]]
            if len(solid) * 2 < len(cols):
                continue
            centre = [bp[bx * kk + i, by * kk + j] for j in range(2, 6) for i in range(2, 6)]
            centre = [c for c in centre if c[3]] or solid
            small.putpixel((bx, by), Counter(centre).most_common(1)[0][0])
    return small.crop(small.getbbox())


def _scale2x(im):
    w, h = im.size
    s = im.load()
    out = Image.new('RGBA', (w * 2, h * 2))
    d = out.load()
    P = lambda x, y: s[min(max(x, 0), w - 1), min(max(y, 0), h - 1)]
    for y in range(h):
        for x in range(w):
            E, B, D, F, H_ = P(x, y), P(x, y - 1), P(x - 1, y), P(x + 1, y), P(x, y + 1)
            if B != H_ and D != F:
                d[2 * x, 2 * y] = D if D == B else E
                d[2 * x + 1, 2 * y] = F if B == F else E
                d[2 * x, 2 * y + 1] = D if D == H_ else E
                d[2 * x + 1, 2 * y + 1] = F if H_ == F else E
            else:
                d[2 * x, 2 * y] = d[2 * x + 1, 2 * y] = d[2 * x, 2 * y + 1] = d[2 * x + 1, 2 * y + 1] = E
    return out


def convert(path, out_dir, cell=None, bg=(255, 255, 255), size=16, colors=32, tol=36, diagonal=True):
    src = Image.open(path)
    alpha = None
    if src.mode in ('RGBA', 'LA', 'P'):     # transparent input: flatten onto the background colour
        src = src.convert('RGBA')
        a = src.getchannel('A')
        if a.getextrema()[0] < 128:          # real transparency: it, not the colour, marks the background
            alpha = a.load()
        flat = Image.new('RGBA', src.size, tuple(bg) + (255,))
        flat.alpha_composite(src)
        src = flat
    im = src.convert('RGB')
    w, h = im.size
    px = im.load()
    if cell:
        cx = cy = float(cell); ox = oy = 0.0
    else:
        box = content_box(px, w, h, bg, tol)
        px_prof, py_prof = edge_profile(px, box, 0), edge_profile(px, box, 1)
        guess = (find_cell(px_prof) + find_cell(py_prof)) / 2      # cells are square
        cx, ox = fit_grid(px_prof, guess, box[0])
        cy, oy = fit_grid(py_prof, guess, box[1])
        c = (cx + cy) / 2
        cx = cy = c
        ox %= c; oy %= c
    gw, gh = int((w - ox) / cx), int((h - oy) / cy)
    grid = [[sample(px, ox + i * cx, oy + j * cy, ox + (i + 1) * cx, oy + (j + 1) * cy) for i in range(gw)] for j in range(gh)]
    # background: flood from the border through cells close to the background colour
    bgset = set()
    if alpha is not None:                    # a cell is background when its centre is mostly transparent
        for j in range(gh):
            for i in range(gw):
                x0, y0 = ox + i * cx, oy + j * cy
                pts = [alpha[min(w - 1, int(x0 + cx * f)), min(h - 1, int(y0 + cy * g))]
                       for f in (0.3, 0.5, 0.7) for g in (0.3, 0.5, 0.7)]
                if sorted(pts)[4] < 128:
                    bgset.add((i, j))
    q = deque() if alpha is not None else deque((i, j) for j in range(gh) for i in range(gw) if i in (0, gw - 1) or j in (0, gh - 1))
    while q:
        i, j = q.popleft()
        if (i, j) in bgset or not (0 <= i < gw and 0 <= j < gh) or not near(grid[j][i], bg, tol):
            continue
        bgset.add((i, j))
        q.extend(((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)))
    # palette clean-up
    fg = [(i, j) for j in range(gh) for i in range(gw) if (i, j) not in bgset]
    tmp = Image.new('RGB', (len(fg) or 1, 1))
    for k, (i, j) in enumerate(fg):
        tmp.putpixel((k, 0), grid[j][i])
    q8 = tmp.quantize(colors, method=Image.Quantize.MEDIANCUT).convert('RGB')
    clean = Image.new('RGBA', (gw, gh), (0, 0, 0, 0))
    for k, (i, j) in enumerate(fg):
        clean.putpixel((i, j), q8.getpixel((k, 0)) + (255,))
    # split into objects (8-connected)
    seen, objs = set(), []
    for p in fg:
        if p in seen:
            continue
        comp, dq = [], deque([p])
        while dq:
            a = dq.popleft()
            if a in seen or a in bgset or not (0 <= a[0] < gw and 0 <= a[1] < gh):
                continue
            seen.add(a); comp.append(a)
            dq.extend((a[0] + dx, a[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
        if len(comp) >= 6:
            objs.append(comp)
    objs.sort(key=lambda c: (min(p[1] for p in c) // 8, min(p[0] for p in c)))
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    report = [f'{path}: cell {cx:.2f}px, offset ({ox:.1f},{oy:.1f}), grid {gw}x{gh}, {len(objs)} object(s)']
    for n, comp in enumerate(objs, 1):
        xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
        box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
        obj = Image.new('RGBA', (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
        for (i, j) in comp:
            obj.putpixel((i - box[0], j - box[1]), clean.getpixel((i, j)))
        native = f'{out_dir}/{base}_{n}_native_{obj.width}x{obj.height}.png'
        obj.save(native)
        fit = obj
        if diagonal and max(obj.size) > size and max(obj.size) / max(1, min(obj.size)) >= 1.4:
            fit = to_diagonal(obj)                # long, thin objects fill the slot better lying corner to corner
        if max(fit.size) > size:              # only when the AI drew more cells than the target
            fit = shrink(fit, size)
        canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        canvas.alpha_composite(fit, ((size - fit.width) // 2, (size - fit.height) // 2))
        canvas.save(f'{out_dir}/{base}_{n}_{size}x{size}.png')
        ncol = len({obj.getpixel((x, y)) for y in range(obj.height) for x in range(obj.width) if obj.getpixel((x, y))[3]})
        report.append(f'  object {n}: native {obj.width}x{obj.height}, {ncol} colours'
                      + ('' if max(obj.size) <= size else f'  (more than {size} cells: shrunk, check by hand)'))
    return '\n'.join(report)


# ----------------------------------------------------------------------------------------- batch mode
# python tools/ai2pixel.py batch <in_dir>            convert every image, write the review sheet
# python tools/ai2pixel.py install <name> [<name>..]  copy reviewed icons into the pack (or "all")
#
# Name each image after the icon it replaces: the English id (carp.png, raw_calamari.png) or the
# Traditional Chinese name (鯉魚.png). One image may hold several objects: name it a+b+c.png and the
# objects are matched left-to-right, top-to-bottom.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
ITEMS = os.path.join(RP, 'textures', 'items')
STAGE = os.path.join(os.path.dirname(ROOT), 'icon_preview', 'AI轉換結果')


def icon_names():
    """id -> Chinese name, for every kfv_<id>.png icon in the pack."""
    ids = sorted(f[4:-4] for f in os.listdir(ITEMS)
                 if f.startswith('kfv_') and f.endswith('.png') and not f.endswith(('_mer.png', '_normal.png')))
    zh = {}
    for f in (os.path.join(RP, 'texts', 'zh_TW.lang'), os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]', 'texts', 'zh_TW.lang')):
        for line in open(f, encoding='utf-8'):
            if '=' not in line:
                continue
            k, v = line.rstrip('\n').split('=', 1)
            for pre in ('kaleidoscope_fishing.display.item.', 'kaleidoscope_fishing.name.'):
                if k.startswith(pre):
                    zh.setdefault(k[len(pre):], v.split('\\n')[0])
    return {i: zh.get(i, i) for i in ids}


def resolve(stem, names):
    by_zh = {v: k for k, v in names.items()}
    out = []
    for part in stem.split('+'):
        part = part.strip()
        if part in names:
            out.append(part)
        elif part in by_zh:
            out.append(by_zh[part])
        else:
            out.append(None)
    return out


def batch(in_dir, size=16):
    names = icon_names()
    os.makedirs(STAGE, exist_ok=True)
    tmp = os.path.join(STAGE, '_raw')
    lines, done = [], []
    files = sorted(f for f in os.listdir(in_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')))
    for f in files:
        stem = os.path.splitext(f)[0]
        ids = resolve(stem, names)
        rep = convert(os.path.join(in_dir, f), tmp)
        lines.append(rep)
        mine = lambda g: g.startswith(stem + '_') and g[len(stem) + 1:].split('_')[0].isdigit()
        outs = sorted((g for g in os.listdir(tmp) if mine(g) and g.endswith(f'_{size}x{size}.png')),
                      key=lambda g: int(g[len(stem) + 1:].split('_')[0]))
        natives = {int(g[len(stem) + 1:].split('_')[0]): g for g in os.listdir(tmp) if mine(g) and '_native_' in g}
        if len(outs) != len(ids):
            lines.append(f'  !! {f}: found {len(outs)} object(s) but the name lists {len(ids)}; nothing staged')
            continue
        for k, (g, i) in enumerate(zip(outs, ids), 1):
            if i is None:
                lines.append(f'  !! {f}: "{stem.split("+")[k - 1]}" is not an icon name; skipped')
                continue
            nat = Image.open(os.path.join(tmp, natives[k]))
            ok = max(nat.size) <= size
            Image.open(os.path.join(tmp, g)).save(os.path.join(STAGE, f'{i}.png'))
            done.append((i, names[i], nat.size, ok))
            lines.append(f'  -> {i} ({names[i]}): {nat.width}x{nat.height} cells' + ('' if ok else '  !! more than 16 cells, shrunk: check by hand'))
    open(os.path.join(STAGE, '_報告.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    sheet(done, os.path.join(os.path.dirname(STAGE), 'AI轉換對照.png'))
    print('\n'.join(lines))
    print(f'staged {len(done)} icon(s) in {STAGE}')


def sheet(done, out):
    from PIL import ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 15)
    except Exception:
        font = ImageFont.load_default()
    C, cols = 128, 4
    pw = 2 * C + 40
    rows = max(1, (len(done) + cols - 1) // cols)
    im = Image.new('RGB', (40 + cols * (pw + 20), 50 + rows * (C + 50)), 'white')
    d = ImageDraw.Draw(im)
    d.text((20, 12), '左：現在　右：AI 轉換後（紅字＝原圖超過 16 格，被硬縮過，要手修）', fill='black', font=font)
    for n, (i, zh, nsize, ok) in enumerate(done):
        x = 20 + (n % cols) * (pw + 20); y = 45 + (n // cols) * (C + 50)
        for j, p in enumerate([os.path.join(ITEMS, f'kfv_{i}.png'), os.path.join(STAGE, f'{i}.png')]):
            t = Image.open(p).convert('RGBA').resize((C, C), Image.NEAREST)
            bg = Image.new('RGBA', (C, C), 'white'); bg.alpha_composite(t)
            im.paste(bg.convert('RGB'), (x + j * (C + 20), y))
        d.text((x, y + C + 5), f'{zh}  {i}  原圖 {nsize[0]}×{nsize[1]} 格', fill='black' if ok else 'red', font=font)
    im.save(out)


def normal_from(icon):
    """A gentle normal map from the icon's brightness, so the RTX look follows the new shape."""
    w, h = icon.size
    lum = [[(sum(icon.getpixel((x, y))[:3]) / 765.0 if icon.getpixel((x, y))[3] else 0.0) for x in range(w)] for y in range(h)]
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            a = icon.getpixel((x, y))[3]
            if not a:
                continue
            L = lambda xx, yy: lum[min(h - 1, max(0, yy))][min(w - 1, max(0, xx))]
            dx = (L(x + 1, y) - L(x - 1, y)) * 2.0
            dy = (L(x, y + 1) - L(x, y - 1)) * 2.0
            nz = 1.0
            n = (dx * dx + dy * dy + nz * nz) ** 0.5
            out.putpixel((x, y), (int((-dx / n * 0.5 + 0.5) * 255), int((dy / n * 0.5 + 0.5) * 255), int((nz / n * 0.5 + 0.5) * 255), 255))
    return out


def install(which):
    """Copy staged icons into the pack. The old _mer / _normal maps are redrawn for the new shape:
    the normal map from the new icon, the MER map keeps the old one's average values."""
    staged = {f[:-4] for f in os.listdir(STAGE) if f.endswith('.png') and not f.startswith('_')}
    names = icon_names()
    targets = sorted(staged) if which == ['all'] else [resolve(w, names)[0] or w for w in which]
    for i in targets:
        if i not in staged:
            print(f'!! {i}: not staged'); continue
        icon = Image.open(os.path.join(STAGE, f'{i}.png')).convert('RGBA')
        base = os.path.join(ITEMS, f'kfv_{i}')
        mer_p, nor_p = base + '_mer.png', base + '_normal.png'
        if os.path.exists(mer_p):
            old = Image.open(mer_p).convert('RGBA')
            px = [old.getpixel((x, y)) for y in range(old.height) for x in range(old.width)]
            px = [c for c in px if c[3]] or [(0, 0, 230, 255)]
            avg = tuple(sum(c[k] for c in px) // len(px) for k in range(3)) + (255,)
            mer = Image.new('RGBA', icon.size, (0, 0, 0, 0))
            for y in range(icon.height):
                for x in range(icon.width):
                    if icon.getpixel((x, y))[3]:
                        mer.putpixel((x, y), avg)
            mer.save(mer_p)
        if os.path.exists(nor_p):
            normal_from(icon).save(nor_p)
        icon.save(base + '.png')
        print(f'installed kfv_{i}.png ({names.get(i, i)})')


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'batch':
        batch(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == 'install':
        install(sys.argv[2:])
    else:
        ap = argparse.ArgumentParser()
        ap.add_argument('image'); ap.add_argument('out_dir')
        ap.add_argument('--cell', type=float); ap.add_argument('--bg', default='ffffff')
        ap.add_argument('--size', type=int, default=16); ap.add_argument('--colors', type=int, default=32)
        a = ap.parse_args()
        bg = tuple(int(a.bg[i:i + 2], 16) for i in (0, 2, 4))
        print(convert(a.image, a.out_dir, a.cell, bg, a.size, a.colors))
