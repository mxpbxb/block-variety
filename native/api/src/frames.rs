//! Block Carpentry's frames: shapes (a slab, stairs, a door, a fence...) that take on the look of
//! the block put in them.
//!
//! - Right-click a frame with a block: the frame takes on that block's textures, face by face (a
//!   door both halves). The block is used up, except in creative.
//! - Right-click a filled frame with the hammer: it gives the block back and is empty again.
//! - Breaking a filled frame drops the block in it too.
//!
//! A frame's block model is empty; its block entity draws it, every box of its shape (its
//! template's, read from its state) with the frame's own texture while empty, else with the
//! textures of the block in it. The Illusion Block draws the block in it whole, model and all.
use horizon_client::mod_api::{
    BlockEntityDraw, BlockEntityEvent, BlockEntitySubmitEvent, BlockEntityUpdateTagEvent, BlockStateId, Compound, CubeFace,
    DestroyBlockEvent, Direction, Flow, Host, ItemStack, Tag, UseItemOnEvent,
};

use crate::groups::FRAMES;

pub const ENTITY: &str = "block_variety:frame";
pub const HAMMER: &str = "block_variety:hammer";
const MIMIC: &str = "mimic";
const EMPTY: &str = "block_variety:block/frame";
const ILLUSION: &str = "block_variety:block/illusion";
/// What a tinted face (grass, leaves) is drawn in: a temperate biome's grass.
const GRASS: u32 = 0x91BD59;
const SIDES: [Direction; 6] = [Direction::Down, Direction::Up, Direction::North, Direction::South, Direction::West, Direction::East];

pub fn is_frame(block: &str) -> bool {
    FRAMES.contains(&block)
}

fn shape(block: &str) -> &str {
    block.split(':').nth(1).unwrap_or("")
}

/// The block in a frame's compound, if any.
pub fn mimic(nbt: &Compound) -> Option<String> {
    match nbt.get(&MIMIC.into()) {
        Some(Tag::String(s)) => s.to_string().ok(),
        _ => None,
    }
}

type Box6 = [f32; 6];

/// `b` (texels, as a model element) turned about the block's upright axis from facing north to
/// `facing`, clockwise seen from above.
fn turn(b: Box6, facing: &str) -> Box6 {
    let quarter = match facing {
        "east" => 1,
        "south" => 2,
        "west" => 3,
        _ => 0,
    };
    let (mut x0, mut z0, mut x1, mut z1) = (b[0], b[2], b[3], b[5]);
    for _ in 0..quarter {
        (x0, z0, x1, z1) = (16.0 - z1, x0, 16.0 - z0, x1);
    }
    [x0.min(x1), b[1], z0.min(z1), x0.max(x1), b[4], z0.max(z1)]
}

