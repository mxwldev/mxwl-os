# mxwl OS

A user-local desktop profile for **Pop!_OS 24.04 with COSMIC**, matching
`mxwl-editor`: charcoal backgrounds, muted green accents, compact borders,
Space Grotesk UI text and IBM Plex Mono controls and terminals.

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

Both repositories are private. Your GitHub account needs read access to
[`mxwldev/mxwl-os`](https://github.com/mxwldev/mxwl-os) and
[`KerryRitter/cosmic-window-list`](https://github.com/KerryRitter/cosmic-window-list).
Authenticate Git before cloning; with GitHub CLI, use `gh auth login` and
`gh auth setup-git`. SSH clones work too: the script reuses SSH for Window List
without changing your global Git configuration.

Check prerequisites and repository access without installing anything:

```sh
./install.sh --check
```

If build dependencies are already installed or managed separately:

```sh
./install.sh --skip-system-packages
```

The same script works for updates: run `git pull --ff-only`, then `./install.sh`.
Existing tile colors, font size, padding and panel height are preserved when
updating an installed profile. Already installed, unmodified Window List files
are reused at the required version.

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

Colors come from [brand.json](brand.json), copied from
`../mxwl-editor/src/shared/brand.json`. The editor itself is not modified.

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
cd ~/Workspaces/mxwl/mxwl-os
./mxwl-os build
./mxwl-os apply --dry-run
./mxwl-os status
```

Theme output is written to this project's `build/` directory and exported themes
in `themes/`; fetched dependencies use the caches described below.
View `build/data/backgrounds/mxwl/mxwl-grid.png` for the wallpaper.
The native theme is generated and read back using the same library family as
COSMIC Settings. Both v1 and v2 config files are included for the mixed versions
of COSMIC applications shipped on this machine.

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
cd ~/Workspaces/mxwl/mxwl-os
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
All writes stay in those user directories. System login/boot screens, proprietary
application themes and sandboxed apps with their own appearance settings may
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
optional panel controls. Applying this full profile reapplies its mxwl preset.
The compact preset uses 14 px labels, 6 px horizontal and 2 px vertical tile
padding, 2 px gaps and an XS panel with zero outer padding. Adjust **Label font
size**, **Tile horizontal/vertical padding** and **Panel height** in that window.
Choose **Background color** and **Foreground color** to style window tiles, or
their **Active** counterparts for the focused window. **Panel background color**
has its own color picker and hex input. Close and reopen settings after updating
if an already open settings window still shows the previous controls.

Native theme-builder source and dependency lockfile are in `theme-builder/`.
Font provenance and checksums are in `assets/fonts/sources.json`.

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
installed files and recovery from an interrupted write.

Native configuration and exports use
[System76's cosmic-theme](https://github.com/pop-os/libcosmic/tree/511384f6206527cf87369da67a9164831afbabef/cosmic-theme).
See also [System76's overview of native COSMIC theming](https://system76.com/blog/post/customizing-cosmic-theming-and-applications).

mxwl-os code is [MIT licensed](LICENSE). The separately installed
[COSMIC Window List](https://github.com/KerryRitter/cosmic-window-list) is
GPL-3.0-only; native COSMIC libraries and bundled fonts retain their own licenses.
