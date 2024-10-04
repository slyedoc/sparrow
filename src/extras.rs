use bevy::core::Name;
use bevy::gltf::{GltfMaterialExtras, GltfSceneExtras};
use bevy::prelude::*;
use bevy::reflect::serde::ReflectDeserializer;
use bevy::reflect::{Reflect, TypeRegistration, TypeRegistry};
use bevy::utils::HashMap;
use ron::Value;
use serde::de::DeserializeSeed;

use crate::SparrowConfig;

pub trait GltfExtraType {
    fn value(&self) -> String;
}

impl GltfExtraType for GltfExtras {
    fn value(&self) -> String {
        self.value.clone()
    }
}

impl GltfExtraType for GltfSceneExtras {
    fn value(&self) -> String {
        self.value.clone()
    }
}

impl GltfExtraType for GltfMaterialExtras {
    fn value(&self) -> String {
        self.value.clone()
    }
}

/// Instead of just adding components like gltf_extras, going to flatten new scene in 2 ways:
/// 1. adding the GltfSceneExtras up a level removing the "Scene Root" entity
/// 2. Due to  and the "Full_Colllection_Heirarchy" we get a Scene Collection, remove this as well

pub fn scene_extras_and_flatten(world: &mut World) {
    // get the added extras
    let extras = world
        .query_filtered::<(
            Entity,
            &GltfSceneExtras,
            &Parent,
            &Children,
            Option<&Name>,
        ), Added<GltfSceneExtras>>()
        .iter(world)
        .map(
            |(entity, extra, parent, children, name)| {
                (
                    entity.clone(),
                    extra.clone(),
                    parent.get(),
                    children.to_vec(),
                    name.cloned(),
                )
            },
        )
        .collect::<Vec<(
            Entity,
            GltfSceneExtras,
            Entity,
            Vec<Entity>,
            Option<Name>,
        )>>();

    world.resource_scope(|world, config: Mut<SparrowConfig>| {
        world.resource_scope(|world, type_registry: Mut<AppTypeRegistry>| {
            let type_registry = type_registry.read();
            for (entity, extra, parent, children, name) in &extras {
                let value = extra.value();
                let reflect_components = ronstring_to_reflect_component(
                    &value,
                    &type_registry,
                    name.clone(),
                    &config.ignore,
                );

                for (component, type_registration) in reflect_components {
                    let mut entity_mut = world.entity_mut(*parent); // using parent here instead of our scene root
                    type_registration
                        .data::<ReflectComponent>()
                        .expect("Unable to reflect component")
                        .insert(&mut entity_mut, &*component, &type_registry);
                }

                // delete scene root and scene collection
                for child in children {
                    //     let grand_children = world.get::<Children>(*child).unwrap().to_vec();
                    //     for gc in grand_children {
                    //         world.entity_mut(gc).set_parent(*parent);
                    //     }
                    //     world.entity_mut(*child).despawn_recursive();
                    world.entity_mut(*child).set_parent(*parent);

                }
                world.entity_mut(*entity).despawn_recursive();
                //info!("Flattened scene: {:?}", world.get::<Name>(*parent));
            }
        });
    });
}

// parse gltf extras on added and spawn the components
pub fn gltf_extras<T: Component + Clone + GltfExtraType>(world: &mut World) {
    // get the added extras
    let extras = world
        .query_filtered::<(Entity, &T, Option<&Name>), Added<T>>()
        .iter(world)
        .map(|(entity, extra, name)| (entity.clone(), extra.clone(), name.cloned()))
        .collect::<Vec<(Entity, T, Option<Name>)>>();
    if !extras.is_empty() {
        world.resource_scope(|world, config: Mut<SparrowConfig>| {
            world.resource_scope(|world, type_registry: Mut<AppTypeRegistry>| {
                let type_registry = type_registry.read();
                for (entity, extra, name) in &extras {
                    let value = extra.value();
                    let reflect_components = ronstring_to_reflect_component(
                        &value,
                        &type_registry,
                        name.clone(),
                        &config.ignore,
                    );
                    for (component, type_registration) in reflect_components {
                        //info!("inserting component {:?}", type_registration.type_info());
                        let mut entity_mut = world.entity_mut(*entity);

                        if let Some(reflect_component) = type_registration
                            .data::<ReflectComponent>() {
                                reflect_component.insert(&mut entity_mut, &*component, &type_registry);
                        } else {
                            error!("Unable to get reflect component for {:?}, did you forget to add #[reflect(Component)] to your component?", type_registration.type_info());
                        }
                    }
                }
            });
        });
    }
}

