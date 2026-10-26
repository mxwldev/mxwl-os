# mxwl OS

A desktop profile for **Pop!_OS 24.04 with COSMIC**: charcoal backgrounds,
per-machine accent colors, compact panels, a taskbar-style window list,
Space Grotesk UI text and IBM Plex Mono controls and terminals. It installs
into your existing desktop account and includes backup and restore support.

The visual defaults match `mxwl-editor`, but this repository contains everything
needed to build and install the profile independently.

- [Install](#quick-install)
- [Features](#included)
- [Customize colors and the panel](#customize)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Update](#update)
- [Command reference](#command-reference)
- [Backups and restore](#apply-and-restore)
- [Installed files](#installed-files)
- [Troubleshooting](#troubleshooting)
- [Development and validation](#validation)

## Compatibility and requirements

- **Pop!_OS 24.04**, logged into a **COSMIC Wayland session**. The bootstrap
  checks the operating system, version and desktop before installing.
- **Git** to clone this repository, an internet connection for packages and
  source dependencies, and `sudo` access to install missing system packages.
- A normal desktop user account. Run `./install.sh` without `sudo`; it requests
  elevation only for the system package step.
- A current Rust toolchain. The installer checks for Rust **1.99 or newer** and
  installs the stable toolchain when necessary.

COSMIC Window List and the native theme library are pinned to specific source
revisions. Other Linux distributions and COSMIC versions have not been verified.

## Quick install

From a terminal in **Pop!_OS 24.04 with COSMIC**:

```sh
git clone https://github.com/mxwldev/mxwl-os.git
cd mxwl-os
./install.sh
```

Run the script as your normal user. It automatically:

1. Installs missing system/build packages through `sudo apt-get`.
2. Installs a current stable Rust toolchain if needed.
3. Downloads, builds, installs and enables the required **COSMIC Window List**.
4. Installs fonts, icons and wallpaper, backs up your settings and applies mxwl.

There is no separate Window List installation step. The first build can take
several minutes. Open **mxwl OS Appearance** afterward to pick a machine color.

Both this repository and the required
[COSMIC Window List](https://github.com/KerryRitter/cosmic-window-list) dependency
are public. GitHub authentication is not required. Window List is fetched over
HTTPS, including when your mxwl-os checkout uses an SSH remote.

Check prerequisites and repository access without installing anything:

```sh
./install.sh --check
```

If build dependencies are already installed or managed separately:

```sh
./install.sh --skip-system-packages
```

### After installation

1. Press **Alt+Space** to open the COSMIC launcher.
2. Open **mxwl OS Appearance** to choose an accent for this machine.
3. Right-click a window-list button and open **Window List Settings** to adjust
   grouping, monitor filtering, panel icons and button appearance.
4. Reopen any applications that retain their previous fonts or colors. Logging
   out and back in refreshes the whole session when needed.

## Included

| Component | What changes |
| --- | --- |
| COSMIC desktop and apps | Native dark theme, green highlights, small corner radii, thin active-window hint and compact window gaps |
| Panel and applets | Charcoal panel, compact spacing, launcher icon and mxwl window-list buttons; existing applet layout and monitor assignments are preserved |
| GTK 3 / GTK 4 | Native COSMIC color export, dark preference, UI font and icons |
| Qt / KDE | Native COSMIC palette, qt5ct/qt6ct color configuration and kdeglobals colors |
| COSMIC Terminal | mxwl ANSI colors, cursor color and IBM Plex Mono; existing color schemes and profiles are preserved |
| Fonts | Space Grotesk, IBM Plex Mono regular/medium, Pixelify Sans; pinned font files, SHA-256 checksums and OFL licenses |
| Icons | mxwl folder icons, inheriting the installed Cosmic, Adwaita and hicolor app/symbolic icons |
| Wallpaper | 4K charcoal grid with no logo or text, PNG and SVG |
| Keyboard shortcuts | Alt+Space opens the COSMIC launcher; other custom shortcuts are preserved |

Window List shows live window titles and icons, restores or focuses windows on
click, minimizes an active window when clicked again, and supports middle-click
to close an individual window. By default, each panel shows windows on its own
monitor. Up to five windows of an app remain separate; the sixth combines them
into a counted button with a window picker. Grouping and monitor filtering can
be changed in its settings.

Colors come from [brand.json](brand.json). Machine-specific overrides are stored
in your user configuration rather than committed to the shared palette.

## Installer details

**COSMIC Window List is required and installed automatically.** The installer
fetches the exact commit in `dependencies.json`, builds the applet, installs its
settings application, enables it in the panel, then builds and applies mxwl.
Existing panel icons and other applets are preserved. Later applications check
the installed revision and file hashes, reinstalling the dependency when needed.

`install.sh` handles these prerequisites automatically. If an administrator
prefers to install packages separately, the equivalent commands are:

```sh
sudo apt update
sudo apt install build-essential pkg-config git curl ca-certificates python3 python3-cairo python3-gi \
  gir1.2-gtk-3.0 fontconfig libxkbcommon-dev libwayland-dev libfontconfig-dev \
  libfreetype-dev libdbus-1-dev libudev-dev
```

A current stable Cargo/Rust toolchain is also required. The bootstrap checks for
Rust 1.99 or newer, the toolchain family used to verify the pinned COSMIC sources.
When needed, it installs Rust through the official `https://sh.rustup.rs`
installer, using the minimal profile and leaving shell startup files alone.

The lower-level installer is available when prerequisites are already managed:

```sh
./mxwl-os install
```

Run either installer as your normal user in a COSMIC session. No sudo is used after
system prerequisites are installed. It replaces App Tray in its existing panel
slot, or adds Window List when no taskbar slot exists. The native COSMIC applets
already installed with Pop!_OS inherit the theme; no GNOME extensions are needed.

## Build and preview

The first build fetches the pinned Window List source, native COSMIC theme library
and Cargo dependencies. The font files are included. Previewing does not install
the applet or change the live desktop:

```sh
# Run these commands from your cloned mxwl-os directory.
./mxwl-os build
./mxwl-os apply --dry-run
./mxwl-os status
```

Theme output is written to this project's `build/` directory and exported themes
in `themes/`; fetched dependencies use the caches described below.
View `build/data/backgrounds/mxwl/mxwl-grid.png` for the wallpaper.
The native theme is generated and read back using the same library family as
COSMIC Settings. Both v1 and v2 config files are included for the mixed versions
of COSMIC applications shipped with the supported desktop.

The source is cached in `~/.cache/mxwl-os/dependencies/`. An existing clean
`~/Workspaces/cosmic-window-list` checkout at the required commit is reused when
mxwl-os is checked out at `~/Workspaces/mxwl/mxwl-os`.
For development, use an explicit local checkout:

```sh
./mxwl-os build --window-list /path/to/cosmic-window-list
./mxwl-os install --window-list /path/to/cosmic-window-list
./install.sh --window-list /path/to/cosmic-window-list
```

## Apply and restore

Run from your normal COSMIC session:

```sh
# Run from your cloned mxwl-os directory.
./mxwl-os apply
```

`apply` also enforces the Window List dependency before changing the desktop.
`apply --dry-run` only previews theme files and never installs dependencies.

The installer previews and validates every target before writing, snapshots
existing files and symlinks, applies writes atomically, and refreshes font/icon
caches. Repeating `apply` is safe. Backups are stored in
`~/.local/state/mxwl-os/backups/`, including a manifest recording files that did
not previously exist. Failed writes trigger rollback. GTK and Qt INI settings
are merged, and existing terminal color schemes are retained.

The desktop normally reloads its native configuration. Restart an already open
app if it keeps cached fonts, icons or colors; a new login refreshes the entire
session. The profile does not restart applications or change their running work.

Restore the desktop from before mxwl, or specify an individual backup directory.
The original baseline also covers files introduced by later profile updates:

```sh
./mxwl-os restore
./mxwl-os restore ~/.local/state/mxwl-os/backups/20261026-123456-000000
```

The installer respects `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and `XDG_STATE_HOME`.
Profile settings and assets stay in those user directories. System login/boot
screens, proprietary application themes and sandboxed apps with their own appearance settings may
need separate integration. Qt apps must use a platform theme that reads the
generated palette (COSMIC's Qt integration, KDE, qt5ct or qt6ct).

The Window List applet installs its executable under `~/.local/bin` and its
settings and desktop registrations under `~/.local/share`, matching that
project's installer. Restoring the mxwl profile restores the previous panel
layout and theme; the separately installed Window List applet remains available.

To import only the colors manually, use `themes/mxwl.ron` in
**COSMIC Settings → Desktop → Appearance → Import**, or import
`themes/mxwl-terminal.ron` in COSMIC Terminal's color-scheme settings.

## Customize

Open **mxwl OS Appearance** from the launcher, or run `./mxwl-os settings`, to
choose a machine accent with the color picker, a hex value or color presets.
The color updates native COSMIC highlights, active window tiles, terminal colors
and folder icons together. Font size, tile padding and panel height remain as
you set them when changing the accent.

The CLI supports the same per-machine setting:

```sh
./mxwl-os accent '#8ccfe5'
./mxwl-os accent
```

The preference is stored in `~/.config/mxwl-os/machine.json`, so each machine can
use a different color without editing the shared brand palette.

Edit `brand.json` and rerun `build` to generate desktop colors and wallpaper.
Button colors and geometry are configured independently through **Window List
Settings → Appearance**, with mxwl and System presets, a color preview and
optional panel controls. Fresh installations start with the mxwl preset;
updates through `./install.sh` preserve your current tile colors and dimensions.
The compact preset uses 14 px labels, 6 px horizontal and 2 px vertical tile
padding, 2 px gaps and an XS panel with zero outer padding. Adjust **Label font
size**, **Tile horizontal/vertical padding** and **Panel height** in that window.
Choose **Background color** and **Foreground color** to style window tiles, or
their **Active** counterparts for the focused window. **Panel background color**
has its own color picker and hex input. Close and reopen settings after updating
if an already open settings window still shows the previous controls.

Native theme-builder source and dependency lockfile are in `theme-builder/`.
Font provenance and checksums are in `assets/fonts/sources.json`.

## Keyboard shortcuts

**Alt+Space opens the COSMIC launcher**, so you can find and open applications
without reaching for the Super/Windows key. This works on the laptop keyboard
and external keyboards, including keyboards whose left Windows position is Fn.

The installer merges this binding into COSMIC's existing custom shortcuts.
An existing Alt+Space binding is replaced by the launcher action; other custom
shortcuts are retained. The original shortcut file is included in the backup.

To choose a different shortcut after installation, use
**COSMIC Settings → Input Devices → Keyboard → Keyboard Shortcuts**. The mxwl
Alt+Space binding is reapplied when you next apply the profile. To change the
shared default, edit [scripts/shortcuts.py](scripts/shortcuts.py), rebuild and apply.

## Update

From your cloned mxwl-os directory:

```sh
git pull --ff-only
./install.sh
```

The installer checks the pinned Window List revision and installed file hashes.
It reuses an intact installation or rebuilds it when necessary, then rebuilds
and applies the profile with a new backup. Existing tile colors, font size,
padding and panel height are preserved on updates. Machine accents remain in
your local configuration.

Use `./install.sh --skip-system-packages` if your administrator manages build
dependencies. This still checks Rust and the Python GTK/Cairo dependencies.

## Command reference

Run commands from your cloned mxwl-os directory. `./mxwl-os --help` and each
subcommand's `--help` show the available options.

| Command | Purpose |
| --- | --- |
| `./install.sh` | Install prerequisites, required Window List and the profile |
| `./install.sh --check` | Check compatibility, dependencies and source access without installing |
| `./install.sh --skip-system-packages` | Install with system packages managed separately |
| `./install.sh --window-list /path/to/checkout` | Install using a local Window List development checkout |
| `./mxwl-os install` | Build and install without the system-package/Rust bootstrap |
| `./mxwl-os build` | Generate the theme bundle and exports without changing desktop settings |
| `./mxwl-os apply --dry-run` | List pending changes from an existing build without applying them |
| `./mxwl-os apply` | Verify the applet dependency and apply the current build with backups |
| `./mxwl-os status` | Report the profile, accent, applet readiness, pending files and resolved fonts |
| `./mxwl-os settings` | Open the machine accent picker |
| `./mxwl-os accent` | Print the effective accent color |
| `./mxwl-os accent '#8ccfe5'` | Save and apply this machine's accent |
| `./mxwl-os restore` | Restore the original desktop baseline |
| `./mxwl-os restore /path/to/backup` | Restore one particular apply transaction |

`build`, `install` and `apply` also accept `--window-list /path/to/checkout`.
An initial build is required before previewing changes or reporting pending files.

## Installed files

Default locations are below. Profile configuration, data, state and dependency
cache locations follow `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME` and
`XDG_CACHE_HOME` when set. The Window List executable and settings application
use that project's home-directory install locations.

| Location | Contents |
| --- | --- |
| `~/.config/cosmic/` | Native theme, fonts, panel, terminal, wallpaper and shortcut preferences |
| `~/.config/gtk-3.0/`, `~/.config/gtk-4.0/` | GTK settings and native COSMIC CSS exports |
| `~/.config/qt5ct/`, `~/.config/qt6ct/`, `~/.config/kdeglobals` | Qt/KDE palette integration |
| `~/.config/mxwl-os/machine.json` | This machine's chosen accent |
| `~/.config/mxwl-os/profile.json` | Applied profile and resolved brand colors |
| `~/.local/share/fonts/mxwl/` | Bundled fonts and licenses |
| `~/.local/share/icons/mxwl/` | Folder icons and inherited icon-theme definition |
| `~/.local/share/backgrounds/mxwl/` | Generated wallpaper |
| `~/.local/share/applications/io.github.kerry.MxwlOSAppearance.desktop` | Accent-picker launcher registration |
| `~/.local/share/color-schemes/` | Native COSMIC Qt color export |
| `~/.local/bin/cosmic-window-list` | Window List applet executable |
| `~/.local/bin/cosmic-window-list-settings` | Window List settings launcher |
| `~/.local/share/cosmic-window-list/` | Window List settings and appearance code |
| `~/.local/state/mxwl-os/` | Backups, baseline/latest markers and dependency installation record |
| `~/.cache/mxwl-os/dependencies/` | Pinned Window List source checkout |
| `build/` in this checkout | Generated configuration, assets and install manifest |

## Uninstall or return to the previous desktop

```sh
./mxwl-os restore
```

This restores files and symlinks recorded in the original baseline and removes
profile files that did not exist before installation. Individual backup paths
restore the state immediately before that apply transaction instead.

Restore before deleting the checkout or the backups. Restoration leaves the
separately installed Window List applet, build tools, Rust toolchain and saved
machine accent available. To remove the applet too, follow its
[uninstall instructions](https://github.com/KerryRitter/cosmic-window-list#uninstall-or-switch-back).

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| The installer asks for a COSMIC session or rejects the OS | Run from a normal-user terminal in Pop!_OS 24.04's COSMIC session. Check `echo "$XDG_CURRENT_DESKTOP"` and `cat /etc/os-release`. |
| Missing packages or Python GTK/Cairo errors | Run `./install.sh` without `--skip-system-packages`, or install the packages in [Installer details](#installer-details) through your administrator. |
| Rust is too old | Run `./install.sh` to install current stable Rust, then retry. The bootstrap requires 1.99 or newer. |
| Source downloads fail | Check network access to GitHub, the Rust package registry and your OS package mirrors. Both project repositories are public; the documented HTTPS clone needs no GitHub login. |
| `Permission denied (publickey)` | Check for a Git URL rewrite with `git config --show-origin --get-regexp '^url\..*\.insteadof$'`. Remove or adjust an unintended HTTPS-to-SSH rewrite in the configuration it identifies. |
| `Run ./mxwl-os build first` | Run `./mxwl-os build` before `status` or `apply --dry-run`, or use `./install.sh` for the complete install. |
| Cached Window List source has local edits | Use `--window-list /path/to/your/checkout` for development, or move the edited cache checkout aside before retrying. |
| A new font, icon or theme is not visible | Reopen the affected app; log out and back in if the whole session needs refreshing. Use `fc-match 'Space Grotesk'` and `fc-match 'IBM Plex Mono'` to inspect font resolution. |
| A Qt or sandboxed app retains its old colors | Verify that the app uses COSMIC's Qt integration, KDE, qt5ct or qt6ct. App-specific themes may require separate configuration. |
| Alt+Space opens something else | Reapply the profile and inspect COSMIC's keyboard shortcuts. An app may also reserve the shortcut while it has focus. |
| Restore does not remove Window List | The applet is installed separately; follow its uninstall instructions after restoring the profile. |

For a bug report, include the failing command, its output, your Pop!_OS and
COSMIC versions, and whether you used `--window-list`. Open an
[issue](https://github.com/mxwldev/mxwl-os/issues) with those details.

## Validation

```sh
./mxwl-os build
/usr/bin/python3 -m unittest discover -s tests -v
bash -n install.sh
./install.sh --check
./mxwl-os apply --dry-run
```

Tests use temporary XDG directories and cover INI merging, retaining terminal
schemes, idempotent installation, exact file/symlink restoration, removing newly
installed files and recovery from an interrupted write. Shortcut updates merge
Alt+Space into the existing custom map and participate in backup and restore.

Native configuration and exports use
[System76's cosmic-theme](https://github.com/pop-os/libcosmic/tree/511384f6206527cf87369da67a9164831afbabef/cosmic-theme).
See also [System76's overview of native COSMIC theming](https://system76.com/blog/post/customizing-cosmic-theming-and-applications).

## License and upstream projects

mxwl-os code is [MIT licensed](LICENSE). The separately installed
[COSMIC Window List](https://github.com/KerryRitter/cosmic-window-list) is
GPL-3.0-only; native COSMIC libraries and bundled fonts retain their own licenses.
