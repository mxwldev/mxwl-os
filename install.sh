#!/usr/bin/env bash
# Bootstrap a cloned mxwl-os checkout, then install its required applet and theme.
set -euo pipefail

mxwl_project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mxwl_check_only=false
mxwl_skip_packages=false
mxwl_install_args=()
mxwl_rustup_script=''

usage() {
    cat <<'EOF'
Usage: ./install.sh [--check] [--skip-system-packages] [--window-list PATH]

Install mxwl OS on Pop!_OS 24.04 with COSMIC. Run as your normal desktop user.
System packages use sudo; Rust, Window List and the theme install for this user.

  --check                 Check prerequisites and repository access without installing.
  --skip-system-packages  Use existing build dependencies instead of installing apt packages.
  --window-list PATH      Use a local Window List development checkout.
  -h, --help              Show this help.
EOF
}

fail() { printf 'mxwl-os: %s\n' "$*" >&2; exit 1; }
cleanup() {
    if [[ -n "$mxwl_rustup_script" ]]; then rm -f -- "$mxwl_rustup_script"; fi
}
trap cleanup EXIT

while (( $# )); do
    case "$1" in
        --check) mxwl_check_only=true; shift ;;
        --skip-system-packages) mxwl_skip_packages=true; shift ;;
        --window-list)
            (( $# >= 2 )) || fail '--window-list requires a checkout path.'
            mxwl_install_args+=(--window-list "$2"); shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; fail "Unknown option: $1" ;;
    esac
done

[[ "$EUID" -ne 0 ]] || fail 'Run this script as your normal user, without sudo.'
[[ -r /etc/os-release ]] || fail 'Cannot identify this operating system.'
# shellcheck source=/dev/null
. /etc/os-release
[[ "${ID:-}" == pop && "${VERSION_ID:-}" == 24.04 ]] || fail 'This installer supports Pop!_OS 24.04.'
mxwl_desktop="${XDG_CURRENT_DESKTOP:-}"
[[ "${mxwl_desktop^^}" == *COSMIC* ]] || fail 'Run this script from a terminal in your COSMIC session.'
[[ -f "$mxwl_project_dir/mxwl-os" && -f "$mxwl_project_dir/dependencies.json" ]] || fail 'Run install.sh from a complete mxwl-os checkout.'

mxwl_packages=(
    build-essential pkg-config git curl ca-certificates python3 python3-cairo
    python3-gi gir1.2-gtk-3.0 fontconfig libxkbcommon-dev libwayland-dev
    libfontconfig-dev libfreetype-dev libdbus-1-dev libudev-dev
)
mxwl_missing_packages=()
if ! "$mxwl_skip_packages"; then
    for mxwl_package in "${mxwl_packages[@]}"; do
        if [[ "$(dpkg-query -W -f='${db:Status-Status}' "$mxwl_package" 2>/dev/null || true)" != installed ]]; then
            mxwl_missing_packages+=("$mxwl_package")
        fi
    done
    if (( ${#mxwl_missing_packages[@]} )); then
        printf 'Missing system packages: %s\n' "${mxwl_missing_packages[*]}"
        if ! "$mxwl_check_only"; then
            command -v sudo >/dev/null || fail 'sudo is required to install system packages.'
            sudo apt-get update
            sudo apt-get install -y -- "${mxwl_missing_packages[@]}"
        fi
    else
        printf 'System packages are installed.\n'
    fi
fi

export PATH="$HOME/.cargo/bin:$PATH"
rust_ready() {
    command -v cargo >/dev/null && command -v rustc >/dev/null || return 1
    local mxwl_version
    mxwl_version="$(rustc --version | awk '{print $2}')"
    # This is the toolchain family used to verify the pinned COSMIC sources.
    [[ "$(printf '%s\n' '1.99.0' "$mxwl_version" | sort -V | head -n 1)" == 1.99.0 ]]
}
if ! rust_ready; then
    if "$mxwl_check_only"; then
        printf 'A current Rust toolchain (1.99 or newer) is required.\n'
        exit 1
    fi
    printf 'Installing the current stable Rust toolchain…\n'
    if command -v rustup >/dev/null; then
        rustup toolchain install stable --profile minimal
    else
        command -v curl >/dev/null || fail 'curl is required to install Rust.'
        mxwl_rustup_script="$(mktemp -t mxwl-rustup.XXXXXX)"
        curl --fail --show-error --silent --proto '=https' --tlsv1.2 \
            https://sh.rustup.rs -o "$mxwl_rustup_script"
        sh "$mxwl_rustup_script" -y --profile minimal --default-toolchain stable --no-modify-path
    fi
    export RUSTUP_TOOLCHAIN=stable
    rust_ready || fail 'The stable Rust toolchain does not meet the required version (1.99 or newer).'
fi
printf 'Rust: %s\n' "$(rustc --version)"

command -v git >/dev/null || fail 'Git is missing. Rerun without --skip-system-packages.'
[[ -x /usr/bin/python3 ]] || fail 'Python 3 is missing.'
/usr/bin/python3 -c 'import cairo, gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' \
    || fail 'Python GTK/Cairo dependencies are missing. Rerun without --skip-system-packages.'

if (( ${#mxwl_install_args[@]} == 0 )); then
    mxwl_dependency_url="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["cosmic-window-list"]["repository"])' "$mxwl_project_dir/dependencies.json")"
    # Both repositories are public. Use the dependency's HTTPS URL regardless
    # of how this checkout was cloned; GitHub authentication is not required.
    git ls-remote "$mxwl_dependency_url" HEAD >/dev/null \
        || fail 'Cannot reach KerryRitter/cosmic-window-list over HTTPS. Check your network and Git configuration, then rerun.'
    printf 'Window List repository access verified.\n'
else
    /usr/bin/python3 - "$mxwl_project_dir" "${mxwl_install_args[1]}" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1])/'scripts'))
from dependencies import validate_source
validate_source(Path(sys.argv[2]).expanduser().resolve())
PY
    printf 'Local Window List checkout verified.\n'
fi

if "$mxwl_check_only"; then
    (( ${#mxwl_missing_packages[@]} == 0 )) || fail 'Install the missing packages by running ./install.sh.'
    printf 'Checks passed. Run ./install.sh to install Window List and the mxwl desktop profile.\n'
    exit 0
fi

printf 'Installing Window List and applying the mxwl desktop profile…\n'
cd -- "$mxwl_project_dir"
/usr/bin/python3 "$mxwl_project_dir/mxwl-os" install "${mxwl_install_args[@]}"
printf '\nmxwl OS is installed. Open "mxwl OS Appearance" to choose this machine\047s accent color.\n'