pub fn ronstring_to_reflect_component(
    ron_string: &str,
    type_registry: &TypeRegistry,
    name: Option<Name>,
    ignore: &[String],
) -> Vec<(Box<dyn Reflect>, TypeRegistration)> {
    let lookup: HashMap<String, Value> = ron::from_str(ron_string).unwrap();
    let mut components: Vec<(Box<dyn Reflect>, TypeRegistration)> = Vec::new();
    // if ron_string.contains("bevy_components") {
    //     dbg!(ron_string, &lookup);
    // }

    for (component, value) in lookup.into_iter() {
        //info!("{:?} - {:?}: {:?}", &name, &component, &value);
        let parsed_value: String = match value.clone() {
            Value::String(str) => str,
            _ => ron::to_string(&value).unwrap().to_string(),
        };

        if component.as_str() == "bevy_components" {
            bevy_components_string_to_components(
                parsed_value,
                type_registry,
                &mut components,
                &name,
            );
        } else {
            components_string_to_components(
                &name,
                component,
                value,
                parsed_value,
                type_registry,
                &mut components,
                ignore,
            );
        }
    }
    components
}

fn components_string_to_components(
    entity_name: &Option<Name>,
    name: String,
    value: Value,
    parsed_value: String,
    type_registry: &TypeRegistry,
    components: &mut Vec<(Box<dyn Reflect>, TypeRegistration)>,
    ignore: &[String],
) {
    let type_string = name.replace("component: ", "").trim().to_string();
    let capitalized_type_name = capitalize_first_letter(type_string.as_str());

    if let Some(type_registration) =
        type_registry.get_with_short_type_path(capitalized_type_name.as_str())
    {
        //info!("TYPE INFO {:?}", type_registration.type_info());

        let ron_string = format!(
            "{{ \"{}\":{} }}",
            type_registration.type_info().type_path(),
            parsed_value
        );

        // usefull to determine what an entity looks like Serialized
        /*let test_struct = CameraRenderGraph::new("name");
        let serializer = ReflectSerializer::new(&test_struct, &type_registry);
        let serialized =
            ron::ser::to_string_pretty(&serializer, ron::ser::PrettyConfig::default()).unwrap();
        println!("serialized Component {}", serialized);*/

        debug!("component data ron string {}", ron_string);

        let mut deserializer = ron::Deserializer::from_str(ron_string.as_str())
            .expect("deserialzer should have been generated from string");
        let reflect_deserializer = ReflectDeserializer::new(type_registry);
        if let Ok(component) = reflect_deserializer.deserialize(&mut deserializer) {
            components.push((component, type_registration.clone()));
        } else {
            warn!(
                "failed to deserialize component on {:?} - {} with value: {:?}",
                entity_name, name, value,
            )
        }
    } else {
        // Components_meta self made, rest are 3rd party plugins in blender I have
        if !ignore.iter().any(|s| capitalized_type_name.contains(s)) {
            warn!(
                "no type registration on {:?} for {}",
                entity_name, capitalized_type_name
            );
        }
    }
}

fn bevy_components_string_to_components(
    parsed_value: String,
    type_registry: &TypeRegistry,
    components: &mut Vec<(Box<dyn Reflect>, TypeRegistration)>,
    name: &Option<Name>,
) {
    let Ok(lookup)= ron::from_str::<HashMap<String, Value>>(&parsed_value) else {
        warn!("failed to parse bevy_components on {:?}", name);
        return;
    };

    for (key, value) in lookup.into_iter() {
        //info!("----- {:?}: {:?}", &key, &value);
        let parsed_value: String = match value.clone() {
            Value::String(str) => str,
            _ => ron::to_string(&value).unwrap().to_string(),
        };

        if let Some(type_registration) = type_registry.get_with_type_path(key.as_str()) {
            debug!("TYPE INFO {:?}", type_registration.type_info());

            let ron_string = format!(
                "{{ \"{}\":{} }}",
                type_registration.type_info().type_path(),
                parsed_value
            );

            debug!("component data ron string {}", ron_string);
            let mut deserializer = ron::Deserializer::from_str(ron_string.as_str())
                .expect("deserialzer should have been generated from string");
            let reflect_deserializer = ReflectDeserializer::new(type_registry);
            let Ok(component) = reflect_deserializer.deserialize(&mut deserializer) else {
                warn!(
                    "failed to deserialize component on {:?} - {} with value: {:?}",
                    name, key, value,
                );
                return;
            };

            debug!("component {:?}", component);
            debug!("real type {:?}", component.get_represented_type_info());
            components.push((component, type_registration.clone()));
            debug!("found type registration for {}", key);
        } else {
            warn!("no type registration on {:?} for {}", name, key);
        }
    }
}

fn capitalize_first_letter(s: &str) -> String {
    s[0..1].to_uppercase() + &s[1..]
}
