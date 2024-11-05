use bevy::{asset::LoadState, prelude::*};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

mod registry;
pub use registry::*;

mod process_gltfs;
use process_gltfs::*;

mod extras;
pub use extras::*;

#[cfg(feature = "animation")]
mod animations;

mod fake_entity;
mod ronstring_to_reflect_component;

pub mod prelude {
    #[cfg(feature = "animation")]
    pub use crate::animations::*;
    pub use crate::{
        extras::*, SceneLoaded, SceneLoading, SparrowConfig, SparrowPlugin, SparrowSet,
    };
}

#[derive(Debug, Clone)]
/// Plugin for gltf blueprints
pub struct SparrowPlugin {
    /// Path to save the registry schema, relative to the assets folder
    pub save_path: PathBuf,
    pub component_filter: SceneFilter,
    pub ignore: Vec<String>,
}

impl Default for SparrowPlugin {
    fn default() -> Self {
        Self {
            save_path: PathBuf::from("../registry.json"),
            component_filter: SceneFilter::default(),
            ignore: Vec::new(),
        }
    }
}

#[derive(Resource)]
pub struct SparrowConfig {
    pub save_path: PathBuf,
    pub component_filter: SceneFilter,
    pub ignore: Vec<String>,
}

// Scenes are loaded in custom schedual after update and before post update,
// and we want global transforms to be propagated before we add component like clidider from mesh
// so we run after TransformSystem::TransformPropagate
#[derive(SystemSet, Debug, Hash, PartialEq, Eq, Clone)]
pub enum SparrowSet {
    Extras, // for adding components from gltf extras
    Post,   // for any post processing , don't use ourselves
}

impl Plugin for SparrowPlugin {
    fn build(&self, app: &mut App) {
        app.add_plugins((
            extras::plugin,
            #[cfg(feature = "animation")]
            animations::plugin,
        ))
        .insert_resource(SparrowConfig {
            save_path: self.save_path.clone(),
            component_filter: self.component_filter.clone(),
            ignore: self.ignore.clone(),
        })
        .configure_sets(
            PostUpdate,
            (SparrowSet::Extras, SparrowSet::Post)
                .chain()
                .after(TransformSystem::TransformPropagate),
        );

        #[cfg(feature = "registry")]
        {
            // hack to get the asset path, could be removed?

            let asset_plugins: Vec<&AssetPlugin> = app.get_added_plugins();
            let asset_plugin = asset_plugins
                .into_iter()
                .next()
                .expect("Asset plugin required.");
            let path_str = asset_plugin.file_path.clone();
            let path = PathBuf::from(path_str);

            app.insert_resource(AssetRoot(path))
                .add_systems(Startup, export_types);
        }

        // handle loading of gltf files, scene and blueprints from path
        app.register_type::<GltfProcessed>()
            .register_type::<Blueprint>()
            .add_systems(
                PostUpdate,
                (add_components_from_gltf_extras).in_set(SparrowSet::Extras),
            )
            .add_systems(
                PostUpdate,
                (spawn_blueprints, check_scene_loading).in_set(SparrowSet::Post),
            );

        #[cfg(feature = "reload")]
        app.add_systems(Update, reload_scene_on_asset_change);
        // .add_systems(
        //     PostUpdate,
        //     (
        //         #[cfg(feature = "flatten_scene")]
        //         scene_extras_and_flatten,
        //         #[cfg(not(feature = "flatten_scene"))]
        //         gltf_extras::<bevy::gltf::GltfSceneExtras>,
        //         apply_deferred,
        //         gltf_extras::<bevy::gltf::GltfExtras>,
        //         gltf_extras::<bevy::gltf::GltfMaterialExtras>,
        //     )
        //         .chain()
        //         .in_set(SceneSet::Extras),
        // );
    }
}

#[derive(Component, Deref, DerefMut, Debug, Clone, Default, Reflect, Serialize, Deserialize)]
#[reflect(Component, Serialize, Deserialize)]
pub struct Blueprint(pub String);

#[derive(Component)]
pub struct SceneLoading(pub Handle<Gltf>);

#[derive(Component, Debug, Clone)]
pub struct SceneLoaded(pub Handle<Gltf>);

fn spawn_blueprints(
    mut commands: Commands,
    query: Query<(Entity, &Blueprint), Added<Blueprint>>,
    assets_gltf: Res<Assets<Gltf>>,
    asset_server: Res<AssetServer>,
) {
    for (e, blueprint) in query.iter() {
        let gltf: Handle<Gltf> = asset_server.load(&blueprint.0);

        if let Some(LoadState::Loaded) = asset_server.get_load_state(&gltf) {
            debug!("Spawning blueprint already loaded: {:?}", blueprint.0);
            let scene = first_scene(&gltf, &assets_gltf);
            commands.entity(e).insert((SceneLoaded(gltf), SceneRoot(scene)));
        } else {
            debug!("Spawning blueprint once loaded: {:?}", blueprint.0);
            commands.entity(e).insert(SceneLoading(gltf));
        }
    }
}

fn check_scene_loading(
    mut commands: Commands,
    query: Query<(Entity, Option<&Name>, &SceneLoading)>,
    gltfs: Res<Assets<Gltf>>,
    asset_server: Res<AssetServer>,
) {
    for (e, name, gltf) in query.iter() {
        if let Some(LoadState::Loaded) = asset_server.get_load_state(&gltf.0) {
            let scene = first_scene(&gltf.0, &gltfs);
            debug!("Spawning blueprint after it loaded: {:?}", name);
            commands
                .entity(e)
                .remove::<SceneLoading>()
                .insert((SceneLoaded(gltf.0.clone()), SceneRoot(scene)));
        }
    }
}

#[cfg(feature = "reload")]
fn reload_scene_on_asset_change(
    mut commands: Commands,
    mut asset_event: EventReader<AssetEvent<Scene>>,
    scenes: Query<(Entity, &SceneRoot, Option<&Name>)>,
) {
    for event in asset_event.read() {
        match event {
            AssetEvent::Modified { id } => {
                for (e, scene, name) in &mut scenes.iter() {
                    if scene.id() != *id {
                        continue;
                    }
                    info!("Reloading: {:?}", name);

                    // remove the old scene
                    commands
                        .entity(e)
                        .despawn_descendants()
                        // add the new scene
                        .insert(scene.clone());
                }
            }
            _ => {}
        }
    }
}

fn first_scene(gltf_handle: &Handle<Gltf>, assets_gltf: &Res<Assets<Gltf>>) -> Handle<Scene> {
    let gltf = assets_gltf
        .get(gltf_handle)
        .unwrap_or_else(|| panic!("gltf file {:?} should have been loaded", gltf_handle));

    // WARNING we work under the assumtion that there is ONLY ONE named scene, and
    // that the first one is the right one
    let main_scene_name = gltf
        .named_scenes
        .keys()
        .next()
        .expect("there should be at least one named scene in the gltf file to spawn");
    gltf.named_scenes[main_scene_name].clone()
}
