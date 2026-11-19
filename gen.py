#!/usr/bin/env python3
"""Builds the Horizon content mod `block_variety` (Block Variety): every block of Chipped and Chisel,
and Block Carpentry's frames, in one mod.

    python3 -I gen.py <unpacked chipped jar> <unpacked Chisel jar> <vanilla 26.3 data dir> <out dir> <unpacked Block Carpentry jar>

Everything is written under the namespace `chipped` first and moved to `block_variety` at the end.

Chipped (1.16, by Terrarium) gives its blocks as `chipped:<base>_<n>`, kept as they are. Chisel
(1.12.2, by the Chisel team) gives each block's variants in one forge blockstate; each variant
becomes `chipped:chisel_<block>_<variant>` (Horizon declares a mod's blocks in its own namespace).
Chisel's layered models (an overlay on a base) are flattened into one texture each, and its
connected textures drawn as their plain tile. There are no Chipped workbenches: the chisel (the
native part `block_variety_native`) turns a group's blocks into one another. A group is a vanilla block's
family (the vanilla block first), or a Chisel block of its own with no vanilla block.

Each block copies its vanilla template's behaviour, loot (dropping itself where the template
drops itself) and tags (mining tool, tool level, and the rest).
"""
import hashlib, json, os, re, shutil, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
import png  # noqa: E402
import blackstone  # noqa: E402
# Chipped's blackstone (and gilded blackstone), darkened into Programmer Art Continuation's.
BLACKSTONE = re.compile(r'(gilded_)?blackstone_\d+$')
# Chipped's basalt, brought onto the pack's basalt the same way.
BASALT = re.compile(r'basalt_\d+$')

CHIPPED, CHISEL, VANILLA, OUT = sys.argv[1:5]
VERSION = "0.3.0"
DIRS = ['down', 'up', 'north', 'south', 'west', 'east']
COLORS = {'black': 'black', 'blue': 'blue', 'brown': 'brown', 'cyan': 'cyan', 'gray': 'gray', 'green': 'green',
          'lightblue': 'light_blue', 'light_blue': 'light_blue', 'lightgray': 'light_gray', 'light_gray': 'light_gray',
          'silver': 'light_gray', 'lime': 'lime', 'magenta': 'magenta', 'orange': 'orange', 'pink': 'pink',
          'purple': 'purple', 'red': 'red', 'white': 'white', 'yellow': 'yellow'}
# Chipped's crafting stations: left out (the chisel does their work).
WORKBENCHES = {'alchemy_bench', 'botanist_workbench', 'carpenters_table', 'glassblower', 'loom_table',
               'mason_table', 'mechanist_workbench'}
# Blocks that have no item (placed only by their standing form), and that form's item.
WALL = {'minecraft:wall_torch': 'minecraft:torch', 'minecraft:redstone_wall_torch': 'minecraft:redstone_torch'}

if os.path.isdir(OUT):
    for sub in ('assets', 'data'):
        shutil.rmtree(os.path.join(OUT, sub), ignore_errors=True)
os.makedirs(OUT, exist_ok=True)


def wjson(rel, obj):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', newline='\n') as f:
        json.dump(obj, f, indent=1)
        f.write('\n')


def copy(src, rel):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    shutil.copyfile(src, p)


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


# ---- Vanilla: which blocks exist, their loot and their tags -----------------------------------
VLOOT = os.path.join(VANILLA, 'data/minecraft/loot_table/blocks')
def exists(block):
    return block in WALL or os.path.exists(os.path.join(VLOOT, block.split(':')[1] + '.json'))

def read_tags(kind):
    root = os.path.join(VANILLA, 'data/minecraft/tags', kind)
    by_member = {}
    for r, _, fs in os.walk(root):
        for f in fs:
            if f.endswith('.json'):
                tag = os.path.relpath(os.path.join(r, f), root)[:-5].replace(os.sep, '/')
                for v in load(os.path.join(r, f)).get('values', []):
                    v = v if isinstance(v, str) else v.get('id', '')
                    if not v.startswith('#'):
                        by_member.setdefault(v if ':' in v else 'minecraft:' + v, []).append(tag)
    return by_member
BLOCK_TAGS, ITEM_TAGS = read_tags('block'), read_tags('item')

lang, tabs, report = {}, {'chipped': [], 'chisel': []}, {'blocks': 0, 'left_out': {}}
out_tags = {'block': {}, 'item': {}}
groups, group_order, itemless = {}, [], []


def left_out(why, what):
    report['left_out'].setdefault(why, []).append(what)


def swap(obj, new):
    if isinstance(obj, dict):
        return {k: swap(v, new) for k, v in obj.items()}
    if isinstance(obj, list):
        return [swap(v, new) for v in obj]
    return new.get(obj, obj) if isinstance(obj, str) else obj


def block(bid, template, group, name, tab, item=True, standing=None):
    """One block's Horizon declaration, loot, tags, name, tab place and group."""
    full = 'chipped:' + bid
    wjson('data/chipped/horizon/block/%s.json' % bid, {'template': template, 'item': item})
    # Loot: the template's, with the template (and its item) swapped for this block's item.
    src_t = WALL.get(template, template)
    drop = full if item else standing
    loot_file = os.path.join(VLOOT, src_t.split(':')[1] + '.json')
    if os.path.exists(loot_file):
        loot = swap(load(loot_file), {template: drop, src_t: drop})
        loot['random_sequence'] = 'chipped:blocks/' + bid
        wjson('data/chipped/loot_table/blocks/%s.json' % bid, loot)
    for tag in BLOCK_TAGS.get(template, []):
        out_tags['block'].setdefault(tag, []).append(full)
    if item:
        for tag in ITEM_TAGS.get(template, []):
            out_tags['item'].setdefault(tag, []).append(full)
        tabs[tab].append(full)
    else:
        itemless.append(full)
    lang['block.chipped.' + bid] = name
    if group not in groups:
        groups[group] = [group] if group.startswith('minecraft:') else []
        group_order.append(group)
    groups[group].append(full)
    report['blocks'] += 1


