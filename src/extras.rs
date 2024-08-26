use bevy::core::Name;
use bevy::gltf::{GltfMaterialExtras, GltfSceneExtras};
use bevy::prelude::*;
use bevy::reflect::serde::ReflectDeserializer;
use bevy::reflect::{Reflect, TypeRegistration, TypeRegistry};
use bevy::utils::HashMap;
use ron::Value;
use serde::de::DeserializeSeed;


pub trait GltfExtraType {
    fn value(&self) -> String;
}

impl GltfExtraType for GltfExtras {
    fn value(&self) -> String {
        self.value.clone()
    }
}

impl GltfExtraType for GltfSceneExtras{
    fn value(&self) -> String {
        self.value.clone()
    }
}

impl GltfExtraType for GltfMaterialExtras{
    fn value(&self) -> String {
        self.value.clone()
    }
}

// parse gltf extras on added and spawn the components
// note: using world so we can make use of ReflectComponent::insert
pub fn spawn_gltf_extras<T: Component + Clone + GltfExtraType>(world: &mut World) {
    // get the added extras
    let extras = world
        .query_filtered::<(
            Entity,
            &T,
            Option<&Name>,
        ), Added<T>>()
        .iter(world)
        .map(
            |(entity, extra,  name)| {
                (
                    entity.clone(),
                    extra.clone(),
                    name.cloned(),
                )
            },
        )
        .collect::<Vec<(
            Entity,
            T,
            Option<Name>,
        )>>();
    if !extras.is_empty() {
        // info!("spawning gltf extras: {:?}", extras);
        // add the components
        world.resource_scope(
            |world, type_registry: Mut<AppTypeRegistry>| {
                let type_registry = type_registry.read();
                for (entity, extra, name) in &extras {
       
                    let value = extra.value();
                    let reflect_components = ronstring_to_reflect_component(
                        &value,
                        &type_registry,
                        name.clone(),
                    );
                    for (component, type_registration) in reflect_components {
                        //info!("inserting component {:?}", type_registration.type_info());
                        let mut entity_mut = world.entity_mut(*entity);
                        type_registration
                            .data::<ReflectComponent>()
                            .expect("Unable to reflect component")
                            .insert(
                                &mut entity_mut,
                                &*component,
                                &type_registry,
                            );
                    }
                }
            },
        );
    }
}

pub fn ronstring_to_reflect_component(
    ron_string: &str,
    type_registry: &TypeRegistry,
    name: Option<Name>,
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
            bevy_components_string_to_components(parsed_value, type_registry, &mut components, &name);
        } else {
            components_string_to_components(
                &name,
                component,
                value,
                parsed_value,
                type_registry,
                &mut components,
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
        let component = reflect_deserializer
            .deserialize(&mut deserializer)
            .unwrap_or_else(|_| {
                panic!(
                    "failed to deserialize component {} with value: {:?}",
                    name, value
                )
            });

        debug!("component {:?}", component);
        debug!("real type {:?}", component.get_represented_type_info());
        components.push((component, type_registration.clone()));
        debug!("found type registration for {}", capitalized_type_name);
    } else {
        // Components_meta self made, rest are 3rd party plugins in blender I have
        let ignore = vec![
            // our selfs
            "Components_meta",
            "Ant_landscape",
            "COLOR_1",
            "Gltf2_animation_rest",
            "CurrentUVSet",
            // shipwright_collection
            "Plating_generator",
            "Shipwright_collection",
            "Shape_generator_collection",
            // 3d space ships
            "MaxHandle",
            "Mr displacement",
            "MapChannel:1",
            // art blender stuff
            "Conform_object",
            "Kitops",
            "Hair_brush_3d",
            "Hops",
            "Scatter5",
            "Autobake_properties",
            "Sparrow_scene",
            "Sparrow_scene_props",
        ];
        if !ignore.iter().any(|s| capitalized_type_name.contains(s)) {
            warn!("no type registration on {:?} for {}", entity_name, capitalized_type_name);
        }
    }
}

fn bevy_components_string_to_components(
    parsed_value: String,
    type_registry: &TypeRegistry,
    components: &mut Vec<(Box<dyn Reflect>, TypeRegistration)>,
    name: &Option<Name>,
) {
    let lookup: HashMap<String, Value> = ron::from_str(&parsed_value).unwrap();
    for (key, value) in lookup.into_iter() {
        info!("----- {:?}: {:?}", &key, &value);
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
                panic!(
                    "failed to deserialize component on {:?} - {} with value: {:?}",
                    name, key, value, 
                )
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
