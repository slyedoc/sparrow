
mod helpers;

use bevy::prelude::*;
use bevy_asset_loader::prelude::*;
use bevy_inspector_egui::quick::WorldInspectorPlugin;
use sickle_ui::{prelude::*, SickleUiPlugin};
use sparrow::SparrowPlugin; 

#[derive(AssetCollection, Resource)]
pub struct GameAssets {
    #[asset(path = "scenes/basic.gltf#Scene0")]
    pub part2: Handle<Scene>,
}

#[derive(States, Debug, Default, Clone, Hash, Eq, PartialEq, Reflect)]
pub enum AppState {
    #[default]
    Loading,
    Playing,
}


fn main() {
    App::new()
        .add_plugins((
            DefaultPlugins,
            SparrowPlugin::default(),
            WorldInspectorPlugin::default(),
            //StateInspectorPlugin::<AppState>::default(),
            SickleUiPlugin,
            helpers::plugin,
        ))
        .init_state::<AppState>()
        .enable_state_scoped_entities::<AppState>()
        .add_systems(PreStartup, pre_setup)
        .add_systems(OnEnter(AppState::Playing), setup)
        .add_systems(PostUpdate, todo_on_scene_spawn)
        .run();
}

fn setup(mut commands: Commands, game_assets: Res<GameAssets>) {
    commands.spawn((
        Name::new("Scene: part2"),
        SceneBundle {
            scene: game_assets.part2.clone(),
            ..default()
        },
    ));
}

fn todo_on_scene_spawn() {}


#[derive(Component)]
pub struct UiMainRootNode;

fn pre_setup(mut commands: Commands) {

    // The root of the UI, all UI elements will be children of this
    commands
        .ui_builder(UiRoot)
        .container(
            (
                NodeBundle {
                    style: Style {
                        width: Val::Percent(100.0),
                        height: Val::Percent(100.0),
                        flex_direction: FlexDirection::Column,
                        justify_content: JustifyContent::SpaceBetween,
                        ..default()
                    },
                    ..default()
                },
            ),
            |container| {
                container.spawn((
                    NodeBundle {
                        style: Style {
                            width: Val::Percent(100.0),
                            height: Val::Percent(100.0),
                            flex_direction: FlexDirection::Row,
                            justify_content: JustifyContent::SpaceBetween,
                            ..default()
                        },
                        ..default()
                    },
                    UiMainRootNode,
                ));
            },
        )
        .insert(Name::new("UI Root"));
}
