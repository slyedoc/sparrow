use std::time::Duration;

use bevy::{animation::AnimationTarget, prelude::*, utils::HashMap};

use crate::{SceneLoaded, SparrowSet};

pub(crate) fn plugin(app: &mut App) {
    app.add_systems(
        PostUpdate,
        (
            set_animation_clips,
            apply_deferred,
            scene_auto_play_animations,
        )
            .chain()
            .in_set(SparrowSet::Post),
    );
}

#[derive(Component, Reflect, Default, Debug)]
#[reflect(Component)]
/// storage for animations for a given entity (hierarchy), essentially a clone
/// of gltf's `named_animations`
pub struct Animations {
    pub named_animations: HashMap<String, Handle<AnimationClip>>,
    pub named_indices: HashMap<String, AnimationNodeIndex>,
}

/// Controls animation clips for a unique entity.
#[derive(Component)]
struct Clips {
    nodes: Vec<AnimationNodeIndex>,
    current: usize,
}
impl Clips {
    fn new(clips: Vec<AnimationNodeIndex>) -> Self {
        Clips {
            nodes: clips,
            current: 0,
        }
    }

    /// # Panics
    ///
    /// When no clips are present.
    fn current(&self) -> AnimationNodeIndex {
        self.nodes[self.current]
    }

    #[allow(dead_code)]
    fn advance_to_next(&mut self) {
        self.current = (self.current + 1) % self.nodes.len();
    }
}

pub fn scene_auto_play_animations(
    mut commands: Commands,
    mut players: Query<(Entity, &Animations, &mut AnimationPlayer), Added<AnimationPlayer>>,
) {
    for (entity, animations, mut player) in &mut players {
        error!("Setting up scene for {:?}", entity);
        let mut transitions = AnimationTransitions::new();

        // Make sure to start the animation via the `AnimationTransitions`
        // component. The `AnimationTransitions` component wants to manage all
        // the animations and will get confused if the animations are started
        // directly via the `AnimationPlayer`.
        let index = animations.named_indices.values().next().unwrap();
        transitions
            .play(&mut player, *index, Duration::ZERO)
            .repeat();

        commands.entity(entity).insert(transitions);
    }
}

/// Automatically assign [`AnimationClip`]s to [`AnimationPlayer`] and play
/// them, if the clips refer to descendants of the animation player (which is
/// the common case).
// from bevy scene viewer example
#[allow(clippy::too_many_arguments)]
pub fn set_animation_clips(
    query: Query<&SceneLoaded, Changed<SceneRoot>>,
    mut players: Query<&mut AnimationPlayer>,
    targets: Query<(Entity, &AnimationTarget)>,
    parents: Query<&Parent>,
    clips: Res<Assets<AnimationClip>>,
    gltf_assets: Res<Assets<Gltf>>,
    assets: Res<AssetServer>,
    mut graphs: ResMut<Assets<AnimationGraph>>,
    mut commands: Commands,
) {
    for scene_loaded in query.iter() {
        let gltf = gltf_assets.get(&scene_loaded.0).unwrap();
        let animations = &gltf.animations;
        if animations.is_empty() {
            return;
        }

        // let target_count = targets.iter().count();
        // dbg!(&target_count);

        // let count = animations.len();
        // dbg!(&count);
        // let plural = if count == 1 { "" } else { "s" };
        // info!(
        //     "Found {} animation{plural}",
        //     animations.len()
        // );
        // let names: Vec<_> = gltf.named_animations.keys().collect();
        // info!("Animation names: {names:?}");

        // Map animation target IDs to entities.
        let animation_target_id_to_entity: HashMap<_, _> = targets
            .iter()
            .map(|(entity, target)| (target.id, entity))
            .collect();

        // Build up a list of all animation clips that belong to each player. A clip
        // is considered to belong to an animation player if all targets of the clip
        // refer to entities whose nearest ancestor player is that animation player.

        let mut player_to_graph: bevy::ecs::entity::EntityHashMap<(
            AnimationGraph,
            Vec<AnimationNodeIndex>,
        )> = bevy::ecs::entity::EntityHashMap::default();

        for (clip_id, clip) in clips.iter() {
            // dbg!(clip);
            let mut ancestor_player = None;
            for target_id in clip.curves().keys() {
                // If the animation clip refers to entities that aren't present in
                // the scene, bail.
                let Some(&target) = animation_target_id_to_entity.get(target_id) else {
                    continue;
                };

                // Find the nearest ancestor animation player.
                let mut current = Some(target);
                while let Some(entity) = current {
                    if players.contains(entity) {
                        match ancestor_player {
                            None => {
                                // If we haven't found a player yet, record the one
                                // we found.
                                ancestor_player = Some(entity);
                            }
                            Some(ancestor) => {
                                // If we have found a player, then make sure it's
                                // the same player we located before.
                                if ancestor != entity {
                                    // It's a different player. Bail.
                                    ancestor_player = None;
                                    break;
                                }
                            }
                        }
                    }

                    // Go to the next parent.
                    current = parents.get(entity).ok().map(Parent::get);
                }
            }

            let Some(ancestor_player) = ancestor_player else {
                // ------------------------------------------------------------------------------------------------------
                // warn!(
                //     "Unexpected animation hierarchy for animation clip {:?}; ignoring.",
                //     clip_id
                // );
                // ------------------------------------------------------------------------------------------------------
                continue;
            };

            let Some(clip_handle) = assets.get_id_handle(clip_id) else {
                warn!("Clip {:?} wasn't loaded.", clip_id);
                continue;
            };

            let &mut (ref mut graph, ref mut clip_indices) =
                player_to_graph.entry(ancestor_player).or_default();
            let node_index = graph.add_clip(clip_handle, 1.0, graph.root);
            clip_indices.push(node_index);
        }

        // Now that we've built up a list of all clips that belong to each player,
        // package them up into a `Clips` component, play the first such animation,
        // and add that component to the player.
        for (player_entity, (graph, clips)) in player_to_graph {
            let Ok(mut player) = players.get_mut(player_entity) else {
                warn!("Animation targets referenced a nonexistent player. This shouldn't happen.");
                continue;
            };
            let graph = graphs.add(graph);
            let animations = Clips::new(clips);
            player.play(animations.current()).repeat();
            commands
                .entity(player_entity)
                .insert((animations, AnimationGraphHandle(graph)));
        }
    }
}
