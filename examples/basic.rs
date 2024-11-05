mod helpers;

use bevy::prelude::*;
use sparrow::SparrowPlugin;

//use bevy_inspector_egui::quick::WorldInspectorPlugin;
use serde::{Deserialize, Serialize};


fn main() {
    App::new()
        .add_plugins((
            DefaultPlugins,
            SparrowPlugin {

                save_path: "./art/registry.json".into(),
                component_filter: SceneFilter::default()
                    .allow::<ItemType>(),
                ..default()
            },
            //WorldInspectorPlugin::default(),
            //StateInspectorPlugin::<AppState>::default(),
            helpers::plugin,
        ))
        .add_systems(Startup, setup)
        .add_systems(Update, print_item_type_added)
        .register_type::<ItemType>()
        .run();
}

fn setup(mut commands: Commands, asset_server: Res<AssetServer>) {
    commands.spawn((
        Name::new("Scene: basic"),
        SceneRoot(asset_server.load(GltfAssetLabel::Scene(0).from_asset("scenes/Basic.gltf"))),
    ));
}


#[derive(Component, Debug, Serialize, Deserialize, Reflect)]
#[reflect(Component)]
pub enum ItemType {
    Object,
    Collection,
    Scene,
}

fn print_item_type_added(query: Query<(Entity, &ItemType, Option<&Name>), Added<ItemType>>) {
    for (entity, item_type, name) in query.iter() {
        if let Some(name) = name {
            println!("Added {:?} to {} with name {:?}", item_type, entity, name);
        } else {
            println!("Added {:?} to {:?}", item_type, entity);
        }
    }
}
