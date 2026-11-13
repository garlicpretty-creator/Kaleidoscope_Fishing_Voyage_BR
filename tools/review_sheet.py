"""Old-vs-new review sheet for staged icons.

usage: python tools/review_sheet.py <title> <out.png> name [name ...]
       a name ending in * is marked as hand touched-up.
Each cell: old icon -> new icon -> new icon in an inventory slot at real size (x3). Chinese names come from zh_TW.lang.
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
TEX = os.path.join(RP, 'textures', 'items')
STAGE = os.path.join(os.path.dirname(ROOT), 'icon_preview', 'AI轉換結果')


def zh_names():
    out = {}
    with open(os.path.join(RP, 'texts', 'zh_TW.lang'), encoding='utf-8') as f:
        for line in f:
            if line.startswith('kaleidoscope_fishing.name.') and '=' in line:
                k, v = line.rstrip('\n').split('=', 1)
                out[k[len('kaleidoscope_fishing.name.'):]] = v
    return out


def main(title, out_path, names):
    zh = zh_names()
    font = ImageFont.truetype(r'C:\Windows\Fonts\msjh.ttc', 17)
    S = 6; T = 16 * S; cw = T * 2 + 54 + 30; ch = T + 34; cols = 5
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cw + 20, rows * ch + 50), (232, 230, 222))
    d = ImageDraw.Draw(sheet)
    d.text((12, 10), title, font=font, fill=(40, 40, 40))

    def slot(im):
        b = Image.new('RGBA', (18, 18), (139, 139, 139, 255)); b.alpha_composite(im, (1, 1))
        return b.resize((54, 54), Image.NEAREST).convert('RGB')

    for i, raw in enumerate(names):
        mark = raw.endswith('*'); n = raw.rstrip('*')
        x = 10 + (i % cols) * cw; y = 42 + (i // cols) * ch
        p = os.path.join(TEX, f'kfv_{n}.png')
        old = Image.open(p).convert('RGBA') if os.path.exists(p) else Image.new('RGBA', (16, 16))
        if old.size != (16, 16):
            old = old.resize((16, 16), Image.NEAREST)
        new = Image.open(os.path.join(STAGE, f'{n}.png')).convert('RGBA')
        for k, im in enumerate((old, new)):
            b = Image.new('RGBA', (T, T), (139, 139, 139, 255)); b.alpha_composite(im.resize((T, T), Image.NEAREST))
            sheet.paste(b.convert('RGB'), (x + k * (T + 4), y))
        sheet.paste(slot(new), (x + 2 * T + 12, y + T - 54))
        d.text((x, y + T + 2), zh.get(n, n) + ('*' if mark else ''), font=font, fill=(40, 40, 40))
    sheet.save(out_path)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
