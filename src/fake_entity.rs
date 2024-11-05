// Based on https://github.com/kaosat-dev/Blenvy/pull/236 


use std::{alloc::Layout, cell::Cell, num::NonZeroU32};
use bevy::{
    core::Name,
    ecs::system::SystemParam,
    gltf::GltfExtras,
    log::warn,
    prelude::{HierarchyQueryExt, Parent, Query, With},
    reflect::ReflectDeserialize,
    scene::{InstanceId, SceneInstance},
};
use serde::Deserialize;

#[derive(SystemParam)]
pub(crate) struct BadWorldAccess<'w, 's> {
    pub(crate) names: Query<'w, 's, (bevy::ecs::entity::Entity, &'static Name), With<GltfExtras>>,
    pub(crate) hierarchy: Query<'w, 's, &'static Parent, ()>,
    pub(crate) scene_instances: Query<'w, 's, &'static SceneInstance, ()>,
}

thread_local! {
    pub(crate) static BAD_WORLD_ACCESS: Cell<Option<BadWorldAccess<'static, 'static>>> = Cell::new(None);
    pub(crate) static INSTANCE_ID: Cell<Option<InstanceId>> = Cell::new(None);
}

const _: () = {
    let real = Layout::new::<bevy::ecs::entity::Entity>();
    let fake = Layout::new::<Entity>();
    assert!(real.size() == fake.size());
    assert!(real.align() == fake.align());
};

#[derive(Clone, Hash, Debug, PartialEq, Eq)]
#[repr(C, align(8))]
pub(crate) struct Entity {
    // Do not reorder the fields here. The ordering is equivalent to bevy's `Entity`
    #[cfg(target_endian = "little")]
    index: u32,
    generation: NonZeroU32,
    #[cfg(target_endian = "big")]
    index: u32,
}

impl<'de> Deserialize<'de> for Entity {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        #[derive(Deserialize)]
        #[serde(rename = "Entity")]
        struct EntityData {
            name: Option<String>,
        }

        let entity_data = EntityData::deserialize(deserializer)?;

        let entity = if let Some(name) = entity_data.name {
            // info!("Found name {name}");
            let BadWorldAccess {
                names,
                hierarchy,
                scene_instances,
            } = BAD_WORLD_ACCESS.take().expect("No bad world access :c");
            let instance = INSTANCE_ID.get().expect("No instance id set :c");

            let mut target = None;
            'search: for (e, n) in names.iter() {
                if !name.eq(n.as_str()) {
                    continue;
                }

                for parent in hierarchy.iter_ancestors(e) {
                    let Ok(id) = scene_instances.get(parent) else {
                        continue;
                    };
                    if instance.eq(id) {
                        target = Some(e);
                        break 'search;
                    }
                }
            }

            BAD_WORLD_ACCESS.set(Some(BadWorldAccess {
                names,
                hierarchy,
                scene_instances,
            }));

            target.unwrap_or_else(|| {
                warn!("No entity found for '{name}' - perhaps it doesn't contain any components from blender?");
                bevy::ecs::entity::Entity::PLACEHOLDER
            })
        } else {
            warn!("No object was specified for Entity relation, using `Entity::PLACEHOLDER`.");
            bevy::ecs::entity::Entity::PLACEHOLDER
        };

        Ok(unsafe {
            // SAFETY: both have the same layout
            core::mem::transmute(entity)
        })
    }
}

