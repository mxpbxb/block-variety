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