def item_model(bid, model_ref):
    wjson('assets/chipped/items/%s.json' % bid, {'model': {'type': 'minecraft:model', 'model': model_ref}})


# ---- Chipped: kept as it is, its models and textures copied -----------------------------------
CA = os.path.join(CHIPPED, 'assets/chipped')
copied = set()

def copy_chipped_model(ref):
    """A chipped model, its chipped parents and its chipped textures."""
    if not ref.startswith('chipped:') or ref in copied:
        return
    copied.add(ref)
    path = ref.split(':', 1)[1]
    src = os.path.join(CA, 'models', path + '.json')
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    m = load(src)
    wjson('assets/chipped/models/%s.json' % path, m)
    if 'parent' in m:
        copy_chipped_model(m['parent'])
    for tex in m.get('textures', {}).values():
        if tex.startswith('chipped:'):
            tp = tex.split(':', 1)[1]
            for ext in ('.png', '.png.mcmeta'):
                s = os.path.join(CA, 'textures', tp + ext)
                if os.path.exists(s):
                    copy(s, 'assets/chipped/textures/%s%s' % (tp, ext))
                    if ext == '.png' and BLACKSTONE.match(tp.split('/')[-1]):
                        out = os.path.join(OUT, 'assets/chipped/textures', tp + ext)
                        png.write(out, blackstone.darken(png.read(out)))
                    elif ext == '.png' and BASALT.match(tp.split('/')[-1]):
                        out = os.path.join(OUT, 'assets/chipped/textures', tp + ext)
                        png.write(out, blackstone.basalt(png.read(out)))

def models_in(state):
    found = []
    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('model'), str):
                found.append(o['model'])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(state)
    return found

def chipped_family(base):
    """(template, group) of a Chipped base."""
    m = re.fullmatch(r'(.+)_wood_glass(_pane)?', base)
    if m:
        return ('minecraft:glass_pane' if m.group(2) else 'minecraft:glass'), 'chipped:' + base
    special = {'special_lantern': 'minecraft:lantern', 'special_soul_lantern': 'minecraft:soul_lantern'}
    if base in special:
        return special[base], special[base]
    m = re.fullmatch(r'(pumpkin|carved_pumpkin|jack_o_lantern)_(end2?|nether)', base)
    if m:
        return 'minecraft:' + m.group(1), 'minecraft:' + m.group(1)
    return 'minecraft:' + base, 'minecraft:' + base