// This is expanded and modified from
// ```
// #[derive(Clone, Reflect)]
// #[reflect_value(Deserialize)]
// ```
const _: () = {
    use bevy::reflect as bevy_reflect;

    #[allow(unused_mut)]
    impl bevy_reflect::GetTypeRegistration for Entity
    where
        Self: ::core::any::Any + ::core::marker::Send + ::core::marker::Sync,
    {
        fn get_type_registration() -> bevy_reflect::TypeRegistration {
            let mut registration = bevy_reflect::TypeRegistration::of::<Self>();
            registration
                .insert::<
                    bevy_reflect::ReflectFromPtr,
                >(bevy_reflect::FromType::<Self>::from_type());
            registration.insert::<bevy_reflect::ReflectFromReflect>(
                bevy_reflect::FromType::<Self>::from_type(),
            );
            registration.insert::<ReflectDeserialize>(bevy_reflect::FromType::<Self>::from_type());
            registration
        }
    }
    impl bevy_reflect::TypePath for Entity
    where
        Self: ::core::any::Any + ::core::marker::Send + ::core::marker::Sync,
    {
        fn type_path() -> &'static str {
            "bevy_ecs::entity::Entity" // this is changed
        }
        fn short_type_path() -> &'static str {
            "Entity"
        }
        fn type_ident() -> Option<&'static str> {
            ::core::option::Option::Some("Entity")
        }
        fn crate_name() -> Option<&'static str> {
            // this is changed
            ::core::option::Option::Some("bevy_ecs::entity".split(':').next().unwrap())
        }
        fn module_path() -> Option<&'static str> {
            ::core::option::Option::Some("bevy_ecs::entity") // this is changed
        }
    }
    impl bevy_reflect::Typed for Entity
    where
        Self: ::core::any::Any + ::core::marker::Send + ::core::marker::Sync,
    {
        fn type_info() -> &'static bevy_reflect::TypeInfo {
            static CELL: bevy_reflect::utility::NonGenericTypeInfoCell =
                bevy_reflect::utility::NonGenericTypeInfoCell::new();
            CELL.get_or_set(|| {
                let info = bevy_reflect::OpaqueInfo::new::<bevy::ecs::entity::Entity>(); // this is changed
                bevy_reflect::TypeInfo::Opaque(info)
            })
        }
    }
    impl bevy_reflect::Reflect for Entity
    where
        Self: ::core::any::Any + ::core::marker::Send + ::core::marker::Sync,
    {
        #[inline]
        fn into_any(self: ::std::boxed::Box<Self>) -> ::std::boxed::Box<dyn ::core::any::Any> {
            // this is changed
            unsafe {
                core::mem::transmute::<
                    ::std::boxed::Box<Entity>,
                    ::std::boxed::Box<bevy::ecs::entity::Entity>,
                >(self)
            }
        }
        #[inline]
        fn as_any(&self) -> &dyn ::core::any::Any {
            // this is changed
            unsafe { core::mem::transmute::<&Entity, &bevy::ecs::entity::Entity>(self) }
        }
        #[inline]
        fn as_any_mut(&mut self) -> &mut dyn ::core::any::Any {
            // this is changed
            unsafe { core::mem::transmute::<&mut Entity, &mut bevy::ecs::entity::Entity>(self) }
        }
        #[inline]
        fn into_reflect(
            self: ::std::boxed::Box<Self>,
        ) -> ::std::boxed::Box<dyn bevy_reflect::Reflect> {
            self
        }
        #[inline]
        fn as_reflect(&self) -> &dyn bevy_reflect::Reflect {
            self
        }
        #[inline]
        fn as_reflect_mut(&mut self) -> &mut dyn bevy_reflect::Reflect {
            self
        }

        #[inline]
        fn set(
            &mut self,
            value: ::std::boxed::Box<dyn bevy_reflect::Reflect>,
        ) -> ::core::result::Result<(), ::std::boxed::Box<dyn bevy_reflect::Reflect>> {
            *self = <dyn bevy_reflect::Reflect>::take(value)?;
            ::core::result::Result::Ok(())
        }

    }
    impl bevy_reflect::PartialReflect for Entity
    where
        Entity: ::core::any::Any + ::core::marker::Send + ::core::marker::Sync,
    {
        #[inline]
        fn get_represented_type_info(
            &self,
        ) -> ::core::option::Option<&'static bevy_reflect::TypeInfo> {
            ::core::option::Option::Some(<Self as bevy_reflect::Typed>::type_info())
        }
        #[inline]
        fn clone_value(&self) -> ::std::boxed::Box<dyn bevy_reflect::PartialReflect> {
            ::std::boxed::Box::new(::core::clone::Clone::clone(self))
        }

        #[inline]
        fn try_apply(
            &mut self,
            value: &dyn bevy_reflect::PartialReflect,
        ) -> ::core::result::Result<(), bevy_reflect::ApplyError> {
            if let ::core::option::Option::Some(value) =
                <dyn bevy_reflect::PartialReflect>::try_downcast_ref::<Self>(value)
            {
                *self = ::core::clone::Clone::clone(value);
                return ::core::result::Result::Ok(());
            }
            ::core::result::Result::Err(bevy_reflect::ApplyError::MismatchedTypes {
                from_type: ::core::convert::Into::into(
                    bevy_reflect::DynamicTypePath::reflect_type_path(value),
                ),
                to_type: ::core::convert::Into::into(<Self as bevy_reflect::TypePath>::type_path()),
            })
        }
        #[inline]
        fn reflect_kind(&self) -> bevy_reflect::ReflectKind {
            bevy_reflect::ReflectKind::Opaque
        }
        #[inline]
        fn reflect_ref(&self) -> bevy_reflect::ReflectRef {
            bevy_reflect::ReflectRef::Opaque(self)
        }
        #[inline]
        fn reflect_mut(&mut self) -> bevy_reflect::ReflectMut {
            bevy_reflect::ReflectMut::Opaque(self)
        }
        #[inline]
        fn reflect_owned(self: ::std::boxed::Box<Self>) -> bevy_reflect::ReflectOwned {
            bevy_reflect::ReflectOwned::Opaque(self)
        }
        #[inline]
        fn try_into_reflect(
            self: ::std::boxed::Box<Self>,
        ) -> ::core::result::Result<
            ::std::boxed::Box<dyn bevy_reflect::Reflect>,
            ::std::boxed::Box<dyn bevy_reflect::PartialReflect>,
        > {
            ::core::result::Result::Ok(self)
        }
        #[inline]
        fn try_as_reflect(&self) -> ::core::option::Option<&dyn bevy_reflect::Reflect> {
            ::core::option::Option::Some(self)
        }
        #[inline]
        fn try_as_reflect_mut(&mut self) -> ::core::option::Option<&mut dyn bevy_reflect::Reflect> {
            ::core::option::Option::Some(self)
        }
        #[inline]
        fn into_partial_reflect(
            self: ::std::boxed::Box<Self>,
        ) -> ::std::boxed::Box<dyn bevy_reflect::PartialReflect> {
            self
        }
        #[inline]
        fn as_partial_reflect(&self) -> &dyn bevy_reflect::PartialReflect {
            self
        }
        #[inline]
        fn as_partial_reflect_mut(&mut self) -> &mut dyn bevy_reflect::PartialReflect {
            self
        }
        fn reflect_hash(&self) -> ::core::option::Option<u64> {
            use ::core::hash::{Hash, Hasher};
            let mut hasher = bevy_reflect::utility::reflect_hasher();
            Hash::hash(&::core::any::Any::type_id(self), &mut hasher);
            Hash::hash(self, &mut hasher);
            ::core::option::Option::Some(Hasher::finish(&hasher))
        }
        fn reflect_partial_eq(
            &self,
            value: &dyn bevy_reflect::PartialReflect,
        ) -> ::core::option::Option<bool> {
            let value = <dyn bevy_reflect::PartialReflect>::try_downcast_ref::<Self>(value);
            if let ::core::option::Option::Some(value) = value {
                ::core::option::Option::Some(::core::cmp::PartialEq::eq(self, value))
            } else {
                ::core::option::Option::Some(false)
            }
        }
        fn debug(&self, f: &mut ::core::fmt::Formatter<'_>) -> ::core::fmt::Result {
            ::core::fmt::Debug::fmt(self, f)
        }
    }

    impl bevy_reflect::FromReflect for Entity
    where
        Self: ::core::any::Any + ::core::marker::Send + ::core::marker::Sync,
    {
        fn from_reflect(
            reflect: &dyn bevy_reflect::PartialReflect,
        ) -> ::core::option::Option<Self> {
            ::core::option::Option::Some(::core::clone::Clone::clone(
                <dyn bevy_reflect::PartialReflect>::try_downcast_ref::<Entity>(reflect)?,
            ))
        }
    }
};