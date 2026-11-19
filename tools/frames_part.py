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
        return (v['item'] if isinstance(v, dict) else v).replace('blockcarpentry:', 'chipped:')
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

