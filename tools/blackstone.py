"""Chipped's blackstone, darkened into Programmer Art Continuation's: each pixel's lightness mapped
from Chipped's blackstone's spread onto the pack's (its mean and spread), in the pack's neutral grey.
The gold of gilded blackstone stays as it is.

    from blackstone import darken; darken(image)   # a png.Image, changed in place
"""
import png

# Lightness (Rec. 601) of Chipped's blackstone variants together, and of the pack's blackstone.
SRC_MEAN, SRC_SD = 47.0, 21.8
DST_MEAN, DST_SD = 26.4, 19.2


def is_gold(r, g, b):
    return max(r, g, b) - min(r, g, b) > 40 and r > 90 and r >= g >= b


def darken(im):
    px = im.px
    for i in range(0, len(px), 4):
        r, g, b, a = px[i:i + 4]
        if a == 0 or is_gold(r, g, b):
            continue
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        v = (lum - SRC_MEAN) / SRC_SD * DST_SD + DST_MEAN
        v = max(0, min(255, round(v)))
        px[i:i + 3] = bytes((v, v, v))
    return im


# Chipped's basalt variants together, and the pack's basalt_side and basalt_top together. Chipped's
# is lighter-spread and bluer; the pack's is a near-neutral grey with a trace of blue.
BASALT_SRC = 81.2, 33.0
BASALT_DST = 80.5, 19.1
BASALT_TINT = (0, 0, 1)
# Chisel's basalt (in vanilla basalt's group): darker and flatter than the pack's.
CHISEL_BASALT_SRC = 50.1, 10.7


def basalt(im, src=BASALT_SRC):
    """Basalt onto the pack's: its lightness mapped onto the pack's spread, its colour the pack's grey."""
    (sm, ss), (dm, ds) = src, BASALT_DST
    px = im.px
    for i in range(0, len(px), 4):
        r, g, b, a = px[i:i + 4]
        if a == 0:
            continue
        v = (0.299 * r + 0.587 * g + 0.114 * b - sm) / ss * ds + dm
        px[i:i + 3] = bytes(max(0, min(255, round(v + t))) for t in BASALT_TINT)
    return im


def lightness_stats(paths):
    """Mean and spread of the lightness of `paths`' stone pixels (to set SRC_* from)."""
    import statistics
    vals = []
    for p in paths:
        im = png.read(p)
        for i in range(0, len(im.px), 4):
            r, g, b, a = im.px[i:i + 4]
            if a >= 128 and not is_gold(r, g, b):
                vals.append(0.299 * r + 0.587 * g + 0.114 * b)
    return statistics.mean(vals), statistics.pstdev(vals)
