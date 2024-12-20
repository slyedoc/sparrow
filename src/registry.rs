use bevy::{
    prelude::*,
    reflect::{TypeInfo, TypeRegistration, VariantInfo},
};
use serde_json::{json, Map, Value};
use std::{
    env, fs::File, path::{Path, PathBuf}
};

use crate::SparrowConfig;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Resource)]
pub struct AssetRoot(pub PathBuf);

pub fn export_types(world: &mut World) {
    let config = world.get_resource::<SparrowConfig>().unwrap();

    //let asset_root = world.resource::<AssetRoot>();
    let path = env::current_dir().unwrap();
    let registry_save_path = Path::join(&path, &config.save_path);

    info!("Current directory: {:?}", path);
    let writer = match File::create(&registry_save_path) {
        Ok(writer) => writer,
        Err(e) => {
            error!("{e}, failed to create file: {:?} ", registry_save_path);
            return;
        }
    };

    let components_to_filter_out = &config.component_filter.clone()
    .allow::<Entity>()
    // add some default components
;

    let types = world.resource_mut::<AppTypeRegistry>();    
    let types = types.read();
    let schemas = types
        .iter()
        .filter(|type_info| {
            let type_id = type_info.type_id();
            components_to_filter_out.is_allowed_by_id(type_id)
        })
        .map(|type_info| {
            // TODO: save a default value to registry schema
            // let type_id = type_info.type_id();
            // let type_path = type_info.type_info().type_path();
            // let d = types.get_type_data::<ReflectDefault>(type_id);
            // let s = types.get_type_data::<ReflectSerialize>(type_id);
            // match (s, d) {
            //     (Some(_s), Some(d)) => {                    
            //         let d = d.default();
            //         //let s = s.get_serializable(&d);
            //         info!("default for type: {:?} is: {:?}", type_path, d);
            //     },
            //     (Some(_), None) => {
            //         warn!("No default for type: {:?}", type_path);
            //     },
            //     (None, Some(_)) => {
            //         warn!("No serializer for type: {:?}", type_path);
            //     },
            //     (None, None) => {},
            // }

            export_type(type_info)
        } )
        .collect::<Map<_, _>>();

    serde_json::to_writer_pretty(
        writer,
        &json!({
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "long_name": "bevy component registry schema",
            "$defs": schemas,
        }),
    )
    .expect("valid json");

    info!("Done exporting {} registry schema: {:?}", schemas.len(), registry_save_path)
}

