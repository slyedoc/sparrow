use bevy::prelude::*;
use std::path::PathBuf;

mod registry;
pub use registry::*;

mod process_gltfs;
use process_gltfs::*;

mod extra_settings;
pub use extra_settings::*;

mod fake_entity;

mod ronstring_to_reflect_component;



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
            save_path: PathBuf::from("../art/registry.json"),
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

/// systemset to order your systems after the component injection when needed
#[derive(SystemSet, Debug, Hash, PartialEq, Eq, Clone)]
pub enum SceneSet {
    Extras,
    Post,
}

impl Plugin for SparrowPlugin {
    fn build(&self, app: &mut App) {
        app
        .add_plugins(extra_settings::plugin)
        .insert_resource(SparrowConfig {
            save_path: self.save_path.clone(),
            component_filter: self.component_filter.clone(),
            ignore: self.ignore.clone(),
        })
        .configure_sets(
            PostUpdate,
            // chain() will ensure sets run in the order they are listed
            (SceneSet::Extras, SceneSet::Post)
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
        app.register_type::<GltfProcessed>()
            .add_systems(
                PostUpdate,
                (add_components_from_gltf_extras).in_set(SceneSet::Extras),
            );
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