for f in sorted(os.listdir(os.path.join(CA, 'blockstates')), key=lambda f: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', f)]):
    bid = f[:-5]
    m = re.fullmatch(r'(.+)_(\d+)', bid)
    base, n = (m.group(1), m.group(2)) if m else (bid, None)
    if bid in WORKBENCHES:
        continue
    template, group = chipped_family(base)
    if not exists(template):
        left_out('chipped: no vanilla template', bid)
        continue
    state = load(os.path.join(CA, 'blockstates', f))
    im = os.path.join(CA, 'models/item', bid + '.json')
    try:
        for ref in models_in(state):
            copy_chipped_model(ref)
        if os.path.exists(im):
            copy_chipped_model('chipped:item/' + bid)
    except FileNotFoundError as e:
        left_out('chipped: missing model', '%s (%s)' % (bid, os.path.basename(str(e))))
        continue
    wjson('assets/chipped/blockstates/%s.json' % bid, state)
    item = template not in WALL
    if item:
        item_model(bid, 'chipped:item/' + bid if os.path.exists(im) else models_in(state)[0])
    title = base.replace('_', ' ').title()
    standing = None if item else 'chipped:' + bid.replace('wall_torch', 'torch')
    block(bid, template, group, '%s (Chipped %s)' % (title, n) if n else title, 'chipped', item, standing)

# ---- Chisel: each forge blockstate variant flattened into a plain model -----------------------
XA = os.path.join(CHISEL, 'assets/chisel')
# Its textures by lowercase path: its blockstates' case doesn't always match its files'.
TEXFILES = {}
for r, _, fs in os.walk(os.path.join(XA, 'textures')):
    for f in fs:
        if f.endswith('.png'):
            rel = os.path.relpath(os.path.join(r, f), os.path.join(XA, 'textures'))[:-4].replace(os.sep, '/')
            TEXFILES[rel.lower()] = os.path.join(r, f)

def tex_file(tex):
    """A Chisel texture's png, or None. `extra/` ones are sometimes at the block's top level."""
    path = tex.split(':', 1)[1].lower()
    return TEXFILES.get(path) or TEXFILES.get(path.replace('/extra/', '/'))

names = {}
for line in open(os.path.join(XA, 'lang/en_us.lang'), encoding='utf-8', errors='replace'):
    if '=' in line:
        k, v = line.rstrip('\n').split('=', 1)
        names[k] = v.strip()

# 1.12 vanilla texture names, where a Chisel variant draws one (only on its own, never layered).
V112 = {'stone_slab_top': 'smooth_stone', 'stone_slab_side': 'smooth_stone_slab_side', 'brick': 'bricks',
        'nether_brick': 'nether_bricks', 'hardened_clay': 'terracotta', 'prismarine_rough': 'prismarine',
        'sandstone_normal': 'sandstone', 'red_sandstone_normal': 'red_sandstone', 'stonebrick': 'stone_bricks',
        'quartz_block_lines_top': 'quartz_pillar_top', 'quartz_block_lines': 'quartz_pillar', 'end_bricks': 'end_stone_bricks'}
for w, m in [('oak', 'oak'), ('spruce', 'spruce'), ('birch', 'birch'), ('jungle', 'jungle'), ('acacia', 'acacia'), ('big_oak', 'dark_oak')]:
    V112['planks_' + w] = m + '_planks'
    V112['log_' + w] = m + '_log'
    V112['log_%s_top' % w] = m + '_log_top'
MODERN_SAME = {'stone', 'cobblestone', 'obsidian', 'glass', 'glowstone', 'netherrack', 'end_stone', 'dirt', 'ice',
               'iron_block', 'gold_block', 'diamond_block', 'emerald_block', 'lapis_block', 'redstone_block',
               'coal_block', 'quartz_block_top', 'quartz_block_side', 'quartz_block_bottom', 'sandstone_top',
               'sandstone_bottom', 'red_sandstone_top', 'red_sandstone_bottom', 'purpur_block', 'packed_ice',
               'lava_still', 'water_still', 'mossy_cobblestone', 'bookshelf', 'iron_bars'}

def vanilla_tex(tex):
    path = tex.split(':', 1)[-1]
    if not path.startswith('blocks/'):
        return None
    name = path[len('blocks/'):]
    m = re.fullmatch(r'glass_pane_top(?:_(\w+))?', name)
    if m:
        c = m.group(1)
        if c and c not in COLORS:
            return None
        return 'minecraft:block/' + ('%s_stained_glass_pane_top' % COLORS[c] if c else 'glass_pane_top')
    name = V112.get(name, name if name in MODERN_SAME else None)
    return 'minecraft:block/' + name if name else None

BUILTIN = {
    'block/cube_all': {d: ['#all'] for d in DIRS},
    'block/cube_column': {'up': ['#end'], 'down': ['#end'], **{d: ['#side'] for d in DIRS[2:]}},
    'block/cube_bottom_top': {'up': ['#top'], 'down': ['#bottom'], **{d: ['#side'] for d in DIRS[2:]}},
    'block/cube': {d: ['#' + d] for d in DIRS},
    'block/block': {}, 'block/block_no_ao': {},
}

def model_ref(ref, from_state):
    ns, path = ref.split(':', 1) if ':' in ref else ('minecraft', ref)
    if from_state and not path.startswith('block/'):
        path = 'block/' + path
    return ns, path

def flatten(ref, from_state=True, depth=0):
    """(textures, faces): faces maps each direction to its layers (texture refs, bottom first,
    each with whether it is tinted); None for a model that is not a full cube."""
    ns, path = model_ref(ref, from_state)
    if ns == 'minecraft' and path in BUILTIN:
        return {}, {d: [(t, False) for t in BUILTIN[path].get(d, [])] for d in DIRS}
    if ns != 'chisel' or depth > 8:
        return None
    p = os.path.join(XA, 'models', path + '.json')
    if not os.path.exists(p):
        return None
    m = load(p)
    textures, faces = {}, {d: [] for d in DIRS}
    if 'parent' in m:
        got = flatten(m['parent'], False, depth + 1)
        if got is None:
            return None
        textures, faces = got
    textures = {**textures, **m.get('textures', {})}
    if 'elements' in m:
        faces = {d: [] for d in DIRS}
        for el in m['elements']:
            full = all(abs(a - b) <= 0.11 for a, b in zip(el['from'] + el['to'], [0, 0, 0, 16, 16, 16]))
            if not full:
                return None
            for d, face in el.get('faces', {}).items():
                if 'uv' in face and face['uv'] != [0, 0, 16, 16]:
                    return None
                faces[d].append((face['texture'], 'tintindex' in face))
    return textures, faces

def resolve(tex, textures, seen=0):
    while tex.startswith('#') and seen < 10:
        tex = textures.get(tex[1:], '')
        seen += 1
    return tex if tex and not tex.startswith('#') else None

made = {}
def chisel_png(tex):
    """A Chisel texture copied in (with its animation only); its new id, or None."""
    if tex in made:
        return made[tex]
    made[tex] = None
    src = tex_file(tex)
    if src is None:
        return None
    rel = os.path.relpath(src, os.path.join(XA, 'textures'))[:-4].replace(os.sep, '/')
    to = 'block/chisel/' + re.sub(r'[^a-z0-9_./-]', '_', rel.split('/', 1)[1].lower())
    try:
        img = png.read(src)
    except Exception:
        return None
    meta = {}
    if os.path.exists(src + '.mcmeta'):
        try:
            meta = {k: v for k, v in load(src + '.mcmeta').items() if k == 'animation'}
        except Exception:
            meta = {}
    if img.h != img.w:
        if img.h % img.w:
            return None
        meta.setdefault('animation', {})
    copy(src, 'assets/chipped/textures/%s.png' % to)
    if to.startswith('block/chisel/basalt/'):
        out = os.path.join(OUT, 'assets/chipped/textures', to + '.png')
        png.write(out, blackstone.basalt(png.read(out), blackstone.CHISEL_BASALT_SRC))
    if meta:
        wjson('assets/chipped/textures/%s.png.mcmeta' % to, meta)
    made[tex] = 'chipped:' + to
    return made[tex]

def layered(texes):
    """Chisel textures put one over another, bottom first: one texture's id, or None."""
    key = tuple(texes)
    if key in made:
        return made[key]
    made[key] = None
    imgs, metas = [], []
    for t in texes:
        if not t.startswith('chisel:'):
            return None
        src = tex_file(t)
        if src is None:
            return None
        try:
            imgs.append(png.read(src))
        except Exception:
            return None
        try:
            metas.append(load(src + '.mcmeta').get('animation') if os.path.exists(src + '.mcmeta') else None)
        except Exception:
            metas.append(None)
    # From the last opaque layer up: nothing under it shows.
    start = max([i for i, im in enumerate(imgs) if im.opaque()] or [0])
    if len(imgs) - start == 1:
        made[key] = chisel_png(texes[start])
        return made[key]
    imgs, metas = imgs[start:], metas[start:]
    to = 'block/chisel/layered/' + hashlib.sha1('|'.join(texes[start:]).encode()).hexdigest()[:12]
    out = png.over(imgs)
    p = os.path.join(OUT, 'assets/chipped/textures', to + '.png')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    png.write(p, out)
    if out.h != out.w:
        anim = max(((m, im.frames()) for m, im in zip(metas, imgs)), key=lambda x: x[1])[0] or {}
        wjson('assets/chipped/textures/%s.png.mcmeta' % to, {'animation': anim})
    made[key] = 'chipped:' + to
    return made[key]

def face_tex(layers):
    if len(layers) == 1:
        t = layers[0]
        return chisel_png(t) if t.startswith('chisel:') else vanilla_tex(t)
    return layered(layers)

def cube_model(defaults, form):
    """A variant's model, flattened to one texture a face: the model json, or None."""
    kind = form.get('model', defaults.get('model', 'cube_all'))
    got = flatten(kind)
    if got is None:
        return None
    textures, faces = got
    textures = {**textures, **defaults.get('textures', {}), **form.get('textures', {})}
    out, tint = {}, False
    for d in DIRS:
        layers = []
        for ref, tinted in faces[d]:
            t = resolve(ref, textures)
            if t is None:
                return None
            layers.append(t if ':' in t else 'minecraft:' + t)
            tint |= tinted
        if not layers:
            return None
        out[d] = face_tex(layers)
        if out[d] is None:
            return None
    if len(set(out.values())) == 1 and not tint:
        return {'parent': 'minecraft:block/cube_all', 'textures': {'all': out['up']}}
    faces = {d: {'texture': '#' + d, 'cullface': d, **({'tintindex': 0} if tint else {})} for d in DIRS}
    return {'parent': 'minecraft:block/block', 'textures': {**out, 'particle': out['north']},
            'elements': [{'from': [0, 0, 0], 'to': [16, 16, 16], 'faces': faces}]}

def tex_of(defaults, form, *keys):
    textures = {**defaults.get('textures', {}), **(form or {}).get('textures', {})}
    out = []
    for k in keys:
        t = resolve('#' + k, textures)
        t = chisel_png(t) if t and t.startswith('chisel:') else (vanilla_tex(t) if t else None)
        if t is None:
            return None
        out.append(t)
    return out

def chisel_family(state, variant):
    """(template, group, kind) of a Chisel variant, or None to leave it out."""
    if state in ('auto_chisel', 'testblock', 'glasspane'):
        return None
    m = re.fullmatch(r'glass_stained/(\w+)', state)
    if m and m.group(1) in COLORS:
        t = 'minecraft:%s_stained_glass' % COLORS[m.group(1)]
        return t, t, 'cube'
    m = re.fullmatch(r'glasspane_stained/(\w+)/.+', state)
    if m and m.group(1) in COLORS:
        t = 'minecraft:%s_stained_glass_pane' % COLORS[m.group(1)]
        return t, t, 'pane'
    if state.startswith('glasspane/'):
        return 'minecraft:glass_pane', 'minecraft:glass_pane', 'pane'
    if state.startswith('ironpane/'):
        return 'minecraft:iron_bars', 'minecraft:iron_bars', 'bars'
    color = COLORS.get(variant.split('_')[-1]) or COLORS.get(variant)
    if state in ('carpet', 'wool', 'concrete_powder') and color:
        t = 'minecraft:%s_%s' % (color, state)
        return t, t, 'carpet' if state == 'carpet' else 'cube'
    m = re.fullmatch(r'concrete_(\w+)', state)
    if m and m.group(1) in COLORS:
        t = 'minecraft:%s_concrete' % COLORS[m.group(1)]
        return t, t, 'cube'
    m = re.fullmatch(r'(planks|thinwood)-(.+)', state)
    if m:
        wood = {'dark-oak': 'dark_oak', 'dark': 'dark_oak'}.get(m.group(2), m.group(2))
        t = 'minecraft:%s_planks' % wood
        return t, t, 'cube'
    if state.startswith('bookshelf_'):
        return 'minecraft:bookshelf', 'minecraft:bookshelf', 'cube'
    same = {'andesite': 'andesite', 'diorite': 'diorite', 'granite': 'granite', 'basalt': 'basalt',
            'bricks': 'bricks', 'cobblestone': 'cobblestone', 'cobblestonemossy': 'mossy_cobblestone',
            'diamond': 'diamond_block', 'emerald': 'emerald_block', 'gold': 'gold_block', 'iron': 'iron_block',
            'lapis': 'lapis_block', 'redstone': 'redstone_block', 'quartz': 'quartz_block', 'purpur': 'purpur_block',
            'prismarine': 'prismarine', 'netherbrick': 'nether_bricks', 'netherrack': 'netherrack',
            'endstone': 'end_stone', 'hardenedclay': 'terracotta', 'ice': 'ice', 'icepillar': 'packed_ice',
            'glowstone': 'glowstone', 'dirt': 'dirt', 'stone': 'stone', 'obsidian': 'obsidian', 'glass': 'glass',
            'block_coal': 'coal_block', 'sandstoneyellow': 'sandstone', 'sandstone-scribbles': 'sandstone',
            'sandstonered': 'red_sandstone', 'sandstonered-scribbles': 'red_sandstone',
            'metals/iron': 'iron_block', 'metals/gold': 'gold_block', 'metals/copper': 'waxed_copper_block'}
    if state in same:
        t = 'minecraft:' + same[state]
        return t, t, 'cube'
    own = {'leaves': 'oak_leaves', 'paper': 'white_wool', 'cloud': 'white_wool', 'block_charcoal': 'coal_block',
           'block_coal_coke': 'coal_block', 'concrete': 'light_gray_concrete'}
    t = 'minecraft:' + (own.get(state) or ('iron_block' if state.startswith('metals/') else 'stone'))
    return t, 'chipped:chisel_' + re.sub(r'[^a-z0-9_]', '_', state.lower()), 'cube'

def pane_states(bid, pane, edge):
    """A glass pane's five models and its multipart blockstate, as vanilla's glass pane."""
    for part in ('post', 'side', 'side_alt', 'noside', 'noside_alt'):
        wjson('assets/chipped/models/block/%s_%s.json' % (bid, part),
              {'parent': 'minecraft:block/template_glass_pane_' + part, 'textures': {'pane': pane, 'edge': edge}})
    m = lambda p, y=0: {'model': 'chipped:block/%s_%s' % (bid, p), **({'y': y} if y else {})}
    wjson('assets/chipped/blockstates/%s.json' % bid, {'multipart': [
        {'apply': m('post')},
        {'when': {'north': 'true'}, 'apply': m('side')}, {'when': {'east': 'true'}, 'apply': m('side', 90)},
        {'when': {'south': 'true'}, 'apply': m('side_alt')}, {'when': {'west': 'true'}, 'apply': m('side_alt', 90)},
        {'when': {'north': 'false'}, 'apply': m('noside')}, {'when': {'east': 'false'}, 'apply': m('noside_alt')},
        {'when': {'south': 'false'}, 'apply': m('noside_alt', 90)}, {'when': {'west': 'false'}, 'apply': m('noside', 270)}]})
    wjson('assets/chipped/models/item/%s.json' % bid, {'parent': 'minecraft:item/generated', 'textures': {'layer0': pane}})
    item_model(bid, 'chipped:item/' + bid)

BARS = ['bars_post_ends', 'bars_post', 'bars_cap', 'bars_cap_alt', 'bars_side', 'bars_side_alt']
for b in BARS:
    wjson('assets/chipped/models/block/chisel/%s.json' % b, load(os.path.join(XA, 'models/block', b + '.json')))

def bars_states(bid, bars, edge, side):
    for b in BARS:
        wjson('assets/chipped/models/block/%s_%s.json' % (bid, b), {'parent': 'chipped:block/chisel/' + b,
              'textures': {'bars': bars, 'edge': edge, 'side': side, 'particle': bars}})
    m = lambda p, y=0: {'model': 'chipped:block/%s_%s' % (bid, p), **({'y': y} if y else {})}
    f = 'false'
    wjson('assets/chipped/blockstates/%s.json' % bid, {'multipart': [
        {'apply': m('bars_post_ends')},
        {'when': {'north': f, 'east': f, 'south': f, 'west': f}, 'apply': m('bars_post')},
        {'when': {'north': 'true', 'east': f, 'south': f, 'west': f}, 'apply': m('bars_cap')},
        {'when': {'north': f, 'east': 'true', 'south': f, 'west': f}, 'apply': m('bars_cap', 90)},
        {'when': {'north': f, 'east': f, 'south': 'true', 'west': f}, 'apply': m('bars_cap_alt')},
        {'when': {'north': f, 'east': f, 'south': f, 'west': 'true'}, 'apply': m('bars_cap_alt', 90)},
        {'when': {'north': 'true'}, 'apply': m('bars_side')}, {'when': {'east': 'true'}, 'apply': m('bars_side', 90)},
        {'when': {'south': 'true'}, 'apply': m('bars_side_alt')}, {'when': {'west': 'true'}, 'apply': m('bars_side_alt', 90)}]})
    wjson('assets/chipped/models/item/%s.json' % bid, {'parent': 'minecraft:item/generated', 'textures': {'layer0': bars}})
    item_model(bid, 'chipped:item/' + bid)

def simple_state(bid, model):
    wjson('assets/chipped/models/block/%s.json' % bid, model)
    wjson('assets/chipped/blockstates/%s.json' % bid, {'variants': {'': {'model': 'chipped:block/' + bid}}})
    item_model(bid, 'chipped:block/' + bid)

XBS = os.path.join(XA, 'blockstates')
states = sorted(os.path.relpath(os.path.join(r, f), XBS)[:-5].replace(os.sep, '/')
                for r, _, fs in os.walk(XBS) for f in fs if f.endswith('.json'))
for state in states:
    d = load(os.path.join(XBS, state + '.json'))
    defaults = d.get('defaults', {})
    sid = re.sub(r'[^a-z0-9_]', '_', state.lower())
    top = state.split('/')[0]
    base_name = names.get('tile.chisel.%s.name' % top, top.replace('_', ' ').replace('-', ' ').title())
    variants = d.get('variants', {})
    fam = chisel_family(state, '')
    if fam and fam[2] in ('pane', 'bars'):
        # One block a blockstate file: its connections are the template's states.
        template, group, kind = fam
        bid = 'chisel_' + sid
        t = tex_of(defaults, None, 'pane', 'edge') if kind == 'pane' else tex_of(defaults, None, 'bars', 'edge', 'side')
        if t is None:
            left_out('chisel: %s textures' % kind, state)
            continue
        (pane_states if kind == 'pane' else bars_states)(bid, *t)
        sub = ' '.join(w.replace('-', ' ').title() for w in state.split('/')[1:])
        block(bid, template, group, '%s (%s)' % (base_name, sub), 'chisel')
        continue
    for variant, forms in variants.items():
        form = forms[0] if isinstance(forms, list) else forms
        if not isinstance(form, dict) or '=' in variant or variant == 'inventory':
            continue
        fam = chisel_family(state, variant)
        if fam is None:
            continue
        template, group, kind = fam
        if not exists(template):
            left_out('chisel: no vanilla template', '%s %s' % (state, variant))
            continue
        bid = 'chisel_%s_%s' % (sid, re.sub(r'[^a-z0-9_]', '_', variant.lower()))
        if kind == 'carpet':
            t = tex_of(defaults, form, 'all')
            if t is None:
                left_out('chisel: textures', '%s %s' % (state, variant))
                continue
            simple_state(bid, {'parent': 'minecraft:block/carpet', 'textures': {'wool': t[0]}})
        else:
            model = cube_model(defaults, form)
            if model is None:
                left_out('chisel: model not a plain cube, or a vanilla texture under an overlay', '%s %s' % (state, variant))
                continue
            simple_state(bid, model)
        desc = names.get('tile.chisel.%s.%s.desc.1' % (top, variant)) or variant.replace('-', ' ').replace('_', ' ').title()
        if '/' in state:
            desc = ' '.join(w.replace('-', ' ').title() for w in state.split('/')[1:]) + ', ' + desc
        block(bid, template, group, '%s (%s)' % (base_name, desc), 'chisel')

# ---- The chisel: Chisel's iron chisel, the one way between a group's blocks --------------------
copy(os.path.join(XA, 'textures/items/chisel_iron.png'), 'assets/chipped/textures/item/chisel.png')
wjson('assets/chipped/models/item/chisel.json', {'parent': 'minecraft:item/handheld', 'textures': {'layer0': 'chipped:item/chisel'}})
item_model('chisel', 'chipped:item/chisel')
wjson('data/chipped/horizon/item/chisel.json', {'template': 'minecraft:iron_sword', 'max_stack_size': 1, 'components': {
    'minecraft:item_name': {'translate': 'item.chipped.chisel'}, 'minecraft:max_damage': 500,
    'minecraft:attribute_modifiers': [
        {'type': 'minecraft:attack_damage', 'id': 'minecraft:base_attack_damage', 'amount': 2, 'operation': 'add_value', 'slot': 'mainhand'}]}})
lang['item.chipped.chisel'] = 'Chisel'
wjson('data/chipped/recipe/chisel.json', {'type': 'minecraft:crafting_shaped', 'category': 'tools',
    'key': {'I': 'minecraft:iron_ingot', 'S': 'minecraft:stick'}, 'pattern': [' I', 'S '],
    'result': {'id': 'chipped:chisel', 'count': 1}})

# ---- Block Carpentry's frames: shapes that take on the look of the block put in them -----------
# Each frame is its vanilla template's shape and behaviour (a door opens, a fence joins), drawn by
# the native part from its block entity: the frame's own texture while empty, the block's put in
# it once filled. Its block model is empty but for its breaking particles.
BC = sys.argv[5] if len(sys.argv) > 5 else None
FRAMES = [  # id, name, template, item model (parent, texture keys) or a flat item texture
    ('frameblock', 'Frame Block', 'minecraft:oak_planks', ('minecraft:block/cube_all', ['all'])),
    ('frame_slab', 'Frame Slab', 'minecraft:oak_slab', ('minecraft:block/slab', ['bottom', 'top', 'side'])),
    ('frame_stairs', 'Frame Stairs', 'minecraft:oak_stairs', ('minecraft:block/stairs', ['bottom', 'top', 'side'])),
    ('frame_slope', 'Frame Slope', 'minecraft:oak_stairs', ('minecraft:block/stairs', ['bottom', 'top', 'side'])),
    ('frame_wall', 'Frame Wall', 'minecraft:cobblestone_wall', ('minecraft:block/wall_inventory', ['wall'])),
    ('frame_fence', 'Frame Fence', 'minecraft:oak_fence', ('minecraft:block/fence_inventory', ['texture'])),
    ('frame_fence_gate', 'Frame Fence Gate', 'minecraft:oak_fence_gate', ('minecraft:block/template_fence_gate', ['texture'])),
    ('frame_door', 'Frame Door', 'minecraft:oak_door', 'item/frame_door'),
    ('frame_trapdoor', 'Frame Trapdoor', 'minecraft:oak_trapdoor', ('minecraft:block/template_trapdoor_bottom', ['texture'])),
    ('frame_pane', 'Frame Pane', 'minecraft:glass_pane', 'block/frame'),
    ('frame_carpet', 'Frame Carpet', 'minecraft:white_carpet', ('minecraft:block/carpet', ['wool'])),
    ('frame_ladder', 'Frame Ladder', 'minecraft:ladder', 'block/frame_ladder'),
    ('frame_button', 'Frame Button', 'minecraft:oak_button', ('minecraft:block/button_inventory', ['texture'])),
    ('frame_pressure_plate', 'Frame Pressure Plate', 'minecraft:oak_pressure_plate', ('minecraft:block/pressure_plate_up', ['texture'])),
    ('frame_layered_block', 'Frame Layered Block', 'minecraft:snow', ('minecraft:block/snow_height2', ['texture', 'particle'])),
    ('illusion_block', 'Illusion Block', 'minecraft:oak_planks', ('minecraft:block/cube_all', ['all'])),
    ('frame_edged_slope', 'Frame Edged Slope', 'minecraft:oak_stairs', ('minecraft:block/stairs', ['bottom', 'top', 'side'])),
    ('falling_frameblock', 'Falling Frame Block', 'minecraft:sand', ('minecraft:block/cube_all', ['all'])),
    ('frame_bed', 'Frame Bed', 'minecraft:white_bed', ('minecraft:block/slab', ['bottom', 'top', 'side'])),
    ('frame_chest', 'Frame Chest', 'minecraft:chest', ('minecraft:block/cube_all', ['all'])),
    ('frame_daylight_detector', 'Frame Daylight Detector', 'minecraft:daylight_detector',
     ('minecraft:block/slab', ['bottom', 'top', 'side'])),
]
# Each shape's illusion twin: the same frame, with the illusion's look while empty.
ILLUSIONS = ['bed', 'button', 'carpet', 'chest', 'daylight_detector', 'door', 'fence', 'fence_gate', 'ladder',
             'layered_block', 'pane', 'pressure_plate', 'slab', 'stairs', 'trapdoor', 'wall']
_by_id = {f[0]: f for f in FRAMES}
for _s in ILLUSIONS:
    _bid, _name, _template, _model = _by_id['frame_' + _s]
    if _model == 'block/frame':
        _model = 'block/illusion'
    FRAMES.append(('illusion_' + _s, _name.replace('Frame ', 'Illusion '), _template, _model))

def frame_png(path, inner):
    """A 16x16 wooden frame: a dark rim, a lighter border, a brace corner to corner, `inner` within."""
    px = bytearray()
    for y in range(16):
        for x in range(16):
            edge = min(x, y, 15 - x, 15 - y)
            if edge == 0:
                c = (0x5a, 0x43, 0x26)
            elif edge == 1:
                c = (0xa0, 0x7f, 0x4c)
            elif edge == 2:
                c = (0x7a, 0x5e, 0x36)
            elif abs(x - y) <= 1:
                c = (0x8c, 0x6c, 0x3e) if x != y else (0xa0, 0x7f, 0x4c)
            else:
                c = inner if (x + y) % 4 else tuple(max(0, v - 18) for v in inner)
            px += bytes((*c, 255))
    p = os.path.join(OUT, 'assets/chipped/textures', path + '.png')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    png.write(p, png.Image(16, 16, px))

frames = []
if BC:
    BA = os.path.join(BC, 'assets/blockcarpentry')
    frame_png('block/frame', (0xc8, 0xa8, 0x72))
    frame_png('block/illusion', (0xb4, 0x92, 0xd6))
    copy(os.path.join(BA, 'textures/block/frame_ladder.png'), 'assets/chipped/textures/block/frame_ladder.png')
    for t in ('frame_door', 'hammer'):
        copy(os.path.join(BA, 'textures/item/%s.png' % t), 'assets/chipped/textures/item/%s.png' % t)
    wjson('assets/chipped/models/block/frame_empty.json', {'textures': {'particle': 'chipped:block/frame'}})
    wjson('assets/chipped/models/block/illusion_empty.json', {'textures': {'particle': 'chipped:block/illusion'}})
    for bid, name, template, model in FRAMES:
        full = 'chipped:' + bid
        tex = 'chipped:block/' + ('illusion' if bid.startswith('illusion') else 'frame')
        props = {'occludes': False}
        if template == 'minecraft:snow':
            props['random_ticks'] = False  # no melting
        wjson('data/chipped/horizon/block/%s.json' % bid, {'template': template, 'item': True, 'properties': props})
        wjson('assets/chipped/blockstates/%s.json' % bid, {'variants': {'': {'model': 'chipped:block/%s_empty' % (
            'illusion' if bid.startswith('illusion') else 'frame')}}})
        if isinstance(model, tuple):
            parent, keys = model
            wjson('assets/chipped/models/item/%s.json' % bid, {'parent': parent, 'textures': {k: tex for k in keys}})
        else:
            wjson('assets/chipped/models/item/%s.json' % bid, {'parent': 'minecraft:item/generated',
                  'textures': {'layer0': 'chipped:' + model}})
        item_model(bid, 'chipped:item/' + bid)
        # Its own drop: a door's lower half, a bed's head, a double slab two, as vanilla's.
        src = os.path.join(VLOOT, template.split(':')[1] + '.json')
        if template in ('minecraft:oak_door', 'minecraft:oak_slab', 'minecraft:white_bed') and os.path.exists(src):
            loot = swap(load(src), {template: full})
        else:
            loot = {'type': 'minecraft:block', 'pools': [{'rolls': 1, 'entries': [{'type': 'minecraft:item', 'name': full}],
                    'conditions': [{'condition': 'minecraft:survives_explosion'}]}]}
        loot['random_sequence'] = 'chipped:blocks/' + bid
        wjson('data/chipped/loot_table/blocks/%s.json' % bid, loot)
        for tag in BLOCK_TAGS.get(template, []):
            if tag not in ('planks',):
                out_tags['block'].setdefault(tag, []).append(full)
        lang['block.chipped.' + bid] = name
        frames.append(full)
    # The hammer: empties a frame, giving the block back.
    wjson('assets/chipped/models/item/hammer.json', {'parent': 'minecraft:item/handheld', 'textures': {'layer0': 'chipped:item/hammer'}})
    item_model('hammer', 'chipped:item/hammer')
    wjson('data/chipped/horizon/item/hammer.json', {'template': 'minecraft:stick', 'max_stack_size': 1,
          'components': {'minecraft:item_name': {'translate': 'item.chipped.hammer'}}})
    lang['item.chipped.hammer'] = 'Hammer'
    # Block Carpentry's recipes, for the blocks here, in today's recipe format.
    def item_of(v):
        if isinstance(v, list):
            v = v[0]
        if isinstance(v, dict):
            v = v['item'] if 'item' in v else '#' + v['tag']
        return v.replace('blockcarpentry:', 'chipped:')
    have = {b for b, *_ in FRAMES} | {'hammer'}
    for f in sorted(os.listdir(os.path.join(BC, 'data/blockcarpentry/recipes'))):
        r = load(os.path.join(BC, 'data/blockcarpentry/recipes', f))
        out_id = r.get('result', {}).get('item', '').split(':')[-1]
        if out_id not in have or r.get('type') != 'minecraft:crafting_shaped':
            continue
        keys = {k: item_of(v) for k, v in r['key'].items()}
        if any(v.startswith('chipped:') and v.split(':')[1] not in have for v in keys.values()):
            continue
        wjson('data/chipped/recipe/%s' % f, {'type': 'minecraft:crafting_shaped', 'category': 'building',
              'pattern': r['pattern'], 'key': keys,
              'result': {'id': 'chipped:' + out_id, 'count': r['result'].get('count', 1)}})
    tabs['frames'] = frames + ['chipped:hammer']

# ---- Trash Cans' Item Trash Can (by SuperMartijn642): what goes in is gone ------------------------
TC = sys.argv[6] if len(sys.argv) > 6 else None
trash = []
if TC:
    TA = os.path.join(TC, 'assets/trashcans')
    copy(os.path.join(TA, 'textures/trash_can_items.png'), 'assets/chipped/textures/block/trash_can_items.png')
    shape = load(os.path.join(TA, 'models/trash_can.json'))
    wjson('assets/chipped/models/block/trash_can.json', shape)
    wjson('assets/chipped/models/block/item_trash_can.json',
          {'parent': 'chipped:block/trash_can', 'textures': {'all': 'chipped:block/trash_can_items'}})
    wjson('assets/chipped/blockstates/item_trash_can.json', {'variants': {'': {'model': 'chipped:block/item_trash_can'}}})
    wjson('assets/chipped/models/item/item_trash_can.json', {'parent': 'chipped:block/item_trash_can'})
    item_model('item_trash_can', 'chipped:item/item_trash_can')
    # A chest's shape and its way of holding a mod container; drawn as its own model.
    wjson('data/chipped/horizon/block/item_trash_can.json', {'template': 'minecraft:chest', 'item': True,
          'properties': {'occludes': False, 'render_shape': 'MODEL', 'sounds': 'minecraft:stone', 'requires_tool': True}})
    wjson('data/chipped/loot_table/blocks/item_trash_can.json', {'type': 'minecraft:block',
          'random_sequence': 'chipped:blocks/item_trash_can',
          'pools': [{'rolls': 1, 'entries': [{'type': 'minecraft:item', 'name': 'chipped:item_trash_can'}],
                     'conditions': [{'condition': 'minecraft:survives_explosion'}]}]})
    out_tags['block'].setdefault('mineable/pickaxe', []).append('chipped:item_trash_can')
    # Its recipe, with vanilla's stone, cobblestone and chest for the `c:` tags.
    wjson('data/chipped/recipe/item_trash_can.json', {'type': 'minecraft:crafting_shaped', 'category': 'misc',
          'pattern': ['AAA', 'BCB', 'BBB'],
          'key': {'A': 'minecraft:stone', 'B': '#minecraft:stone_crafting_materials', 'C': 'minecraft:chest'},
          'result': {'id': 'chipped:item_trash_can', 'count': 1}})
    lang['block.chipped.item_trash_can'] = 'Item Trash Can'
    trash.append('chipped:item_trash_can')

# ---- The groups, for the native part ------------------------------------------------------------
NATIVE = os.path.join(os.path.dirname(os.path.abspath(OUT)), 'native/api/src/groups.rs')
with open(NATIVE, 'w', newline='\n') as f:
    f.write('// Written by gen.py: each group, its vanilla block first (when it has one), then its variants.\n')
    f.write('pub const GROUPS: &[&[&str]] = &[\n')
    for g in group_order:
        f.write('    &[%s],\n' % ', '.join('"%s"' % i for i in groups[g]))
    f.write('];\n\n// Blocks with no item (wall torches): turned on the wall, never in the menu.\n')
    f.write('\n// Block Carpentry\'s frames, which a block put in them draws.\n')
    f.write('pub const FRAMES: &[&str] = &[%s];\n' % ', '.join('"%s"' % i for i in frames))
    f.write('pub const ITEMLESS: &[&str] = &[%s];\n' % ', '.join('"%s"' % i for i in ['minecraft:wall_torch', 'minecraft:redstone_wall_torch'] + itemless))

# ---- The mod's own files ---------------------------------------------------------------------
wjson('data/chipped/horizon/creative_tab/chipped.json', {'title': 'itemGroup.chipped.chipped', 'icon': 'chipped:chisel',
      'items': ['chipped:chisel'] + trash + tabs['chipped']})
wjson('data/chipped/horizon/creative_tab/chisel.json', {'title': 'itemGroup.chipped.chisel', 'icon': tabs['chisel'][0],
      'items': tabs['chisel']})
if frames:
    wjson('data/chipped/horizon/creative_tab/frames.json', {'title': 'itemGroup.chipped.frames', 'icon': 'chipped:frameblock',
          'items': tabs['frames']})
    lang['itemGroup.chipped.frames'] = 'Frames'
lang['itemGroup.chipped.chipped'] = 'Chipped'
lang['itemGroup.chipped.chisel'] = 'Chisel'
wjson('assets/chipped/lang/en_us.json', lang)
for kind, tags in out_tags.items():
    for tag, values in tags.items():
        wjson('data/minecraft/tags/%s/%s.json' % (kind, tag), {'values': values})
with open(os.path.join(OUT, 'horizon-mod.toml'), 'w', newline='\n') as f:
    f.write('''id = "block_variety"
name = "Block Variety"
version = "%s"
description = "Every block of Chipped (by Terrarium) and Chisel (by the Chisel team), turned into one another with the chisel, and the frames of Block Carpentry (by PianoManu), which take on the look of any block put in them, and the Item Trash Can of Trash Cans (by SuperMartijn642) (needs block_variety_native). No crafting stations: hold blocks in your offhand and use the chisel, or use it on a placed block."
authors = ["Terrarium (Chipped)", "Chisel team (Chisel)", "PianoManu (Block Carpentry)", "SuperMartijn642 (Trash Cans)", "mxpbxb (Horizon port)"]
api = "0.2"
side = "both"
capabilities = ["registries"]
''' % VERSION)
# ---- Everything moved from the namespace `chipped` to `block_variety` -----------------------------
NS = 'block_variety'
for top in ('assets', 'data'):
    src = os.path.join(OUT, top, 'chipped')
    if os.path.isdir(src):
        shutil.move(src, os.path.join(OUT, top, NS))
SWAPS = [('chipped:', NS + ':'), ('block.chipped.', 'block.%s.' % NS), ('item.chipped.', 'item.%s.' % NS),
         ('itemGroup.chipped.', 'itemGroup.%s.' % NS)]
for r, _, fs in os.walk(OUT):
    for f in fs:
        if f.endswith(('.json', '.mcmeta')):
            path = os.path.join(r, f)
            s = open(path, encoding='utf-8').read()
            n = s
            for a, b in SWAPS:
                n = n.replace(a, b)
            if n != s:
                open(path, 'w', encoding='utf-8', newline='\n').write(n)
s = open(NATIVE).read().replace('"chipped:', '"%s:' % NS)
open(NATIVE, 'w', newline='\n').write(s)
summary = {'blocks': report['blocks'], 'chipped': len(tabs['chipped']), 'chisel': len(tabs['chisel']), 'frames': len(frames),
           'itemless': len(itemless), 'groups': len(group_order), 'biggest_group': max(len(g) for g in groups.values()),
           'left_out': {k: len(v) for k, v in report['left_out'].items()}}
with open(os.path.join(os.path.dirname(os.path.abspath(OUT)), 'report.json'), 'w') as f:
    json.dump({**summary, 'left_out_list': report['left_out']}, f, indent=1)
print(json.dumps(summary, indent=1))
