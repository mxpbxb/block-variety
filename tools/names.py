"""The chisel screen's names: every block of a group, by id, as its item is called in English.

    python3 -I tools/names.py <content mod folder> <native/api/src/groups.rs> <native/api/src/names.rs>

Block Variety's own blocks are named from the content mod's `en_us.json`; vanilla ones from their
id (`minecraft:polished_andesite` is "Polished Andesite"). gen.py runs this after it writes groups.rs.
"""
import json
import os
import re
import sys


def title(path):
    return ' '.join(w[:1].upper() + w[1:] for w in path.split('_') if w)


def main():
    content, groups, out = sys.argv[1:4]
    lang = {}
    for ns in os.listdir(os.path.join(content, 'assets')):
        p = os.path.join(content, 'assets', ns, 'lang', 'en_us.json')
        if os.path.exists(p):
            lang.update(json.load(open(p, encoding='utf-8')))
    ids = sorted(set(re.findall(r'"([a-z0-9_.-]+:[a-z0-9_./-]+)"', open(groups, encoding='utf-8').read())))
    rows = []
    for i in ids:
        ns, path = i.split(':', 1)
        name = lang.get(f'block.{ns}.{path}') or lang.get(f'item.{ns}.{path}') or title(path)
        rows.append((i, name))
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('// Written by tools/names.py: what each block of a group is called, sorted by id.\n')
        f.write('pub const NAMES: &[(&str, &str)] = &[\n')
        for i, name in rows:
            f.write('    (%s, %s),\n' % (json.dumps(i), json.dumps(name, ensure_ascii=False)))
        f.write('];\n')
    print(len(rows), 'names')


main()
