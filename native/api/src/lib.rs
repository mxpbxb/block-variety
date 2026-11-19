//! Block Variety's native part: the chisel, the one way between a group's blocks of Chipped and
//! Chisel (there are no Chipped workbenches), and Block Carpentry's frames (`frames`).
//!
//! - Right-click with the chisel: the chisel's screen (`chisel_ui`), every block of the group of
//!   what is in your other hand as icons, with a search. Click one, and that whole stack becomes
//!   it; right-click, and one block does.
//! - Right-click a placed block of a group with the chisel: it becomes the group's next block
//!   (sneaking, the one before), keeping its facing, connections and the rest of its state.
use horizon_client::mod_api::{
    BlockEntityContainerEvent, BlockEntityEvent, BlockEntitySubmitEvent, BlockEntityTickEvent, BlockEntityTicksEvent,
    BlockEntityUpdateTagEvent, ClientTickPostEvent, Compound, DestroyBlockEvent, EquipmentSlot, Flow, Hooks, Host,
    ItemStack, ModContainer, NativeServerPlayer, NetFromClientEvent, NetFromServerEvent, ScreenCharTypedPreEvent,
    ScreenKeyPressedPreEvent, ScreenMouseButtonPressedPreEvent, ScreenMouseButtonReleasedPreEvent,
    ScreenMouseDraggedPreEvent, ScreenMouseScrolledPreEvent, ScreenRenderPostEvent, Text, UseItemEvent, UseItemOnEvent,
};

mod chisel_ui;
mod frames;
mod groups;
mod names;
mod trash;

use chisel_ui::{MOD_ID, UI, Ui};

pub fn hooks() -> Box<dyn Hooks> {
    Box::new(Mod)
}

struct Mod;

const CHISEL: &str = "block_variety:chisel";
/// The screen's sound and the chisel's, on a block.
const CLICK: &str = "minecraft:ui.button.click";
const CHIP: &str = "minecraft:block.stone.hit";
const SOUND_BLOCKS: usize = 4;
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

