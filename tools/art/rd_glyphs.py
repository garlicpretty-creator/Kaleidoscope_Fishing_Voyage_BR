"""Glyph pictures drawn with Retro Diffusion (https://www.retrodiffusion.ai), 1.6.0.

Prompts: tools/art/glyph_prompts.json. The key is read from the environment, never from the repository:

    $env:RETRODIFFUSION_API_KEY = ...               # never commit or paste it
    python tools/art/rd_glyphs.py generate          # candidates for every glyph not picked yet
    python tools/art/rd_glyphs.py generate water.lake minecraft:egg   # only these (again)
    python tools/art/rd_glyphs.py sheet             # contact sheet of the candidates
    python tools/art/rd_glyphs.py pick water.lake 2 minecraft:egg 0   # keep candidate n

Candidates go to tools/art/candidates/<name>/<n>.png (not committed) with a contact sheet
tools/art/candidates/sheet.png. `pick` writes the chosen one, cleaned to a 16x16 glyph (hard alpha, and a
white outline for symbols marked "outline"), to tools/data/glyph_src: an item id "ns:item" to
glyph_src/ns/item.png, a symbol to glyph_src/<name>.png. Then `python tools/build.py build` puts it into the
glyph sheet in the same cell. An entry with "dest" (a path from the repository root) is picked there instead:
the 1.6.0 item art (Hand Net), which tools/gen_basket_net_icons.py then finishes. glyph_picks.json records the choices.
"""
import base64, json, os, shutil, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PROMPTS = os.path.join(HERE, "glyph_prompts.json")
CAND = os.path.join(HERE, "candidates")
PICKS = os.path.join(HERE, "glyph_picks.json")
SRC = os.path.join(ROOT, "tools", "data", "glyph_src")
API = "https://api.retrodiffusion.ai/v1"


def config():
    return json.load(open(PROMPTS, encoding="utf-8"))


def folder(name):
    return os.path.join(CAND, name.replace(":", "__"))


def request(method, path, body=None):
    key = os.environ.get("RETRODIFFUSION_API_KEY", "").strip()
    if not key:
        sys.exit("set RETRODIFFUSION_API_KEY in the environment first")
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None, method=method)
    req.add_header("X-RD-Token", key)
    req.add_header("Content-Type", "application/json")
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < 7:
                time.sleep(float(e.headers.get("Retry-After", "8")))
                continue
            raise SystemExit(f"{method} {path}: HTTP {e.code} {e.read().decode(errors='replace')[:400]}")
    raise SystemExit(f"{method} {path}: gave up")


def images_of(payload):
    if isinstance(payload, dict):
        if isinstance(payload.get("base64_images"), list) and payload["base64_images"]:
            return payload["base64_images"]
        for v in payload.values():
            f = images_of(v)
            if f:
                return f
    return None


