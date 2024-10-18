use bevy::prelude::*;
use serde::{Deserialize, Serialize};

pub(super) fn plugin(app: &mut App) {
    app.register_type::<SceneGravity>();
}

/// Added as GltfSceneExtras based on blender scene gravity settings
#[derive(Component, Deref, DerefMut, Debug, Clone, Default, Reflect, Serialize, Deserialize)]
#[reflect(Component)]
pub struct SceneGravity(pub Vec3);