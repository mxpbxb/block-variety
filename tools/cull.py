"""Chipped blocks Block Variety leaves out, and the shine taken out of the rest.

`CUT`: a block id and why it is left out. Chipped's newer textures are airbrushed and glossy
next to the old pixel-art ones: where a group has a few of them they are cut; where every block of
a group is drawn that way (the metal and gem blocks, `DESHINE`), the shine is painted out instead
(`deshine`). The raw ore blocks keep 30 of their 61 patterns: the most alike ones are cut.

`deshine`: takes the glossy shading out of a texture: Chipped 1.18's metal and gem blocks are drawn with
diagonal light and shadow streaks over their pattern. Each pixel that is only a little lighter or
darker than the block's body colour and not part of a straight (horizontal or vertical) line of at
least 4 such pixels becomes the body colour; strong dark lines (the engraving) and the edge rows
are kept, their light pixels toned down."""
import re

import png

def Y(p): return 0.299*p[0] + 0.587*p[1] + 0.114*p[2]

def deshine(im, run=4, strong=0.83):
    w, h = im.w, min(im.w, im.h)
    px = [[tuple(im.get(x, y)) for x in range(w)] for y in range(h)]
    solid = sorted(Y(px[y][x]) for y in range(h) for x in range(w) if px[y][x][3] > 128)
    mid = solid[len(solid)//2]
    pal = sorted({px[y][x][:3] for y in range(h) for x in range(w) if px[y][x][3] > 128}, key=lambda c: abs(Y(c) - mid))
    body = pal[0]; by = Y(body)
    def side(p):
        if p[3] <= 128: return 0
        d = Y(p) - by
        return 0 if abs(d) <= by*0.03 else (1 if d > 0 else -1)
    def run_len(x, y, dx, dy):
        s = side(px[y][x]); n = 1
        for k in (1, -1):
            i, j = x + dx*k, y + dy*k
            while 0 <= i < w and 0 <= j < h and side(px[j][i]) == s:
                n += 1; i += dx*k; j += dy*k
        return n
    def toned(p):  # a light pixel brought halfway to the body
        t = by + (Y(p) - by)*0.5
        c = min(pal, key=lambda c: abs(Y(c) - t))
        return c + (p[3],)
    out = png.Image(im.w, im.h, bytearray(im.px))
    for y in range(h):
        for x in range(w):
            p = px[y][x]; s = side(p)
            if s == 0: continue
            if s < 0 and Y(p) < by*strong: continue
            edge = x in (0, w-1) or y in (0, h-1)
            straight = max(run_len(x, y, 1, 0), run_len(x, y, 0, 1)) >= run
            if edge or straight:
                q = toned(p) if s > 0 else p
            else:
                q = body + (p[3],)
            i = (y*im.w + x)*4; out.px[i:i+4] = bytes(q)
    return out


# The groups drawn glossy all through: their textures (`<group>_<n>.png`) get `deshine`.
DESHINE = re.compile(r'(diamond|emerald|gold|iron|netherite)_block_\d+')

CUT = {
    'raw_iron_block_1': 'raw block, half cut: 59% like Raw Iron Block (Chipped 35)',
    'raw_iron_block_6': 'raw block, half cut: 89% like Raw Iron Block (Chipped 44)',
    'raw_iron_block_9': 'raw block, half cut: 55% like Raw Iron Block (Chipped 8)',
    'raw_iron_block_10': 'raw block, half cut: 69% like Raw Iron Block (Chipped 9)',
    'raw_iron_block_11': 'raw block, half cut: 83% like Raw Iron Block (Chipped 17)',
    'raw_iron_block_12': 'raw block, half cut: 87% like Raw Iron Block (Chipped 11)',
    'raw_iron_block_13': 'raw block, half cut: 57% like Raw Iron Block (Chipped 3)',
    'raw_iron_block_14': 'raw block, half cut: 70% like Raw Iron Block (Chipped 48)',
    'raw_iron_block_15': 'raw block, half cut: 76% like Raw Iron Block (Chipped 14)',
    'raw_iron_block_16': 'raw block, half cut: 85% like Raw Iron Block (Chipped 52)',
    'raw_iron_block_17': 'raw block, half cut: 73% like Raw Iron Block (Chipped 5)',
    'raw_iron_block_18': 'raw block, half cut: 86% like Raw Iron Block (Chipped 20)',
    'raw_iron_block_19': 'raw block, half cut: 80% like Raw Iron Block (Chipped 17)',
    'raw_iron_block_20': 'raw block, half cut: 85% like Raw Iron Block (Chipped 17)',
    'raw_iron_block_22': 'raw block, half cut: 71% like Raw Iron Block (Chipped 44)',
    'raw_iron_block_26': 'raw block, half cut: 73% like Raw Iron Block (Chipped 34)',
    'raw_iron_block_27': 'raw block, half cut: 77% like Raw Iron Block (Chipped 2)',
    'raw_iron_block_28': 'raw block, half cut: 57% like Raw Iron Block (Chipped 5)',
    'raw_iron_block_29': 'raw block, half cut: 53% like Raw Iron Block (Chipped 45)',
    'raw_iron_block_33': 'raw block, half cut: 53% like Raw Iron Block (Chipped 37)',
    'raw_iron_block_35': 'raw block, half cut: 54% like Raw Iron Block (Chipped 37)',
    'raw_iron_block_36': 'raw block, half cut: 64% like Raw Iron Block (Chipped 38)',
    'raw_iron_block_40': 'raw block, half cut: 55% like Raw Iron Block (Chipped 24)',
    'raw_iron_block_41': 'raw block, half cut: 53% like Raw Iron Block (Chipped 31)',
    'raw_iron_block_42': 'raw block, half cut: 59% like Raw Iron Block (Chipped 45)',
    'raw_iron_block_44': 'raw block, half cut: 60% like Raw Iron Block (Chipped 5)',
    'raw_iron_block_48': 'raw block, half cut: 61% like Raw Iron Block (Chipped 37)',
    'raw_iron_block_49': 'raw block, half cut: 72% like Raw Iron Block (Chipped 5)',
    'raw_iron_block_50': 'raw block, half cut: 54% like Raw Iron Block (Chipped 37)',
    'raw_iron_block_51': 'raw block, half cut: 59% like Raw Iron Block (Chipped 29)',
    'raw_iron_block_54': 'raw block, half cut: 53% like Raw Iron Block (Chipped 47)',
    'raw_gold_block_1': 'raw block, half cut: 59% like Raw Gold Block (Chipped 35)',
    'raw_gold_block_6': 'raw block, half cut: 89% like Raw Gold Block (Chipped 44)',
    'raw_gold_block_9': 'raw block, half cut: 55% like Raw Gold Block (Chipped 8)',
    'raw_gold_block_10': 'raw block, half cut: 69% like Raw Gold Block (Chipped 9)',
    'raw_gold_block_11': 'raw block, half cut: 83% like Raw Gold Block (Chipped 17)',
    'raw_gold_block_12': 'raw block, half cut: 87% like Raw Gold Block (Chipped 11)',
    'raw_gold_block_13': 'raw block, half cut: 57% like Raw Gold Block (Chipped 3)',
    'raw_gold_block_14': 'raw block, half cut: 70% like Raw Gold Block (Chipped 48)',
    'raw_gold_block_15': 'raw block, half cut: 76% like Raw Gold Block (Chipped 14)',
    'raw_gold_block_16': 'raw block, half cut: 85% like Raw Gold Block (Chipped 52)',
    'raw_gold_block_17': 'raw block, half cut: 73% like Raw Gold Block (Chipped 5)',
    'raw_gold_block_18': 'raw block, half cut: 86% like Raw Gold Block (Chipped 20)',
    'raw_gold_block_19': 'raw block, half cut: 80% like Raw Gold Block (Chipped 17)',
    'raw_gold_block_20': 'raw block, half cut: 85% like Raw Gold Block (Chipped 17)',
    'raw_gold_block_22': 'raw block, half cut: 71% like Raw Gold Block (Chipped 44)',
    'raw_gold_block_26': 'raw block, half cut: 73% like Raw Gold Block (Chipped 34)',
    'raw_gold_block_27': 'raw block, half cut: 77% like Raw Gold Block (Chipped 2)',
    'raw_gold_block_28': 'raw block, half cut: 57% like Raw Gold Block (Chipped 5)',
    'raw_gold_block_29': 'raw block, half cut: 53% like Raw Gold Block (Chipped 45)',
    'raw_gold_block_33': 'raw block, half cut: 53% like Raw Gold Block (Chipped 37)',
    'raw_gold_block_35': 'raw block, half cut: 54% like Raw Gold Block (Chipped 37)',
    'raw_gold_block_36': 'raw block, half cut: 64% like Raw Gold Block (Chipped 38)',
    'raw_gold_block_40': 'raw block, half cut: 55% like Raw Gold Block (Chipped 24)',
    'raw_gold_block_41': 'raw block, half cut: 53% like Raw Gold Block (Chipped 31)',
    'raw_gold_block_42': 'raw block, half cut: 59% like Raw Gold Block (Chipped 45)',
    'raw_gold_block_44': 'raw block, half cut: 60% like Raw Gold Block (Chipped 5)',
    'raw_gold_block_48': 'raw block, half cut: 61% like Raw Gold Block (Chipped 37)',
    'raw_gold_block_49': 'raw block, half cut: 72% like Raw Gold Block (Chipped 5)',
    'raw_gold_block_50': 'raw block, half cut: 54% like Raw Gold Block (Chipped 37)',
    'raw_gold_block_51': 'raw block, half cut: 59% like Raw Gold Block (Chipped 29)',
    'raw_gold_block_54': 'raw block, half cut: 53% like Raw Gold Block (Chipped 47)',
    'raw_copper_block_1': 'raw block, half cut: 59% like Raw Copper Block (Chipped 35)',
    'raw_copper_block_6': 'raw block, half cut: 89% like Raw Copper Block (Chipped 44)',
    'raw_copper_block_9': 'raw block, half cut: 55% like Raw Copper Block (Chipped 8)',
    'raw_copper_block_10': 'raw block, half cut: 69% like Raw Copper Block (Chipped 9)',
    'raw_copper_block_11': 'raw block, half cut: 83% like Raw Copper Block (Chipped 17)',
    'raw_copper_block_12': 'raw block, half cut: 87% like Raw Copper Block (Chipped 11)',
    'raw_copper_block_13': 'raw block, half cut: 57% like Raw Copper Block (Chipped 3)',
    'raw_copper_block_14': 'raw block, half cut: 70% like Raw Copper Block (Chipped 48)',
    'raw_copper_block_15': 'raw block, half cut: 76% like Raw Copper Block (Chipped 14)',
    'raw_copper_block_16': 'raw block, half cut: 85% like Raw Copper Block (Chipped 52)',
    'raw_copper_block_17': 'raw block, half cut: 73% like Raw Copper Block (Chipped 5)',
    'raw_copper_block_18': 'raw block, half cut: 86% like Raw Copper Block (Chipped 20)',
    'raw_copper_block_19': 'raw block, half cut: 80% like Raw Copper Block (Chipped 17)',
    'raw_copper_block_20': 'raw block, half cut: 85% like Raw Copper Block (Chipped 17)',
    'raw_copper_block_22': 'raw block, half cut: 71% like Raw Copper Block (Chipped 44)',
    'raw_copper_block_26': 'raw block, half cut: 73% like Raw Copper Block (Chipped 34)',
    'raw_copper_block_27': 'raw block, half cut: 77% like Raw Copper Block (Chipped 2)',
    'raw_copper_block_28': 'raw block, half cut: 57% like Raw Copper Block (Chipped 5)',
    'raw_copper_block_29': 'raw block, half cut: 53% like Raw Copper Block (Chipped 45)',
    'raw_copper_block_33': 'raw block, half cut: 53% like Raw Copper Block (Chipped 37)',
    'raw_copper_block_35': 'raw block, half cut: 54% like Raw Copper Block (Chipped 37)',
    'raw_copper_block_36': 'raw block, half cut: 64% like Raw Copper Block (Chipped 38)',
    'raw_copper_block_40': 'raw block, half cut: 55% like Raw Copper Block (Chipped 24)',
    'raw_copper_block_41': 'raw block, half cut: 53% like Raw Copper Block (Chipped 31)',
    'raw_copper_block_42': 'raw block, half cut: 59% like Raw Copper Block (Chipped 45)',
    'raw_copper_block_44': 'raw block, half cut: 60% like Raw Copper Block (Chipped 5)',
    'raw_copper_block_48': 'raw block, half cut: 61% like Raw Copper Block (Chipped 37)',
    'raw_copper_block_49': 'raw block, half cut: 72% like Raw Copper Block (Chipped 5)',
    'raw_copper_block_50': 'raw block, half cut: 54% like Raw Copper Block (Chipped 37)',
    'raw_copper_block_51': 'raw block, half cut: 59% like Raw Copper Block (Chipped 29)',
    'raw_copper_block_54': 'raw block, half cut: 53% like Raw Copper Block (Chipped 47)',
    'glowstone_2': 'shiny new style: a smooth round lamp, airbrushed shading',
    'glowstone_7': 'shiny new style: a smooth airbrushed square, no pixel texture',
    'glowstone_9': 'shiny new style: glossy diagonal shine streaks',
    'glowstone_11': 'shiny new style: a smooth airbrushed pyramid',
    'glowstone_12': 'shiny new style: glossy diagonal shine streaks',
    'glowstone_16': 'shiny new style: smooth airbrushed rings',
    'glowstone_17': 'shiny new style: a smooth airbrushed panel in a frame',
    'shroomlight_6': 'shiny new style: a smooth airbrushed square, no pixel texture',
    'shroomlight_8': 'shiny new style: glossy diagonal shine streaks',
    'shroomlight_9': 'shiny new style: a smooth airbrushed pyramid',
    'shroomlight_10': 'shiny new style: glossy diagonal shine streaks',
    'shroomlight_13': 'shiny new style: smooth airbrushed rings',
    'shroomlight_14': 'shiny new style: a smooth airbrushed panel in a frame',
    'diamond_block_12': 'shiny new style: only a shine and a frame, the plain block once the shine is out',
    'emerald_block_12': 'shiny new style: only a shine and a frame, the plain block once the shine is out',
    'gold_block_12': 'shiny new style: only a shine and a frame, the plain block once the shine is out',
    'iron_block_12': 'shiny new style: only a shine and a frame, the plain block once the shine is out',
    'netherite_block_12': 'shiny new style: only a shine and a frame, the plain block once the shine is out',
}