/// The boxes a frame of shape `kind` is drawn as in state `prop` (its template's properties).
fn boxes(kind: &str, prop: &dyn Fn(&str) -> Option<String>) -> Vec<Box6> {
    let p = |k: &str| prop(k).unwrap_or_default();
    let is = |k: &str| p(k) == "true";
    let facing = p("facing");
    match kind {
        "frame_slab" => match p("type").as_str() {
            "top" => vec![[0.0, 8.0, 0.0, 16.0, 16.0, 16.0]],
            "double" => vec![[0.0, 0.0, 0.0, 16.0, 16.0, 16.0]],
            _ => vec![[0.0, 0.0, 0.0, 16.0, 8.0, 16.0]],
        },
        "frame_stairs" => {
            let top = p("half") == "top";
            let (base, step) = if top { ((8.0, 16.0), (0.0, 8.0)) } else { ((0.0, 8.0), (8.0, 16.0)) };
            // Facing north: the step is on the north side; left is west.
            let (nw, ne, sw, se) = ([0.0, 0.0, 8.0, 8.0], [8.0, 0.0, 16.0, 8.0], [0.0, 8.0, 8.0, 16.0], [8.0, 8.0, 16.0, 16.0]);
            let quarters: Vec<[f32; 4]> = match p("shape").as_str() {
                "outer_left" => vec![nw],
                "outer_right" => vec![ne],
                "inner_left" => vec![nw, ne, sw],
                "inner_right" => vec![nw, ne, se],
                _ => vec![nw, ne],
            };
            let mut out = vec![[0.0, base.0, 0.0, 16.0, base.1, 16.0]];
            out.extend(quarters.iter().map(|q| turn([q[0], step.0, q[1], q[2], step.1, q[3]], &facing)));
            out
        }
        "frame_wall" => {
            let mut out = Vec::new();
            if is("up") {
                out.push([4.0, 0.0, 4.0, 12.0, 16.0, 12.0]);
            }
            for side in ["north", "east", "south", "west"] {
                let h = match p(side).as_str() {
                    "low" => 14.0,
                    "tall" => 16.0,
                    _ => continue,
                };
                out.push(turn([5.0, 0.0, 0.0, 11.0, h, 8.0], side));
            }
            out
        }
        "frame_fence" => {
            let mut out = vec![[6.0, 0.0, 6.0, 10.0, 16.0, 10.0]];
            for side in ["north", "east", "south", "west"] {
                if is(side) {
                    out.push(turn([7.0, 12.0, 0.0, 9.0, 15.0, 6.0], side));
                    out.push(turn([7.0, 6.0, 0.0, 9.0, 9.0, 6.0], side));
                }
            }
            out
        }
        "frame_pane" => {
            let mut out = vec![[7.0, 0.0, 7.0, 9.0, 16.0, 9.0]];
            for side in ["north", "east", "south", "west"] {
                if is(side) {
                    out.push(turn([7.0, 0.0, 0.0, 9.0, 16.0, 7.0], side));
                }
            }
            out
        }
        "frame_fence_gate" => {
            let drop = if is("in_wall") { 3.0 } else { 0.0 };
            let mut out: Vec<Box6> = vec![[0.0, 5.0, 7.0, 2.0, 16.0, 9.0], [14.0, 5.0, 7.0, 16.0, 16.0, 9.0]];
            if is("open") {
                for x in [0.0, 14.0] {
                    out.push([x, 6.0, 1.0, x + 2.0, 15.0, 3.0]);
                    out.push([x, 6.0, 3.0, x + 2.0, 9.0, 7.0]);
                    out.push([x, 12.0, 3.0, x + 2.0, 15.0, 7.0]);
                }
            } else {
                out.extend([
                    [6.0, 6.0, 7.0, 8.0, 15.0, 9.0],
                    [8.0, 6.0, 7.0, 10.0, 15.0, 9.0],
                    [2.0, 6.0, 7.0, 6.0, 9.0, 9.0],
                    [2.0, 12.0, 7.0, 6.0, 15.0, 9.0],
                    [10.0, 6.0, 7.0, 14.0, 9.0, 9.0],
                    [10.0, 12.0, 7.0, 14.0, 15.0, 9.0],
                ]);
            }
            out.into_iter().map(|b| turn([b[0], b[1] - drop, b[2], b[3], b[4] - drop, b[5]], &facing)).collect()
        }
        "frame_door" => {
            // As vanilla's `DoorBlock.getShape`.
            let (s, n, w, e) = (
                [0.0, 0.0, 0.0, 16.0, 16.0, 3.0],
                [0.0, 0.0, 13.0, 16.0, 16.0, 16.0],
                [13.0, 0.0, 0.0, 16.0, 16.0, 16.0],
                [0.0, 0.0, 0.0, 3.0, 16.0, 16.0],
            );
            let closed = !is("open");
            let right = p("hinge") == "right";
            vec![match facing.as_str() {
                "south" => if closed { s } else if right { e } else { w },
                "west" => if closed { w } else if right { s } else { n },
                "north" => if closed { n } else if right { w } else { e },
                _ => if closed { e } else if right { n } else { s },
            }]
        }
        "frame_trapdoor" => vec![if is("open") {
            match facing.as_str() {
                "south" => [0.0, 0.0, 0.0, 16.0, 16.0, 3.0],
                "west" => [13.0, 0.0, 0.0, 16.0, 16.0, 16.0],
                "east" => [0.0, 0.0, 0.0, 3.0, 16.0, 16.0],
                _ => [0.0, 0.0, 13.0, 16.0, 16.0, 16.0],
            }
        } else if p("half") == "top" {
            [0.0, 13.0, 0.0, 16.0, 16.0, 16.0]
        } else {
            [0.0, 0.0, 0.0, 16.0, 3.0, 16.0]
        }],
        "frame_ladder" => vec![turn([0.0, 0.0, 15.0, 16.0, 16.0, 16.0], &facing)],
        "frame_carpet" => vec![[0.0, 0.0, 0.0, 16.0, 1.0, 16.0]],
        "frame_pressure_plate" => vec![[1.0, 0.0, 1.0, 15.0, if is("powered") { 0.5 } else { 1.0 }, 15.0]],
        "frame_layered_block" => {
            let n: f32 = p("layers").parse().unwrap_or(1.0);
            vec![[0.0, 0.0, 0.0, 16.0, 2.0 * n, 16.0]]
        }
        "frame_button" => {
            let h = if is("powered") { 1.0 } else { 2.0 };
            match p("face").as_str() {
                "floor" => vec![turn([5.0, 0.0, 6.0, 11.0, h, 10.0], &facing)],
                "ceiling" => vec![turn([5.0, 16.0 - h, 6.0, 11.0, 16.0, 10.0], &facing)],
                // On a wall facing north, the button is on the block to the south's face.
                _ => vec![turn([5.0, 6.0, 16.0 - h, 11.0, 10.0, 16.0], &facing)],
            }
        }
        _ => vec![[0.0, 0.0, 0.0, 16.0, 16.0, 16.0]],
    }
}

