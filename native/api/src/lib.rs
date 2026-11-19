//! Block Variety's native part: the chisel, the one way between a group's blocks of Chipped and
//! Chisel (there are no Chipped workbenches), and Block Carpentry's frames (`frames`).
//!
//! - Right-click with the chisel: a menu of every block of the group of what is in your other hand
//!   (pages of 45, with arrows, for a group bigger than a chest). Click one, and that whole stack
//!   becomes it.
//! - Right-click a placed block of a group with the chisel: it becomes the group's next block
//!   (sneaking, the one before), keeping its facing, connections and the rest of its state.
use std::collections::HashMap;
use std::sync::{LazyLock, Mutex};

use horizon_client::mod_api::{
    BlockEntityContainerEvent, BlockEntityEvent, BlockEntitySubmitEvent, BlockEntityTickEvent, BlockEntityTicksEvent,
    BlockEntityUpdateTagEvent, Compound, ModContainer, DestroyBlockEvent, EquipmentSlot, Flow, Hooks, Host, ItemStack, MenuClickedEvent, MenuClosedEvent, NativeServerPlayer, Text, UseItemEvent,
    UseItemOnEvent,
};

mod frames;
mod groups;

pub fn hooks() -> Box<dyn Hooks> {
    Box::new(Mod)
}

struct Mod;

const CHISEL: &str = "block_variety:chisel";
/// The menu's sound and the chisel's, on a block.
const CLICK: &str = "minecraft:ui.button.click";
const CHIP: &str = "minecraft:block.stone.hit";
const SOUND_BLOCKS: usize = 4;
/// A page of a big group: five rows of blocks, then a row with the arrows.
const PAGE: usize = 45;
const PREV: usize = 45;
const NEXT: usize = 53;
const ARROW: &str = "minecraft:arrow";

/// The group `block` is in, if any.
fn group_of(block: &str) -> Option<&'static [&'static str]> {
    groups::GROUPS.iter().copied().find(|g| g.contains(&block))
}

/// The block after `block` in its group (before it when `back`), round to the start.
fn step(block: &str, back: bool) -> Option<&'static str> {
    let g = group_of(block)?;
    let i = g.iter().position(|b| *b == block)?;
    let n = g.len();
    Some(g[if back { (i + n - 1) % n } else { (i + 1) % n }])
}

/// What the menu offers of a group: its blocks that have an item.
fn entries(group: &'static [&'static str]) -> Vec<&'static str> {
    group.iter().copied().filter(|b| !groups::ITEMLESS.contains(b)).collect()
}

fn pages(entries: &[&str]) -> usize {
    if entries.len() <= 54 { 1 } else { entries.len().div_ceil(PAGE) }
}

fn rows(entries: &[&str]) -> u8 {
    if pages(entries) > 1 { 6 } else { entries.len().div_ceil(9).clamp(1, 6) as u8 }
}