def generate_one(cfg, name, entry):
    body = {"prompt": entry["prompt"], "prompt_style": entry.get("style", cfg["style"]), "width": entry.get("size", cfg["size"]),
            "height": entry.get("size", cfg["size"]), "num_images": cfg["candidates"], "seed": entry.get("seed", cfg.get("seed")), "remove_bg": True}
    if "init" in entry:                          # image to image: redraw a picture kept in the repository
        body["input_image"] = base64.b64encode(open(os.path.join(ROOT, entry["init"]), "rb").read()).decode()
        body["strength"] = entry.get("strength", 0.45)
    started = request("POST", "/inferences", body)
    imgs, task = images_of(started), started.get("task_id")
    while not imgs:
        if not task:
            raise SystemExit(f"{name}: unexpected response {json.dumps(started)[:300]}")
        time.sleep(2)
        st = request("GET", f"/inferences/tasks/{task}")
        if str(st.get("status", "")).lower() in ("failed", "error", "cancelled", "canceled"):
            raise SystemExit(f"{name}: task {st.get('status')}")
        imgs = images_of(st)
    d = folder(name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for n, b in enumerate(imgs):
        open(os.path.join(d, f"{n}.png"), "wb").write(base64.b64decode(b))
    print("done", name, flush=True)


def picked():
    return json.load(open(PICKS, encoding="utf-8")) if os.path.exists(PICKS) else {}


def cmd_generate(only):
    cfg = config()
    items = cfg["items"]
    names = only or [n for n in items if n not in picked() and not os.path.isdir(folder(n))]
    bad = [n for n in names if n not in items]
    if bad:
        sys.exit("no prompt for: " + ", ".join(bad))
    print(f"generating {len(names)} glyphs x {cfg['candidates']}")
    with ThreadPoolExecutor(2) as pool:          # the API allows 2 jobs at a time
        list(pool.map(lambda n: generate_one(cfg, n, items[n]), names))
    cmd_sheet()


def clean(path, ring):
    img = Image.open(path).convert("RGBA")
    n = img.width if img.width in (16, 32) else 16
    if img.size != (n, n):
        img = img.resize((n, n), Image.NEAREST)
    px = img.load()
    for y in range(n):
        for x in range(n):
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    if ring:
        out = img.copy()
        o = out.load()
        for y in range(16):
            for x in range(16):
                if not px[x, y][3] and any(0 <= x + dx < 16 and 0 <= y + dy < 16 and px[x + dx, y + dy][3]
                                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    o[x, y] = (255, 255, 255, 255)
        img = out
    return img


def cmd_sheet():
    cfg = config()["items"]
    names = [n for n in cfg if os.path.isdir(folder(n))]
    if not names:
        return
    s, label, cols = 4, 190, 5
    cell = 16 * s + 6
    sheet = Image.new("RGB", (label + cols * cell + 6, len(names) * cell + 4), (58, 58, 64))
    d = ImageDraw.Draw(sheet)
    pk = picked()
    for row, n in enumerate(names):
        y = 2 + row * cell
        d.text((4, y + cell // 2 - 6), n + (f"  [{pk[n]}]" if n in pk else ""), fill=(230, 230, 230))
        files = sorted((f for f in os.listdir(folder(n)) if f.endswith(".png")), key=lambda f: int(f[:-4]))
        for col, f in enumerate(files[:cols]):
            x = label + col * cell
            d.rectangle([x, y, x + 16 * s - 1, y + 16 * s - 1], fill=(139, 139, 139))
            big = clean(os.path.join(folder(n), f), cfg[n].get("outline")).resize((16 * s, 16 * s), Image.NEAREST)
            sheet.paste(big, (x, y), big)
            d.text((x + 2, y + 1), f[:-4], fill=(255, 220, 120))
    p = os.path.join(CAND, "sheet.png")
    sheet.save(p)
    print("contact sheet:", os.path.relpath(p, ROOT))


def target(name):
    ns, colon, item = name.partition(":")
    return os.path.join(SRC, ns, item + ".png") if colon else os.path.join(SRC, name + ".png")


def cmd_pick(args):
    if len(args) % 2:
        sys.exit("usage: pick <name> <n> [<name> <n> ...]")
    cfg, pk = config()["items"], picked()
    for name, n in zip(args[::2], args[1::2]):
        src = os.path.join(folder(name), f"{n}.png")
        if not os.path.exists(src):
            sys.exit(f"no candidate {src}")
        t = os.path.join(ROOT, cfg[name]["dest"]) if "dest" in cfg[name] else target(name)
        os.makedirs(os.path.dirname(t), exist_ok=True)
        clean(src, cfg[name].get("outline")).save(t)
        pk[name] = int(n)
        print(f"picked {name} <- {n}")
    with open(PICKS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(sorted(pk.items())), f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("help", [])
    {"generate": lambda: cmd_generate(args), "sheet": cmd_sheet, "pick": lambda: cmd_pick(args)}.get(cmd, lambda: print(__doc__))()