fn sound(host: &mut dyn Host, player: &NativeServerPlayer, sound: &str, at: [f64; 3]) {
    if let Some(level) = host.level(&player.dimension) {
        host.level_play_sound(level, sound, at, SOUND_BLOCKS, 0.6, 1.0);
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

    /// Tells the player's client what is in their other hand, for the chisel's screen (nothing
    /// to chisel closes it).
    fn show(&self, host: &mut dyn Host, player: u128) {
        let held = host.player_equipment(player, EquipmentSlot::OffHand);
        let (id, count) = match held.as_ref().filter(|s| group_of(&s.item).is_some()) {
            Some(s) => (s.item.to_string(), s.count),
            None => (String::new(), 0),
        };
        let _ = host.net_send_to_player(player, chisel_ui::OPEN, &chisel_ui::encode_open(&id, count));
    }

    /// What the screen chose: the stack in the other hand (or one of it) becomes `target`, a block
    /// of the same group.
    fn chisel(&self, host: &mut dyn Host, player: &NativeServerPlayer, target: &str, whole: bool) {
        let Some(held) = host.player_equipment(player.uuid, EquipmentSlot::OffHand) else { return };
        let Some(target) = group_of(&held.item).and_then(|g| g.iter().copied().find(|b| *b == target)) else { return };
        if groups::ITEMLESS.contains(&target) || &*held.item == target {
            return;
        }
        let one = !whole && held.count > 1;
        let into = if one {
            let mut rest = held.clone();
            rest.count -= 1;
            rest
        } else {
            ItemStack::new(target, held.count)
        };
        let set = host
            .entity(player.entity_id as u32)
            .and_then(|e| host.living(e))
            .is_some_and(|l| l.set_equipment(host, EquipmentSlot::OffHand, Some(into.clone())))
            && host.player_equipment(player.uuid, EquipmentSlot::OffHand) == Some(into);
        if set {
            if one {
                self.hand_over(host, player, ItemStack::new(target, 1));
            }
        } else {
            // The hand couldn't be set: take the blocks from the inventory and give the new ones.
            let taken = host.take_items(&held.item, if one { 1 } else { held.count });
            if taken == 0 {
                return;
            }
            self.hand_over(host, player, ItemStack::new(target, taken));
        }
        sound(host, player, CHIP, player.position);
    }
}

// ---- The client's side ----

/// Whether the screen open is the chisel's.
fn ours(host: &dyn Host, id: &str) -> bool {
    id == "mod" && host.mod_screen() == Some(MOD_ID)
}

fn blink() -> bool {
    let ms = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_or(0, |d| d.as_millis());
    ms / 500 % 2 == 0
}

impl Hooks for Mod {
    fn block_entity(&self, _: &mut dyn Host, event: &mut BlockEntityEvent<'_>) -> Option<(String, Compound)> {
        frames::block_entity(event).or_else(|| trash::block_entity(event))
    }

    fn block_entity_container(&self, _: &dyn Host, event: &mut BlockEntityContainerEvent<'_>) -> Option<ModContainer> {
        frames::container(event.block).or_else(|| trash::container(event.block))
    }

    fn block_entity_ticks(&self, _: &dyn Host, event: &mut BlockEntityTicksEvent<'_>) {
        if frames::ticks(event.block) || trash::ticks(event.block) {
            event.ticks = true;
        }
    }

    fn block_entity_tick(&self, host: &mut dyn Host, event: &mut BlockEntityTickEvent<'_>) {
        frames::tick(host, event);
        trash::tick(event);
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

    /// The chisel, used: its screen, for the group of what is in the other hand.
    fn use_item(&self, host: &mut dyn Host, event: &mut UseItemEvent<'_>) -> Flow {
        if &*event.stack.item != CHISEL {
            return Flow::Continue;
        }
        let Some(player) = host.acting_player() else { return Flow::Continue };
        let held = host.player_equipment(player.uuid, EquipmentSlot::OffHand);
        if held.as_ref().and_then(|s| group_of(&s.item)).is_none_or(|g| entries(g).len() < 2) {
            host.action_bar(player.uuid, Text::literal("Chisel: hold the blocks to chisel in your other hand"));
            return Flow::Cancel;
        }
        self.show(host, player.uuid);
        sound(host, &player, CLICK, player.position);
        Flow::Cancel
    }

    /// A block chosen on the chisel's screen; then the screen is told what is held now.
    fn net_from_client(&self, host: &mut dyn Host, event: &mut NetFromClientEvent<'_>) {
        if event.channel != chisel_ui::CHOOSE {
            return;
        }
        let Some((target, whole)) = chisel_ui::decode_choose(event.data) else { return };
        let Some(player) = host.server_players().into_iter().find(|p| p.uuid == event.player) else { return };
        self.chisel(host, &player, &target, whole);
        self.show(host, player.uuid);
    }

    /// The server says what is held: the chisel's screen opens on it, or shows it now.
    fn net_from_server(&self, host: &mut dyn Host, event: &mut NetFromServerEvent<'_>) {
        if event.channel != chisel_ui::OPEN {
            return;
        }
        let Some((held, count)) = chisel_ui::decode_open(event.data) else { return };
        if !chisel_ui::set_held(held, count) {
            if host.mod_screen() == Some(MOD_ID) {
                host.mod_screen_close(MOD_ID);
            }
            return;
        }
        if host.mod_screen() != Some(MOD_ID)
            && !host.mod_screen_open(MOD_ID)
            && let Ok(mut ui) = UI.lock()
        {
            *ui = Ui::Closed;
        }
    }

    /// Sends what the screen chose, and forgets a screen Escape closed.
    fn client_tick_post(&self, host: &mut dyn Host, _: &mut ClientTickPostEvent) {
        let out = chisel_ui::OUTBOX.lock().map(|mut o| std::mem::take(&mut *o)).unwrap_or_default();
        for (channel, data) in out {
            let _ = host.net_send_to_server(channel, &data);
        }
        if host.mod_screen() != Some(MOD_ID)
            && let Ok(mut ui) = UI.lock()
        {
            *ui = Ui::Closed;
        }
    }

    fn screen_render_post(&self, host: &dyn Host, event: &mut ScreenRenderPostEvent<'_>) {
        if ours(host, event.screen.id) {
            chisel_ui::draw(host, event.batch, event.screen.rect, event.screen.mouse, blink());
        }
    }

    fn screen_char_typed_pre(&self, host: &dyn Host, event: &mut ScreenCharTypedPreEvent<'_>) -> Flow {
        if !ours(host, event.screen.id) {
            return Flow::Continue;
        }
        chisel_ui::typed(event.c);
        Flow::Cancel
    }

    fn screen_key_pressed_pre(&self, host: &dyn Host, event: &mut ScreenKeyPressedPreEvent<'_>) -> Flow {
        if !ours(host, event.screen.id) || event.key == "key.keyboard.escape" {
            return Flow::Continue;
        }
        chisel_ui::key(event.key);
        Flow::Cancel
    }

    fn screen_mouse_button_pressed_pre(&self, host: &dyn Host, event: &mut ScreenMouseButtonPressedPreEvent<'_>) -> Flow {
        if !ours(host, event.screen.id) {
            return Flow::Continue;
        }
        chisel_ui::pressed(event.screen.rect, event.screen.mouse, event.button);
        Flow::Cancel
    }

    fn screen_mouse_button_released_pre(&self, host: &dyn Host, event: &mut ScreenMouseButtonReleasedPreEvent<'_>) -> Flow {
        if !ours(host, event.screen.id) {
            return Flow::Continue;
        }
        chisel_ui::released();
        Flow::Cancel
    }

    fn screen_mouse_dragged_pre(&self, host: &dyn Host, event: &mut ScreenMouseDraggedPreEvent<'_>) -> Flow {
        if !ours(host, event.screen.id) {
            return Flow::Continue;
        }
        chisel_ui::dragged(event.screen.rect, event.screen.mouse);
        Flow::Cancel
    }

    fn screen_mouse_scrolled_pre(&self, host: &dyn Host, event: &mut ScreenMouseScrolledPreEvent<'_>) -> Flow {
        if !ours(host, event.screen.id) {
            return Flow::Continue;
        }
        chisel_ui::scrolled(event.screen.rect, event.scroll[1]);
        Flow::Cancel
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
    fn wall_torches_turn_but_are_not_offered() {
        let g = group_of("minecraft:wall_torch").expect("wall torches are a group");
        assert!(g.len() > 1);
        assert!(entries(g).is_empty());
        assert!(entries(group_of("minecraft:torch").unwrap()).len() > 1);
    }
}
