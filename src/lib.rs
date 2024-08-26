use bevy::{gltf::GltfSceneExtras, prelude::*};
use std::path::PathBuf;

mod registry;
pub use registry::*;

mod extras;
pub use extras::*;

#[derive(Debug, Clone)]
/// Plugin for gltf blueprints
pub struct SparrowPlugin {
    /// Path to save the registry schema, relative to the assets folder
    pub save_path: PathBuf,
    pub component_filter: SceneFilter,
}

impl Default for SparrowPlugin {
    fn default() -> Self {
        Self {
            save_path: PathBuf::from("../art/registry.json"),
            component_filter: SceneFilter::default(),
        }
    }
}

#[derive(Resource)]
pub struct SparrowConfig {
    pub save_path: PathBuf,
    pub component_filter: SceneFilter,
}

impl Plugin for SparrowPlugin {
    fn build(&self, app: &mut App) {
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
        app.add_systems(
            PostUpdate,
            (
                spawn_gltf_extras::<GltfSceneExtras>,
                spawn_gltf_extras::<GltfExtras>,
            ),
        );

        app.insert_resource(SparrowConfig {
            save_path: self.save_path.clone(),
            component_filter: self.component_filter.clone(),
        });
    }
}