/// The block a slot of a page holds, if any.
fn at(entries: &[&'static str], page: usize, slot: usize) -> Option<&'static str> {
    if pages(entries) == 1 {
        return entries.get(slot).copied();
    }
    if slot >= PAGE {
        return None;
    }
    entries.get(page * PAGE + slot).copied()
}

fn menu_items(entries: &[&'static str], page: usize) -> Vec<Option<ItemStack>> {
    let size = rows(entries) as usize * 9;
    let mut items: Vec<Option<ItemStack>> = (0..size).map(|s| at(entries, page, s).map(|b| ItemStack::new(b, 1))).collect();
    if pages(entries) > 1 {
        if page > 0 {
            items[PREV] = Some(ItemStack::new(ARROW, 1));
        }
        if page + 1 < pages(entries) {
            items[NEXT] = Some(ItemStack::new(ARROW, 1));
        }
    }
    items
}

/// Each player's open chisel menu: its window, what it offers, and the page shown.
struct Open {
    window: i32,
    entries: Vec<&'static str>,
    page: usize,
}
static OPEN: LazyLock<Mutex<HashMap<u128, Open>>> = LazyLock::new(Default::default);

fn sound(host: &mut dyn Host, player: &NativeServerPlayer, sound: &str, at: [f64; 3]) {
    if let Some(level) = host.level(&player.dimension) {
        host.level_play_sound(level, sound, at, SOUND_BLOCKS, 0.6, 1.0);
    }
}

fn title(entries: &[&str], page: usize) -> Text {
    if pages(entries) > 1 {
        Text::literal(format!("Chisel ({}/{})", page + 1, pages(entries)))
    } else {
        Text::literal("Chisel")
    }
}

impl Mod {
    /// Hands `stack` to the player; what doesn't fit drops at their feet.
    fn hand_over(&self, host: &mut dyn Host, player: &NativeServerPlayer, stack: ItemStack) {
        use horizon_client::mod_api::{Compound, Tag};
        if let Some(rest) = host.give_stack(player.uuid, stack) {
            let item: Compound = [
                ("id".into(), Tag::String(rest.item.to_string().as_str().into())),
                ("count".into(), Tag::Int(rest.count as i32)),
            ]
            .into();
            let nbt: Compound = [("Item".into(), Tag::Compound(item))].into();
            host.summon(&player.dimension, "minecraft:item", player.position, nbt);
        }
    }
}

impl Hooks for Mod {
    fn block_entity(&self, _: &mut dyn Host, event: &mut BlockEntityEvent<'_>) -> Option<(String, Compound)> {
        frames::block_entity(event)
    }

    fn block_entity_container(&self, _: &dyn Host, event: &mut BlockEntityContainerEvent<'_>) -> Option<ModContainer> {
        frames::container(event.block)
    }

    fn block_entity_ticks(&self, _: &dyn Host, event: &mut BlockEntityTicksEvent<'_>) {
        if frames::ticks(event.block) {
            event.ticks = true;
        }
    }

    fn block_entity_tick(&self, host: &mut dyn Host, event: &mut BlockEntityTickEvent<'_>) {
        frames::tick(host, event);
    }

    fn block_entity_update_tag(&self, event: &mut BlockEntityUpdateTagEvent<'_>) -> Option<Compound> {
        frames::update_tag(event)
    }

    fn block_entity_submit(&self, host: &dyn Host, event: &mut BlockEntitySubmitEvent<'_>) {
        frames::submit(host, event);
    }

    fn destroy_block(&self, host: &mut dyn Host, event: &mut DestroyBlockEvent) -> Flow {
        frames::destroy_block(host, event);
        Flow::Continue
    }

    /// The chisel on a placed block of a group: the next block of it (sneaking, the one before).
    fn use_item_on(&self, host: &mut dyn Host, event: &mut UseItemOnEvent<'_>) -> Flow {
        if &*event.stack.item != CHISEL {
            return frames::use_item_on(host, event);
        }
        let Some(player) = host.acting_player() else { return Flow::Continue };
        let Some(level) = host.level(&player.dimension) else { return Flow::Continue };
        let Some(here) = host.level_block(level, event.pos) else { return Flow::Continue };
        let (block, state) = match here.find('[') {
            Some(i) => (here[..i].to_owned(), here[i..].to_owned()),
            None => (here.clone(), String::new()),
        };
        let Some(next) = step(&block, player.sneaking) else { return Flow::Continue };
        let [x, y, z] = event.pos;
        let run = |host: &mut dyn Host, state: &str| {
            host.run_command(&format!("execute in {} run setblock {x} {y} {z} {next}{state} replace", player.dimension))
        };
        // Its state as it is (a group's blocks share their template's), else the new block's own.
        if !run(host, &state) {
            run(host, "");
        }
        sound(host, &player, CHIP, [f64::from(x) + 0.5, f64::from(y) + 0.5, f64::from(z) + 0.5]);
        Flow::Cancel
    }

    /// The chisel, used: the menu of the group of what is in the other hand.
    fn use_item(&self, host: &mut dyn Host, event: &mut UseItemEvent<'_>) -> Flow {
        if &*event.stack.item != CHISEL {
            return Flow::Continue;
        }
        let Some(player) = host.acting_player() else { return Flow::Continue };
        let held = host.player_equipment(player.uuid, EquipmentSlot::OffHand);
        let Some(group) = held.as_ref().and_then(|s| group_of(&s.item)) else {
            host.action_bar(player.uuid, Text::literal("Chisel: hold the blocks to chisel in your other hand"));
            return Flow::Cancel;
        };
        let entries = entries(group);
        if let Some(window) = host.open_menu(player.uuid, rows(&entries), title(&entries, 0), menu_items(&entries, 0)) {
            if let Ok(mut o) = OPEN.lock() {
                o.insert(player.uuid, Open { window, entries, page: 0 });
            }
        }
        Flow::Cancel
    }

    /// A block clicked in the chisel menu: the stack in the other hand becomes it. An arrow: the
    /// page before or after.
    fn menu_clicked(&self, host: &mut dyn Host, event: &mut MenuClickedEvent) {
        let Ok(slot) = usize::try_from(event.slot) else { return };
        let (target, turn) = {
            let Ok(mut o) = OPEN.lock() else { return };
            let Some(open) = o.get_mut(&event.uuid) else { return };
            if open.window != event.window {
                return;
            }
            let n = pages(&open.entries);
            if n > 1 && slot == PREV && open.page > 0 {
                open.page -= 1;
                (None, Some((menu_items(&open.entries, open.page), open.page, n)))
            } else if n > 1 && slot == NEXT && open.page + 1 < n {
                open.page += 1;
                (None, Some((menu_items(&open.entries, open.page), open.page, n)))
            } else {
                (at(&open.entries, open.page, slot), None)
            }
        };
        let Some(player) = host.server_players().into_iter().find(|p| p.uuid == event.uuid) else { return };
        if let Some((items, _, _)) = turn {
            host.set_menu_items(player.uuid, items);
            sound(host, &player, CLICK, player.position);
            return;
        }
        let Some(target) = target else { return };
        let Some(held) = host.player_equipment(player.uuid, EquipmentSlot::OffHand) else {
            host.action_bar(player.uuid, Text::literal("Chisel: your other hand is empty"));
            return;
        };
        let same_group = group_of(&held.item).is_some_and(|g| g.contains(&target));
        if !same_group || &*held.item == target {
            return;
        }
        let taken = host.take_items(&held.item, held.count);
        if taken > 0 {
            self.hand_over(host, &player, ItemStack::new(target, taken));
            sound(host, &player, CHIP, player.position);
        }
        sound(host, &player, CLICK, player.position);
    }

    fn menu_closed(&self, _: &mut dyn Host, event: &mut MenuClosedEvent) {
        if let Ok(mut o) = OPEN.lock()
            && o.get(&event.uuid).is_some_and(|open| open.window == event.window)
        {
            o.remove(&event.uuid);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn obsidian_variants_go_round() {
        let g = group_of("minecraft:obsidian").expect("obsidian is a group");
        assert!(g.len() > 30, "{}", g.len());
        assert_eq!(g[0], "minecraft:obsidian");
        let last = g[g.len() - 1];
        assert_eq!(step(last, false), Some("minecraft:obsidian"));
        assert_eq!(step("minecraft:obsidian", true), Some(last));
        assert_eq!(step("block_variety:obsidian_1", false).map(|b| b != "block_variety:obsidian_1"), Some(true));
    }

    #[test]
    fn every_block_is_in_one_group() {
        let mut seen = std::collections::HashSet::new();
        for g in groups::GROUPS {
            assert!(g.len() > 1 || !g[0].starts_with("minecraft:"), "{g:?}");
            for b in *g {
                assert!(seen.insert(*b), "{b} is in two groups");
            }
        }
        assert!(group_of("minecraft:crying_obsidian").unwrap().iter().all(|b| b.contains("crying_obsidian")));
    }

    #[test]
    fn big_groups_page_and_every_entry_has_a_slot() {
        for g in groups::GROUPS {
            let e = entries(g);
            let items = menu_items(&e, 0);
            assert!(items.len() <= 54 && items.len() == rows(&e) as usize * 9);
            let mut found = 0;
            for page in 0..pages(&e) {
                found += (0..54).filter(|&s| at(&e, page, s).is_some()).count();
            }
            assert_eq!(found, e.len());
        }
        let stone = entries(group_of("minecraft:stone").unwrap());
        assert!(pages(&stone) > 1, "{}", stone.len());
        assert_eq!(menu_items(&stone, 0)[NEXT].as_ref().map(|s| s.item.to_string()), Some(ARROW.to_owned()));
        assert!(menu_items(&stone, 0)[PREV].is_none());
    }

    #[test]
    fn wall_torches_turn_but_are_not_offered() {
        let g = group_of("minecraft:wall_torch").expect("wall torches are a group");
        assert!(g.len() > 1);
        assert!(entries(g).is_empty());
        assert!(entries(group_of("minecraft:torch").unwrap()).len() > 1);
    }
}
