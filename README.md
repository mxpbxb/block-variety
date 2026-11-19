# Block Variety

A [Horizon](https://playhorizon.dev) port of three decorative block mods in one, and a trash can:

- **Chipped** (by Terrarium), from its 1.18.1 jar: its 2,487 block variants, every block but its workbenches.
- **Chisel** (by the Chisel team): 2,371 of its variants, each a block of its own.
- **Block Carpentry** (by PianoManu): 37 frames that take on the look of any block put in them.
- **Trash Cans** (by SuperMartijn642): its Item Trash Can.

Ported with the original creators' permission. Their art and designs are theirs.

## The chisel

There are no Chipped workbenches. The chisel does all of it:

- **Right-click with the chisel**, holding blocks in your other hand: the chisel's screen, every
  block of their group as icons in a grid that scrolls, with a search (type part of a name). Click
  one and the whole stack becomes it; right-click and one block does. It stays open, so you can go
  on, and Enter takes the first block the search shows.
- **Right-click a placed block** with the chisel: it becomes the next block of its group (sneaking,
  the one before), keeping its facing, connections and the rest of its state.

A group is a vanilla block's family, the vanilla block first (stone, obsidian, the planks, glass,
torches, lanterns and the rest), or a Chisel block of its own.

Chipped's blackstone and gilded blackstone are darkened into Programmer Art Continuation's
blackstone (`tools/blackstone.py`): each pixel's lightness mapped onto the pack's, in its neutral
grey, the gold left as it is. Chipped's and Chisel's basalt are brought onto the pack's basalt the
same way.

Each block behaves as its vanilla template does: it drops itself where that drops itself, and takes
the same mining tool and tool level.

## Frames

The Frame Block, Falling Frame Block, Slab, Stairs, Slope, Edged Slope (a slope that turns corners,
as stairs do), Wall, Fence, Fence Gate, Door, Trapdoor, Pane, Carpet, Ladder, Button, Pressure
Plate, Layered Block, Bed, Chest (a chest's 27 slots) and Daylight Detector (powered by the sky, as
vanilla's), and the Illusion Block. Each shape but the slopes and the Falling Frame Block has an
illusion twin too, the same frame with the illusion's look while empty. Right-click a frame with a block
to fill it with that block's look (a door or a bed takes it on both halves); right-click it with the hammer
to take the block back out. A broken frame drops the block put in it. The frames keep their
template's shape and behaviour: a door opens, a fence joins. The recipes are Block Carpentry's.

## Item Trash Can

A row of nine slots: whatever goes in, from your hand or a hopper, is gone the next tick. It takes
nothing out. Trash Cans' recipe, with stone, cobblestone (or blackstone or cobbled deepslate) and a
chest. Its filter, its list of deleted items and the other cans are left out.

## Left out

403 of Chisel's variants: 274 whose textures are not in its jar (Emboss, Indent, Large Ornate and
Marker variants, thin wood, uncoloured concrete, leaves, mazestone and others), 128 drawn over
vanilla textures (lavastone, waterstone, bookshelves), and the futura circuitplate. `report.json`
lists them.

## Two parts

Install both:

| Part | Id | What |
|---|---|---|
| Assets (`.hmod`) | `block_variety` | The blocks, items, models, textures, loot, tags and recipes |
| Native (`.hnmod`) | `block_variety_native` | The chisel, the frames and the trash can |

## Building

`gen.py` writes the content mod from the unpacked original jars and vanilla 26.3's data:

```
python3 -I gen.py <Chipped 1.18.1 jar> <Chisel jar> <vanilla 26.3 data> content <Block Carpentry jar> <Trash Cans jar>
cd content && cargo horizon-mod build
python3 -I tools/packnative.py native block_variety_native.hnmod
```

It also writes `native/api/src/groups.rs` (the groups, frames and itemless blocks). `tools/png.py`
reads and writes the PNGs it flattens Chisel's layered textures with.

## Credits

- Chipped: Terrarium
- Chisel: the Chisel team
- Block Carpentry: PianoManu
- Trash Cans: SuperMartijn642
- Horizon port: mxpbxb