/// The sprite and tint of each side: the block in the frame's, else the frame's own.
fn faces(host: &dyn Host, mimic: Option<BlockStateId>, empty: &str) -> [(String, Option<u32>); 6] {
    SIDES.map(|side| match mimic.and_then(|m| host.block_face_sprite(m, side)) {
        Some((sprite, tint)) => (sprite, (tint >= 0).then_some(GRASS)),
        None => (empty.to_owned(), None),
    })
}

fn draw_box(host: &dyn Host, draw: &mut BlockEntityDraw, b: Box6, faces: &[(String, Option<u32>); 6]) {
    // The untinted faces in one box, each tinted face on its own.
    let plain: [Option<CubeFace<'_>>; 6] =
        std::array::from_fn(|i| faces[i].1.is_none().then(|| CubeFace { sprite: &faces[i].0, uv: None }));
    if plain.iter().any(Option::is_some) {
        host.draw_cube(draw, [b[0], b[1], b[2]], [b[3], b[4], b[5]], plain, 0xFF_FF_FF);
    }
    for i in 0..6 {
        if let Some(tint) = faces[i].1 {
            let one: [Option<CubeFace<'_>>; 6] =
                std::array::from_fn(|j| (j == i).then(|| CubeFace { sprite: &faces[i].0, uv: None }));
            host.draw_cube(draw, [b[0], b[1], b[2]], [b[3], b[4], b[5]], one, tint);
        }
    }
}

/// A slope: a wedge, high on its facing side, as Block Carpentry's (an upside-down one when its
/// half is the top). Each face both ways round, so the winding can't hide it.
fn draw_slope(host: &dyn Host, draw: &mut BlockEntityDraw, facing: &str, top: bool, faces: &[(String, Option<u32>); 6]) {
    let yaw = match facing {
        "west" => 90.0,
        "south" => 180.0,
        "east" => 270.0,
        _ => 0.0,
    };
    draw.push();
    draw.rotate_about([0.0, 1.0, 0.0], yaw, [0.5, 0.0, 0.5]);
    let y = |v: f32| if top { 1.0 - v } else { v };
    let (bottom, up, back, side) = (&faces[if top { 1 } else { 0 }], &faces[1], &faces[2], &faces[4]);
    let quad = |host: &dyn Host, draw: &mut BlockEntityDraw, face: &(String, Option<u32>), c: [[f32; 3]; 4]| {
        let tint = face.1.unwrap_or(0xFF_FF_FF);
        host.draw_quad(draw, &face.0, c, [0.0, 0.0, 16.0, 16.0], tint);
        host.draw_quad(draw, &face.0, [c[3], c[2], c[1], c[0]], [16.0, 0.0, 0.0, 16.0], tint);
    };
    // Under it, its back (north) and its slanted top, from the back's top edge to the front's foot.
    quad(host, draw, bottom, [[0.0, y(0.0), 1.0], [0.0, y(0.0), 0.0], [1.0, y(0.0), 0.0], [1.0, y(0.0), 1.0]]);
    quad(host, draw, back, [[1.0, y(1.0), 0.0], [1.0, y(0.0), 0.0], [0.0, y(0.0), 0.0], [0.0, y(1.0), 0.0]]);
    quad(host, draw, up, [[0.0, y(1.0), 0.0], [0.0, y(0.0), 1.0], [1.0, y(0.0), 1.0], [1.0, y(1.0), 0.0]]);
    // Its sides, triangles: a quad with two corners in one place.
    for x in [0.0, 1.0] {
        quad(host, draw, side, [[x, y(1.0), 0.0], [x, y(0.0), 0.0], [x, y(0.0), 1.0], [x, y(0.0), 1.0]]);
    }
    draw.pop();
}

pub fn block_entity(event: &BlockEntityEvent<'_>) -> Option<(String, Compound)> {
    is_frame(event.block).then(|| (ENTITY.to_owned(), Compound::default()))
}

pub fn update_tag(event: &BlockEntityUpdateTagEvent<'_>) -> Option<Compound> {
    (event.entity.id == ENTITY).then(|| event.entity.nbt.clone())
}

pub fn submit(host: &dyn Host, event: &mut BlockEntitySubmitEvent<'_>) {
    if !is_frame(event.block) {
        return;
    }
    let kind = shape(event.block);
    let state = event.state;
    let filled = mimic(&event.entity.nbt);
    let mimic_state = filled.as_deref().and_then(|m| host.default_state(m));
    let draw = &mut *event.draw;
    if kind == "illusion_block" {
        match &filled {
            Some(m) if mimic_state.is_some() => {
                host.draw_block(draw, m, &[]);
            }
            _ => draw_box(host, draw, [0.0, 0.0, 0.0, 16.0, 16.0, 16.0], &faces(host, None, ILLUSION)),
        }
        draw.keep();
        return;
    }
    let faces = faces(host, mimic_state, EMPTY);
    let prop = |k: &str| host.block_state_property(state, k).map(str::to_owned);
    if kind == "frame_slope" {
        draw_slope(host, draw, &prop("facing").unwrap_or_default(), prop("half").as_deref() == Some("top"), &faces);
    } else {
        for b in boxes(kind, &prop) {
            draw_box(host, draw, b, &faces);
        }
    }
    draw.keep();
}

/// The other half of a door at `pos` in state string `state`, if it is one.
fn other_half(pos: [i32; 3], state: &str) -> Option<[i32; 3]> {
    if !state.starts_with("block_variety:frame_door") {
        return None;
    }
    let [x, y, z] = pos;
    Some(if state.contains("half=upper") { [x, y - 1, z] } else { [x, y + 1, z] })
}

fn set_mimic(host: &mut dyn Host, pos: [i32; 3], mimic: Option<&str>) {
    host.change_mod_block_entity(pos, &mut |be| {
        match mimic {
            Some(m) => {
                be.nbt.insert(MIMIC.into(), Tag::String(m.into()));
            }
            None => {
                be.nbt.remove(&MIMIC.into());
            }
        };
    });
    host.block_entity_sync(pos);
}

/// A frame right-clicked: filled with the block in hand, or emptied with the hammer.
pub fn use_item_on(host: &mut dyn Host, event: &mut UseItemOnEvent<'_>) -> Flow {
    let Some(player) = host.acting_player() else { return Flow::Continue };
    let Some(level) = host.level(&player.dimension) else { return Flow::Continue };
    let Some(here) = host.level_block(level, event.pos) else { return Flow::Continue };
    let block = here.split('[').next().unwrap_or(&here).to_owned();
    if !is_frame(&block) {
        return Flow::Continue;
    }
    let Some(be) = host.mod_block_entity(event.pos) else { return Flow::Continue };
    let filled = mimic(&be.nbt);
    let item = event.stack.item.to_string();
    let creative = player.game_mode == 1;
    let halves: Vec<[i32; 3]> = std::iter::once(event.pos).chain(other_half(event.pos, &here)).collect();
    if item == HAMMER {
        let Some(m) = filled else { return Flow::Continue };
        for p in &halves {
            set_mimic(host, *p, None);
        }
        if !creative {
            if let Some(rest) = host.give_stack(player.uuid, ItemStack::new(m.as_str(), 1)) {
                drop_at(host, &player.dimension, event.pos, rest);
            }
        }
        play(host, &player.dimension, event.pos, "minecraft:block.wood.break");
        return Flow::Cancel;
    }
    let is_block = item != "minecraft:air" && !is_frame(&item) && host.default_state(&item).is_some();
    if filled.is_some() || !is_block {
        return Flow::Continue;
    }
    if !creative && host.take_items(&item, 1) == 0 {
        return Flow::Continue;
    }
    for p in &halves {
        set_mimic(host, *p, Some(&item));
    }
    play(host, &player.dimension, event.pos, "minecraft:block.wood.place");
    Flow::Cancel
}

/// A filled frame broken: the block in it drops too (but not in creative).
pub fn destroy_block(host: &mut dyn Host, event: &mut DestroyBlockEvent) {
    let Some(be) = host.mod_block_entity(event.pos) else { return };
    if be.id != ENTITY {
        return;
    }
    let Some(m) = mimic(&be.nbt) else { return };
    let Some(player) = host.acting_player() else { return };
    if player.game_mode == 1 {
        return;
    }
    drop_at(host, &player.dimension, event.pos, ItemStack::new(m.as_str(), 1));
}

fn drop_at(host: &mut dyn Host, dimension: &str, pos: [i32; 3], stack: ItemStack) {
    let item: Compound = [
        ("id".into(), Tag::String(stack.item.to_string().as_str().into())),
        ("count".into(), Tag::Int(stack.count as i32)),
    ]
    .into();
    let nbt: Compound = [("Item".into(), Tag::Compound(item))].into();
    let at = [f64::from(pos[0]) + 0.5, f64::from(pos[1]) + 0.5, f64::from(pos[2]) + 0.5];
    host.summon(dimension, "minecraft:item", at, nbt);
}

fn play(host: &mut dyn Host, dimension: &str, pos: [i32; 3], sound: &str) {
    if let Some(level) = host.level(dimension) {
        let at = [f64::from(pos[0]) + 0.5, f64::from(pos[1]) + 0.5, f64::from(pos[2]) + 0.5];
        host.level_play_sound(level, sound, at, 4, 1.0, 1.0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn props(list: &'static [(&'static str, &'static str)]) -> impl Fn(&str) -> Option<String> {
        move |k| list.iter().find(|(a, _)| *a == k).map(|(_, v)| (*v).to_owned())
    }

    #[test]
    fn turning_goes_round_clockwise() {
        let north = [0.0, 0.0, 0.0, 16.0, 16.0, 3.0];
        assert_eq!(turn(north, "east"), [13.0, 0.0, 0.0, 16.0, 16.0, 16.0]);
        assert_eq!(turn(north, "south"), [0.0, 0.0, 13.0, 16.0, 16.0, 16.0]);
        assert_eq!(turn(north, "west"), [0.0, 0.0, 0.0, 3.0, 16.0, 16.0]);
    }

    #[test]
    fn stairs_and_slabs_have_their_shapes() {
        let straight = boxes("frame_stairs", &props(&[("facing", "north"), ("half", "bottom"), ("shape", "straight")]));
        assert_eq!(straight, vec![[0.0, 0.0, 0.0, 16.0, 8.0, 16.0], [0.0, 8.0, 0.0, 8.0, 16.0, 8.0], [8.0, 8.0, 0.0, 16.0, 16.0, 8.0]]);
        let inner = boxes("frame_stairs", &props(&[("facing", "east"), ("half", "top"), ("shape", "inner_left")]));
        assert_eq!(inner.len(), 4);
        assert_eq!(inner[0], [0.0, 8.0, 0.0, 16.0, 16.0, 16.0]);
        assert_eq!(boxes("frame_slab", &props(&[("type", "double")])), vec![[0.0, 0.0, 0.0, 16.0, 16.0, 16.0]]);
    }

    #[test]
    fn every_frame_draws_something() {
        for f in FRAMES {
            let kind = shape(f);
            if kind == "frame_slope" || kind == "illusion_block" {
                continue;
            }
            let b = boxes(kind, &props(&[("facing", "north"), ("up", "true"), ("layers", "3"), ("face", "wall")]));
            assert!(!b.is_empty(), "{f}");
            for x in &b {
                assert!((0..3).all(|i| x[i] <= x[i + 3] && x[i] >= 0.0 && x[i + 3] <= 16.0), "{f} {x:?}");
            }
        }
    }

    #[test]
    fn a_door_is_two_halves() {
        assert_eq!(other_half([0, 5, 0], "block_variety:frame_door[half=upper,facing=north]"), Some([0, 4, 0]));
        assert_eq!(other_half([0, 5, 0], "block_variety:frame_door[half=lower]"), Some([0, 6, 0]));
        assert_eq!(other_half([0, 5, 0], "block_variety:frame_slab[type=top]"), None);
    }
}
