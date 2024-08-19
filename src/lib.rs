use std::path::PathBuf;

#[derive(Debug, Clone)]
/// Plugin for gltf blueprints
pub struct SparrowPlugin {
    pub save_path: PathBuf,
    //pub component_filter: SceneFilter,
    //pub resource_filter: SceneFilter,
}