pub fn export_type( reg: &TypeRegistration) -> (String, Value) {

    let t = reg.type_info();
    let binding = t.type_path_table();
    let short_name = binding.short_path();    

    let mut schema = match t {
        TypeInfo::Set(_info) => {
            // TODO: figure out set
            unreachable!();
        },
        TypeInfo::Struct(info) => {
            let properties = info
                .iter()
                .enumerate()
                .map(|(idx, field)| {
                    (
                        field.name().to_owned(),
                        add_min_max(json!({ "type": typ(field.type_path()) }), reg, idx, None),
                    )
                })
                .collect::<Map<_, _>>();

            json!({
                "type": "object",
                "type_info": "Struct",
                "long_name": t.type_path(),
                "properties": properties,
                "additional_properties": false,
                "required": info
                    .iter()
                    .filter(|field| !field.type_path().starts_with("core::option::Option"))
                    .map(|field| field.name())
                    .collect::<Vec<_>>(),
            })
        }
        TypeInfo::Enum(info) => {
            let simple = info
                .iter()
                .all(|variant| matches!(variant, VariantInfo::Unit(_)));
            if simple {
                json!({
                    "type": "string",
                    "type_info": "Enum",
                    "long_name": t.type_path(),
                    "one_of": info
                        .iter()
                        .map(|variant| match variant {
                            VariantInfo::Unit(v) => v.name(),
                            _ => unreachable!(),
                        })
                        .collect::<Vec<_>>(),
                })
            } else {
                let variants = info
                .iter()
                .enumerate()
                .map(|(field_idx, variant)| match variant {
                    //let binding = t.type_path_table();
                    //let short_name = binding.short_path();
                    VariantInfo::Struct(v) => json!({
                        "type": "object",
                        "type_info": "Struct",
                        "long_name": v.name(),
                        "short_name": v.name().split("::").last().unwrap_or(v.name()),
                        "properties": v
                            .iter()
                            .enumerate()
                            .map(|(variant_idx, field)| (field.name().to_owned(), add_min_max(json!({"type": typ(field.type_path()), "long_name": field.name()}), reg, field_idx, Some(variant_idx))))
                            .collect::<Map<_, _>>(),
                        "additional_properties": false,
                        "required": v
                            .iter()
                            .filter(|field| !field.type_path().starts_with("core::option::Option"))
                            .map(|field| field.name())
                            .collect::<Vec<_>>(),
                    }),
                    VariantInfo::Tuple(v) => json!({
                        "type": "array",
                        "type_info": "Tuple",
                        "long_name": v.name(),
                        "short_name":v.name(),
                        "prefix_items": v
                            .iter()
                            .enumerate()
                            .map(|(variant_idx, field)| add_min_max(json!({"type": typ(field.type_path())}), reg, field_idx, Some(variant_idx)))
                            .collect::<Vec<_>>(),
                        "items": [],
                    }),
                    VariantInfo::Unit(v) => json!({
                        "long_name": v.name(),
                    }),
                })
                .collect::<Vec<_>>();

                json!({
                    "type": "object",
                    "type_info": "Enum",
                    "long_name": t.type_path(),
                    "one_of": variants,
                })
            }
        }
        TypeInfo::TupleStruct(info) => json!({
            "long_name": t.type_path(),
            "type": "array",
            "type_info": "TupleStruct",
            "prefix_items": info
                .iter()
                .enumerate()
                .map(|(idx, field)| add_min_max(json!({"type": typ(field.type_path())}), reg, idx, None))
                .collect::<Vec<_>>(),
            "items": [],
        }),
        TypeInfo::List(info) => {
            json!({
                "long_name": t.type_path(),
                "type": "array",
                "type_info": "List",
                "items": json!({"type": typ(info.item_ty().type_path_table().path())}),
            })
        }
        TypeInfo::Array(info) => json!({
            "long_name": t.type_path(),
            "type": "array",
            "type_info": "Array",
            "items": json!({"type": typ(info.item_ty().type_path_table().path())}),
        }),
        TypeInfo::Map(info) => json!({
            "long_name": t.type_path(),
            "type": "object",
            "type_info": "Map",
            "value_type": json!({"type": typ(info.value_ty().type_path_table().path())}),
            "key_type": json!({"type": typ(info.key_ty().type_path_table().path())}),
        }),
        TypeInfo::Tuple(info) => json!({
            "long_name": t.type_path(),
            "type": "array",
            "type_info": "Tuple",
            "prefix_items": info
                .iter()
                .enumerate()
                .map(|(idx, field)| add_min_max(json!({"type": typ(field.type_path())}), reg, idx, None))
                .collect::<Vec<_>>(),
            "items": [],
        }),
        TypeInfo::Opaque(info) => json!({
            "long_name": t.type_path(),
            "type": map_json_type(info.type_path()),
            "type_info": "Value",
        }),
    };
    schema.as_object_mut().unwrap().insert(
        "is_component".to_owned(),
        reg.data::<ReflectComponent>().is_some().into(),
    );
    schema.as_object_mut().unwrap().insert(
        "is_resource".to_owned(),
        reg.data::<ReflectResource>().is_some().into(),
    );

    schema
        .as_object_mut()
        .unwrap()
        .insert("short_name".to_owned(), short_name.into());

    (t.type_path().to_owned(), schema)
}

fn typ(t: &str) -> Value {
    json!({ "$ref": format!("#/$defs/{t}") })
}

fn map_json_type(t: &str) -> Value {
    match t {
        "bool" => "boolean",
        "u8" | "u16" | "u32" | "u64" | "u128" | "usize" => "uint",
        "i8" | "i16" | "i32" | "i64" | "i128" | "isize" => "int",
        "f32" | "f64" => "float",
        "char" | "str" | "alloc::string::String" => "string",
        _ => "object",
    }
    .into()
}

// TODO: Renable inspector_options min max support
#[allow(unused_mut)]
fn add_min_max(
    mut val: Value,
    _reg: &TypeRegistration,
    _field_index: usize,
    _variant_index: Option<usize>,
) -> Value {
    //let Some((min, max)) = get_min_max(reg, field_index, variant_index) else {
        return val;
    //};
    // let obj = val.as_object_mut().unwrap();
    // if let Some(min) = min {
    //     obj.insert("minimum".to_owned(), min.into());
    // }
    // if let Some(max) = max {
    //     obj.insert("maximum".to_owned(), max.into());
    // }
    // val
}

// fn get_min_max(
//     reg: &TypeRegistration,
//     field_index: usize,
//     variant_index: Option<usize>,
// ) -> Option<(Option<f32>, Option<f32>)> {
//     use bevy_inspector_egui::inspector_options::{
//         std_options::NumberOptions, ReflectInspectorOptions, Target,
//     };

//     reg.data::<ReflectInspectorOptions>()
//         .and_then(|ReflectInspectorOptions(o)| {
//             o.get(if let Some(variant_index) = variant_index {
//                 Target::VariantField {
//                     variant_index,
//                     field_index,
//                 }
//             } else {
//                 Target::Field(field_index)
//             })
//         })
//         .and_then(|o| o.downcast_ref::<NumberOptions<f32>>())
//         .map(|num| (num.min, num.max))
// }
