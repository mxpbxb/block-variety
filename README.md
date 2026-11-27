# Block Variety

A [Horizon](https://playhorizon.dev) port of three decorative block mods in one, and a trash can:

- **Chipped** (by Terrarium), from its 1.18.1 jar: its 2,487 block variants, every block but its
  workbenches; and from its 1.18.2 jar, 2,720 more for the vanilla blocks 1.18.1 gave none to.
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
torches, lanterns and the rest), or a Chisel block of its own. [Structure Add-on](https://github.com/mxpbxb/structure-addon)'s
limestone and marble head Chisel's limestone and marble groups, and its andesite and basalt are in
vanilla's, so they turn into those blocks too.

## Crafting

The groups with no vanilla block (Chisel's ancient and arcane stone, laboratory, factory, brownstone,
tyrian, temple, voidstone, its metals and the rest, and Chipped's wood glass) each have a crafting
recipe from vanilla things, mostly a ring of eight of a block around one thing that marks it (factory:
stone around an iron ingot; laboratory: stone around quartz; brownstone: sandstone around brown dye).
Coke is a coal block smelted. Once one block is made, the chisel gives the rest of its group.

## No stonecutter recipes

0.5.0 cut every block of a group in the stonecutter from any block of its group. 0.5.1 removes those
recipes: they took a lot of memory (a group of n blocks made n recipes of n items each, 343,026
entries in all, sent to every player). Use the chisel.

## Shiny blocks and raw blocks

Chipped's newer textures are airbrushed and glossy: smooth gradients, white or pink diagonal shine
streaks, and little pixel noise. Next to Chisel's blocks and the old Minecraft textures they look
out of place. `tools/cull.py` holds the rule and the list (`report.json` shows each block left out
and why):

- A group with only a few such blocks loses them: 7 glowstone and 6 shroomlight.
- In a group drawn that way all through (diamond, emerald, gold, iron and netherite blocks), the
  shine is painted out instead (`deshine`). Each pixel only a little lighter or darker than the
  block's body colour, and not part of a straight engraved line, takes the body colour. The
  engraving and strong dark lines stay. Each of these groups' 12th block was only a shine and a
  frame, so it is cut.
  Their 11th block's corner nails, uneven in Chipped, are redrawn as one 2x2 rivet in each corner
  (`nails`).
- Raw iron, raw gold and raw copper blocks keep 30 of Chipped 1.18.2's 61 patterns. The 31 cut are
  the ones most like a pattern that stays.
- Groups few build with are cut down the same way, the creeper-face stamp first: lodestone to 4
  (a medallion, a frame, bricks and tiles), ancient debris, magma block, ice, packed ice and blue
  ice by half, coal, redstone and lapis blocks by a quarter, and the small plants and odd blocks
  (nether sprouts, crimson and warped roots and fungi, lily pads, cobwebs, vines, sponge, melon)
  by three quarters.
- The creeper-face stamp is cut from every group that has it (23 groups' 23rd block, and bricks' 84th).

## Chipped 1.18.2

Chipped 1.18.2's blocks come in only for the vanilla blocks that Chipped 1.18.1 gave none to: iron
and the other metal blocks, raw ore blocks, the logs, stems, leaves, doors, trapdoors, ladders,
bookshelves, glazed terracotta, deepslate, tuff, calcite, amethyst and the rest. A group with 1.18.1
blocks (stone, blackstone and so on) gets none of 1.18.2's. Their textures are Chipped 1.18.2's
recoloured to Programmer Art Continuation (`jars/pa1182`, by its `Recolor.java`: each family's
lightness and colour matched to the pack's textures in CIELAB, then snapped to the pack's palette).

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
python3 -I gen.py <Chipped 1.18.1 jar> <Chisel jar> <vanilla 26.3 data> content <Block Carpentry jar> <Trash Cans jar> <Chipped 1.18.2 jar> jars/pa1182
cd content && cargo horizon-mod build
cd ../native-sdk && cargo horizon-mod build
```

It also writes `native-sdk/src/groups.rs` (the groups, frames and itemless blocks) and `names.rs`.
`native-sdk/` is the native part as a Horizon SDK project (its `.horizon/sdk` not in the
repository); `native/` is the older mixin crate it was ported from. `tools/png.py`
reads and writes the PNGs it flattens Chisel's layered textures with.

## Credits

- Chipped: Terrarium
- Chisel: the Chisel team
- Block Carpentry: PianoManu
- Trash Cans: SuperMartijn642
- Horizon port: mxpbxb
