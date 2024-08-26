
mod helpers;

use bevy::prelude::*;
use sparrow::SparrowPlugin; 

use bevy_asset_loader::prelude::*;
use bevy_inspector_egui::quick::WorldInspectorPlugin;
use sickle_ui::{prelude::*, SickleUiPlugin};
use serde::{Deserialize, Serialize};

#[derive(AssetCollection, Resource)]
pub struct GameAssets {
    #[asset(path = "scenes/Basic.gltf#Scene0")]
    pub basic: Handle<Scene>,
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
        .add_systems(Update, print_item_type_added)
        .register_type::<ItemType>()
        .run();
}

fn setup(mut commands: Commands, game_assets: Res<GameAssets>) {
    commands.spawn((
        Name::new("Scene: basic"),
        SceneBundle {
            scene: game_assets.basic.clone(),
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

#[derive(Component, Debug, Serialize, Deserialize, Reflect)]
#[reflect(Component)]
pub enum ItemType {
    Object,   
    Collection,
    Scene,
}

fn print_item_type_added(
    query: Query<(Entity, &ItemType, Option<&Name>), Added<ItemType>>,
) {
    for (entity, item_type, name) in query.iter() {
        if let Some(name) = name {
            println!(
                "Added {:?} to {} with name {:?}",
                item_type, entity, name
            );
        } else {
            println!("Added {:?} to {:?}", item_type, entity);
        }
    }
}