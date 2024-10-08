use std::any::TypeId;

use bevy::core::Name;
use bevy::log::{debug, warn};
use bevy::reflect::serde::ReflectDeserializer;
use bevy::reflect::{GetTypeRegistration, Reflect, TypeRegistration, TypeRegistry};
use bevy::utils::HashMap;
use ron::Value;
use serde::de::DeserializeSeed;

use crate::fake_entity;

pub(crate) fn ronstring_to_reflect_component(
    ron_string: &str,
    type_registry: &mut TypeRegistry,
    name: &Option<&Name>, // For better error messages
    ignore: &[String],    // ignore these components
) -> Vec<(Box<dyn Reflect>, TypeRegistration)> {
    
    let lookup: HashMap<String, Value> = ron::from_str(ron_string).unwrap();
    let mut components: Vec<(Box<dyn Reflect>, TypeRegistration)> = Vec::new();

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
                name,
            );
        } else {
            components_string_to_components(
                name,
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
    entity_name: &Option<&Name>,
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
                "failed to deserialize string component on {:?} - {} with value: {:?}",
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
    type_registry: &mut TypeRegistry,
    components: &mut Vec<(Box<dyn Reflect>, TypeRegistration)>,
    name: &Option<&Name>, // For better error messages
) {
    let Ok(lookup) = ron::from_str::<HashMap<String, Value>>(&parsed_value) else {
        warn!("failed to parse bevy_components on {:?}", name);
        return;
    };

    let recovery_entity_type = type_registry
        .get(TypeId::of::<bevy::ecs::entity::Entity>())
        .cloned();
    type_registry.overwrite_registration(fake_entity::Entity::get_type_registration());

    for (key, value) in lookup.into_iter() {
        let parsed_value = match value.clone() {
            Value::String(str) => str,
            _ => ron::to_string(&value).unwrap().to_string(),
        };

        if let Some(type_registration) = type_registry.get_with_type_path(key.as_str()) {
            let ron_string = format!(
                "{{ \"{}\":{} }}",
                type_registration.type_info().type_path(),
                parsed_value
            );

            //info!("{:?} - {:?} - {:?}", name, key, ron_string);
            let mut deserializer = ron::Deserializer::from_str(ron_string.as_str())
                .expect("deserialzer should have been generated from string");
            let reflect_deserializer = ReflectDeserializer::new(type_registry);
            let component = reflect_deserializer
                .deserialize(&mut deserializer)
                .unwrap_or_else(|e| {
                    panic!(
                        "failed to deserialize {:?} component '{}'\n{}\n{:?}",
                        name, key, ron_string, e
                    )
                });
            components.push((component, type_registration.clone()));
        } else {
            warn!("no type registration on {:?} for {}", name, key);
        }
    }

    if let Some(original_entity) = recovery_entity_type {
        type_registry.overwrite_registration(original_entity);
    } else {
        warn!("There isn't an original type registration for `bevy_ecs::entity::Entity` but it was overwriten. Stuff may break and/or panic. Make sure that you register it!");
    }
}

fn capitalize_first_letter(s: &str) -> String {
    s[0..1].to_uppercase() + &s[1..]
}
