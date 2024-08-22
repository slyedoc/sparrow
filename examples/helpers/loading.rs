use bevy::{color::palettes::css, diagnostic::DiagnosticsStore, prelude::*};
use bevy_asset_loader::prelude::*;
use iyes_progress::prelude::*;
use sickle_ui::prelude::*;

use crate::{AppState, GameAssets, UiMainRootNode};

pub(super) fn plugin(app: &mut App) {
    app.add_plugins(
        ProgressPlugin::new(AppState::Loading)
            .continue_to(AppState::Playing)
            .track_assets(),
    )
    .add_loading_state(LoadingState::new(AppState::Loading).load_collection::<GameAssets>())    
    .add_systems(Startup, open) // have to use startup here, OnEnter(AppState::Loading) fires before startup
    .add_systems(
        Update,
        update_loading
            .after(LoadingStateSet(AppState::Loading))
            .run_if(in_state(AppState::Loading)),
    );
}


fn open(mut commands: Commands, root: Query<Entity, With<UiMainRootNode>>) {

    commands.spawn((
        Camera3dBundle {
            transform: Transform::from_translation(Vec3::new(0.0, 0.0, 5.0)),
            ..Default::default()
        },
        StateScoped(AppState::Loading)
    ));

    let Ok(root) = root.get_single() else {
        panic!("Failed to get root node");
    };
    let font = Handle::<Font>::default();
    commands.ui_builder(root)
        .column(|column| {
            column
                .style()
                .width(Val::Percent(100.))
                .align_items(AlignItems::Center)
                .justify_content(JustifyContent::Center);

            // Using defualt font
            column.spawn((
                LoadingText,
                TextBundle::from_section(
                    "Loading",
                    TextStyle {
                        font: font.clone(),
                        font_size: 50.0,
                        color: Color::WHITE,
                    },
                ),
            ));

            // Progress bar
            column.container(
                (
                    NodeBundle {
                        style: Style {
                            width: Val::Percent(50.),
                            height: Val::Percent(10.),
                            ..default()
                        },
                        ..default()
                    },
                    Outline {
                        color: css::WHITE.into(),
                        width: Val::Px(5.),
                        ..default()
                    },
                ),
                |container| {
                    container.style().background_color(Color::BLACK.into());

                    container
                        .spawn((
                            LoadingBar,
                            NodeBundle {
                                style: Style {
                                    width: Val::Percent(0.),
                                    height: Val::Percent(100.),
                                    ..default()
                                },
                                ..default()
                            },
                        ))
                        .style()
                        .background_color(css::GRAY.into());
                },
            );
        })
        .insert((
            Name::new("LoadingScreen"),
            StateScoped(AppState::Loading)
        ));
}

#[derive(Component)]
pub struct LoadingText;

#[derive(Component)]
pub struct LoadingBar;

fn update_loading(
    mut cmd: Commands,
    progress: Option<Res<ProgressCounter>>,
    mut texts: Query<&mut Text, With<LoadingText>>,
    bars: Query<Entity, With<LoadingBar>>,
    _diagnostics: Res<DiagnosticsStore>,
    mut last_done: Local<u32>,
) {
    if let Some(progress) = progress.map(|counter| counter.progress()) {
        if progress.done > *last_done {
            *last_done = progress.done;

            let mut complete = progress.done as f32 / progress.total as f32;
            complete *= 100.0;
            complete = complete.min(99.0).max(0.0);

            let mut text = texts.single_mut();
            text.sections[0].value = format!("Loading: {:.0}%", complete);

            let bar = bars.single();
            cmd.ui_builder(bar).style().width(Val::Percent(complete));
        }
    }
}
