use cosmic_config::{Config, CosmicConfigEntry};
use cosmic_theme::{CornerRadii, Theme, ThemeBuilder};
use cosmic_theme::palette::{Srgb, Srgba};
use serde_json::{Value, json};
use std::{error::Error, fs, path::PathBuf};

fn rgb(value: &str) -> Srgb {
    let n = u32::from_str_radix(value.trim_start_matches('#'), 16).expect("hex brand color");
    Srgb::new((n >> 16) as u8 as f32 / 255., (n >> 8) as u8 as f32 / 255., n as u8 as f32 / 255.)
}
fn rgba(value: &str) -> Srgba {
    let c = rgb(value); Srgba::new(c.red, c.green, c.blue, 1.)
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args().collect();
    let brand: Value = serde_json::from_str(&fs::read_to_string(args.get(1).ok_or("brand.json required")?)?)?;
    let output = PathBuf::from(args.get(2).ok_or("output directory required")?);
    fs::create_dir_all(&output)?;
    let color = |key: &str| brand[key].as_str().expect("brand color");
    let mut builder = ThemeBuilder::dark();
    builder.palette.as_mut().name = "mxwl".into();
    builder.bg_color = Some(rgba(color("background")));
    builder.primary_container_bg = Some(rgba(color("surface")));
    builder.secondary_container_bg = Some(rgba(color("elevated")));
    builder.accent = Some(rgb(color("accent")));
    builder.success = Some(rgb(color("accent")));
    builder.warning = Some(rgb(color("peach")));
    builder.destructive = Some(rgb(color("error")));
    builder.window_hint = Some(rgb(color("accent")));
    let number = |key: &str, default: u32| brand[key].as_u64().map(|n| n as u32).unwrap_or(default);
    builder.gaps = (number("outer_gap", 4), number("inner_gap", 4));
    builder.active_hint = number("active_hint", 1);
    let radius = number("corner_radius", 2) as f32;
    builder.corner_radii = CornerRadii {
        radius_0: [0.; 4], radius_xs: [(radius - 2.).max(0.); 4], radius_s: [(radius - 2.).max(0.); 4],
        radius_m: [radius; 4], radius_l: [radius * 2.; 4], radius_xl: [160.; 4],
    };
    let pretty = ron::ser::PrettyConfig::default();
    let theme_ron = ron::ser::to_string_pretty(&builder, pretty.clone())?;
    // Validate the same file that users import through COSMIC Appearance.
    let builder: ThemeBuilder = ron::from_str(&theme_ron)?;
    fs::write(output.join("mxwl.ron"), theme_ron)?;
    let mut value = serde_json::to_value(builder.clone().build())?;
    value["name"] = json!("mxwl");
    for layer in ["background", "primary", "secondary", "transparent_background", "transparent_primary", "transparent_secondary"] {
        value[layer]["on"] = json!(format!("{}ff", color("foreground")));
        value[layer]["divider"] = json!(format!("{}ff", color("line")));
        value[layer]["component"]["on"] = json!(format!("{}ff", color("foreground")));
        value[layer]["component"]["selected_text"] = json!(format!("{}ff", color("accentHover")));
        value[layer]["component"]["focus"] = json!(format!("{}ff", color("accent")));
        value[layer]["component"]["border"] = json!(format!("{}ff", color("line")));
        value[layer]["component"]["on_disabled"] = json!(format!("{}ff", color("muted")));
        value[layer]["component"]["disabled_border"] = json!(format!("{}ff", color("faint")));
    }
    for component in ["accent", "accent_button", "success", "success_button"] {
        value[component]["on"] = json!(format!("{}ff", color("accentInk")));
        value[component]["hover"] = json!(format!("{}ff", color("accentHover")));
    }
    let theme: Theme = serde_json::from_value(value)?;
    builder.write_entry(&Config::with_custom_path("com.system76.CosmicTheme.Dark.Builder", ThemeBuilder::VERSION, output.join("config"))?)?;
    let config = Config::with_custom_path("com.system76.CosmicTheme.Dark", Theme::VERSION, output.join("config"))?;
    theme.write_entry(&config)?;
    let _ = Theme::get_entry(&config).map_err(|(errors, _)| format!("Theme readback failed: {errors:?}"))?;
    fs::write(output.join("mxwl-resolved.ron"), ron::ser::to_string_pretty(&theme, pretty)?)?;
    // XDG paths are set to build/ by build.py; exports never touch the live desktop.
    theme.write_exports()?;
    println!("Generated and validated mxwl COSMIC v{} theme and GTK/Qt exports.", Theme::VERSION);
    Ok(())
}
