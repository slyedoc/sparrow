mod loading;
mod camera_controller;

use bevy::prelude::*;
use bevy_inspector_egui::bevy_egui::EguiContext;

pub fn plugin(app: &mut App) {
    app.add_plugins((
    camera_controller::plugin,
    loading::plugin,
));
}

fn egui_mouse_free(egui_contexts: Query<&EguiContext>) -> bool {
    egui_contexts
        .iter()
        .all(|ctx| !ctx.get().wants_pointer_input())
}
