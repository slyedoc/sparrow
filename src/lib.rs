use bevy::{prelude::*, reflect::{TypeInfo, TypeRegistration, VariantInfo}};
use std::{fs::File, path::{Path, PathBuf}};
use serde_json::{json, Map, Value};

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
            let asset_plugin = asset_plugins.into_iter().next().expect(
                "Asset plugin required.",
            );
            let path_str = asset_plugin.file_path.clone();
            let path = PathBuf::from(path_str);

            app.insert_resource(AssetRoot(path))
                .add_systems(Startup, export_types);
        }  

        app.insert_resource(SparrowConfig {
            save_path: self.save_path.clone(),
            component_filter: self.component_filter.clone(),
        });      
    }
}


#[derive(Debug, Clone, PartialEq, Eq, Hash, Resource)]
pub struct AssetRoot(pub PathBuf);

pub fn export_types(world: &mut World) {
    let config = world
        .get_resource::<SparrowConfig>()
        .unwrap();

    let asset_root = world.resource::<AssetRoot>();
    let registry_save_path = Path::join(&asset_root.0, &config.save_path);
    info!("Exporting registry schema: {:?}", registry_save_path);
    let writer = File::create(&registry_save_path).expect("should have created schema file");

    let components_to_filter_out = &config.component_filter.clone();
    //let resources_to_filter_out = &config.resource_filter.clone();

    let types = world.resource_mut::<AppTypeRegistry>();
    let types = types.read();
    let schemas = types
        .iter()
        .filter(|type_info| {
            let type_id = type_info.type_id();
            components_to_filter_out.is_allowed_by_id(type_id)
            //    && resources_to_filter_out.is_allowed_by_id(type_id)
        })
        .map(export_type)
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

    info!("Done exporting registry schema: {:?}", registry_save_path)
}

pub fn export_type(reg: &TypeRegistration) -> (String, Value) {
    let t = reg.type_info();
    let binding = t.type_path_table();
    let short_name = binding.short_path();
    let mut schema = match t {
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
                    "oneOf": info
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
                        "prefixItems": v
                            .iter()
                            .enumerate()
                            .map(|(variant_idx, field)| add_min_max(json!({"type": typ(field.type_path())}), reg, field_idx, Some(variant_idx)))
                            .collect::<Vec<_>>(),
                        "items": false,
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
                    "oneOf": variants,
                })
            }
        }
        TypeInfo::TupleStruct(info) => json!({
            "long_name": t.type_path(),
            "type": "array",
            "type_info": "TupleStruct",
            "prefixItems": info
                .iter()
                .enumerate()
                .map(|(idx, field)| add_min_max(json!({"type": typ(field.type_path())}), reg, idx, None))
                .collect::<Vec<_>>(),
            "items": false,
        }),
        TypeInfo::List(info) => {
            json!({
                "long_name": t.type_path(),
                "type": "array",
                "type_info": "List",
                "items": json!({"type": typ(info.item_type_path_table().path())}),
            })
        }
        TypeInfo::Array(info) => json!({
            "long_name": t.type_path(),
            "type": "array",
            "type_info": "Array",
            "items": json!({"type": typ(info.item_type_path_table().path())}),
        }),
        TypeInfo::Map(info) => json!({
            "long_name": t.type_path(),
            "type": "object",
            "type_info": "Map",
            "valueType": json!({"type": typ(info.value_type_path_table().path())}),
            "keyType": json!({"type": typ(info.key_type_path_table().path())}),
        }),
        TypeInfo::Tuple(info) => json!({
            "long_name": t.type_path(),
            "type": "array",
            "type_info": "Tuple",
            "prefixItems": info
                .iter()
                .enumerate()
                .map(|(idx, field)| add_min_max(json!({"type": typ(field.type_path())}), reg, idx, None))
                .collect::<Vec<_>>(),
            "items": false,
        }),
        TypeInfo::Value(info) => json!({
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

fn add_min_max(
    mut val: Value,
    reg: &TypeRegistration,
    field_index: usize,
    variant_index: Option<usize>,
) -> Value {

    let Some((min, max)) = get_min_max(reg, field_index, variant_index) else {
        return val;
    };
    let obj = val.as_object_mut().unwrap();
    if let Some(min) = min {
        obj.insert("minimum".to_owned(), min.into());
    }
    if let Some(max) = max {
        obj.insert("maximum".to_owned(), max.into());
    }
    val
}

fn get_min_max(
    reg: &TypeRegistration,
    field_index: usize,
    variant_index: Option<usize>,
) -> Option<(Option<f32>, Option<f32>)> {
    use bevy_inspector_egui::inspector_options::{
        std_options::NumberOptions, ReflectInspectorOptions, Target,
    };

    reg.data::<ReflectInspectorOptions>()
        .and_then(|ReflectInspectorOptions(o)| {
            o.get(if let Some(variant_index) = variant_index {
                Target::VariantField {
                    variant_index,
                    field_index,
                }
            } else {
                Target::Field(field_index)
            })
        })
        .and_then(|o| o.downcast_ref::<NumberOptions<f32>>())
        .map(|num| (num.min, num.max))
}