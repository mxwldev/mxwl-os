#!/usr/bin/env python3
"""Generate native COSMIC, toolkit and desktop assets without changing the session."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'build'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def legacy_colors(text, rgb_only=False):
    def convert(match):
        channels = [int(match[1][i:i+2], 16)/255 for i in (0, 2, 4, 6)]
        fields = ('red', 'green', 'blue') if rgb_only else ('red', 'green', 'blue', 'alpha')
        return '('+', '.join(f'{k}: {v:.8f}' for k, v in zip(fields, channels))+')'
    return re.sub(r'"#([0-9a-fA-F]{8})"', convert, text)


def machine_path():
    return Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'mxwl-os/machine.json'


def read_machine():
    path=machine_path()
    return json.loads(path.read_text()) if path.exists() else {}


def effective_brand(machine=None):
    brand=json.loads((ROOT/'brand.json').read_text())
    machine=read_machine() if machine is None else machine
    if 'accent' in machine:
        accent=machine['accent']
        if not isinstance(accent,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',accent):
            raise ValueError('Machine accent must be a six-digit hex color, e.g. #8ccfe5.')
        rgb=tuple(int(accent[i:i+2],16) for i in (1,3,5))
        brand['accent']=accent.lower()
        brand['accentHover']='#%02x%02x%02x' % tuple(round(v+(255-v)*.25) for v in rgb)
        brand['accentInk']='#%02x%02x%02x' % tuple(round(v*.15) for v in rgb)
    return brand


def wallpaper(brand):
    import cairo
    dest = BUILD/'data/backgrounds/mxwl'
    dest.mkdir(parents=True, exist_ok=True)
    def draw(cr):
        def color(hex_color, alpha=1):
            cr.set_source_rgba(*(int(hex_color[i:i+2],16)/255 for i in (1,3,5)),alpha)
        color(brand['background']); cr.paint()
        color(brand['line'], .24); cr.set_line_width(1)
        for x in range(0,3840,64): cr.move_to(x+.5,0); cr.line_to(x+.5,2160)
        for y in range(0,2160,64): cr.move_to(0,y+.5); cr.line_to(3840,y+.5)
        cr.stroke()
    surface=cairo.ImageSurface(cairo.FORMAT_RGB24,3840,2160)
    draw(cairo.Context(surface)); surface.write_to_png(str(dest/'mxwl-grid.png'))
    surface=cairo.SVGSurface(str(dest/'mxwl-grid.svg'),3840,2160)
    draw(cairo.Context(surface)); surface.finish()
    # COSMIC caches decoded wallpaper paths; a content-based name reloads edits.
    name='mxwl-grid-'+hashlib.sha256((dest/'mxwl-grid.png').read_bytes()).hexdigest()[:12]+'.png'
    shutil.copy2(dest/'mxwl-grid.png',dest/name)
    return name


def build(window_list=None,preserve_layout=False):
    from dependencies import source, panel_layout, requirement
    window_list=source(window_list)
    brand=effective_brand()
    for item in json.loads((ROOT/'assets/fonts/sources.json').read_text()):
        if hashlib.sha256((ROOT/item['file']).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Font checksum mismatch: '+item['file'])
    if BUILD.exists(): shutil.rmtree(BUILD)
    (BUILD/'config').mkdir(parents=True); (BUILD/'data').mkdir()
    write(BUILD/'brand.json',json.dumps(brand,indent=2)+'\n')
    cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
    subprocess.run([cargo,'build','--locked','--manifest-path',str(ROOT/'theme-builder/Cargo.toml')],check=True)
    env={**os.environ,'XDG_CONFIG_HOME':str(BUILD/'config'),'XDG_DATA_HOME':str(BUILD/'data')}
    subprocess.run([str(ROOT/'theme-builder/target/debug/mxwl-theme-builder'),str(BUILD/'brand.json'),str(BUILD)],env=env,check=True)
    # Several Pop!_OS packages still consume v1 while newer libcosmic apps use v2.
    cosmic=BUILD/'config/cosmic'
    rgb_keys={'accent','success','warning','destructive','text_tint','neutral_tint','window_hint'}
    for name in ('com.system76.CosmicTheme.Dark','com.system76.CosmicTheme.Dark.Builder'):
        for source in (cosmic/name/'v2').iterdir():
            if (Path('/usr/share/cosmic')/name/'v1'/source.name).is_file():
                write(cosmic/name/'v1'/source.name,legacy_colors(source.read_text(),name.endswith('Builder') and source.name in rgb_keys))
        write(cosmic/name/'v1/is_frosted','false\n')
        # Newer distro applications require this field even when blur is disabled.
        write(cosmic/name/'v2/frosted_maximized_apps','false\n')
    def config(name,key,value): write(cosmic/name/'v1'/key,value+'\n')
    config('com.system76.CosmicTheme.Mode','auto_switch','false')
    config('com.system76.CosmicTheme.Mode','is_dark','true')
    config('com.system76.CosmicTk','apply_theme_global','true')
    config('com.system76.CosmicTk','icon_theme','"mxwl"')
    # COSMIC defaults to text buttons at XS; retain icons on the compact panel.
    config('com.system76.CosmicPanelButton','configs',
           '{"Panel": (force_presentation: Some(Icon)), "Dock": (force_presentation: Some(Icon))}')
    for key,family in (('interface_font','Space Grotesk'),('monospace_font','IBM Plex Mono')):
        config('com.system76.CosmicTk',key,f'(family: "{family}", weight: Normal, stretch: Normal, style: Normal)')
    config('com.system76.CosmicTerm','font_name','"IBM Plex Mono"')
    config('com.system76.CosmicTerm','font_size','13')
    config('com.system76.CosmicTerm','syntax_theme_dark','"mxwl"')
    # ColorSchemeId is a transparent u64; reserved key avoids replacing existing schemes.
    scheme='(name: "mxwl", foreground: "'+brand['foreground']+'", background: "'+brand['background']+'", cursor: "'+brand['accent']+'", '
    for kind in ('normal','bright'):
        colors=dict(zip(('black','red','green','yellow','blue','magenta','cyan','white'),
                        (brand['surface'],brand['error'],brand['accentHover' if kind=='bright' else 'accent'],brand['peach'],brand['sky'],brand['lavender'],brand['sky'],brand['foreground'])))
        scheme+=kind+': ('+', '.join(k+': '+json.dumps(v) for k,v in colors.items())+'), '
    scheme+=')'
    write(BUILD/'mxwl-terminal.ron',scheme+'\n')
    config('com.system76.CosmicTerm','color_schemes_dark','{1919514476: '+scheme+'}')
    config('com.system76.CosmicBackground','same-on-all','true')
    # Style existing panels in place; their applet lists and monitor arrangement remain user-owned.
    for key,value in {'background':'Color(('+', '.join(f'{int(brand["background"][i:i+2],16)/255:.8f}' for i in (1,3,5))+'))',
                      'opacity':'1.0','border_radius':'0','padding':'0','spacing':'2','size':'XS'}.items():
        config('com.system76.CosmicPanel.Panel',key,value)
    for key,value in panel_layout().items():
        write(cosmic/'com.system76.CosmicPanel.Panel/v1'/key,value)
    spec=importlib.util.spec_from_file_location('mxwl_appearance',Path(window_list)/'appearance.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    style={**module.MXWL,**module.accent_colors(brand['accent'],brand['background'])}
    if preserve_layout:
        current=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'cosmic'
        for key in style.keys()-{'accent_color','active_text_color','active_background'}:
            path=current/'io.github.kerry.CosmicWindowList/v1'/key
            if path.is_file():style[key]=json.loads(path.read_text())
        for key in ('background','opacity','border_radius','padding','spacing','size'):
            path=current/'com.system76.CosmicPanel.Panel/v1'/key
            if path.is_file():config('com.system76.CosmicPanel.Panel',key,path.read_text().strip())
    for key,value in style.items(): config('io.github.kerry.CosmicWindowList',key,module.encode(value).strip())
    for source in (ROOT/'assets/fonts').rglob('*'):
        if source.is_file():
            dest=BUILD/'data/fonts/mxwl'/source.relative_to(ROOT/'assets/fonts')
            dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,dest)
    icons=BUILD/'data/icons/mxwl'
    write(icons/'index.theme','[Icon Theme]\nName=mxwl\nComment=mxwl folders with COSMIC application and symbolic icons\nInherits=Cosmic,Adwaita,hicolor\nDirectories=scalable/places\n\n[scalable/places]\nSize=48\nType=Scalable\nMinSize=16\nMaxSize=256\nContext=Places\n')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><path d="M4 11h15l5 5h20v25H4z" fill="{brand["surface"]}" stroke="{brand["accent"]}" stroke-width="2"/><path d="M11 24v10m0-8 5 5 5-5v8m6-8 4 8 4-8 4 8" fill="none" stroke="{brand["accent"]}" stroke-width="2"/></svg>'
    for name in ('folder','folder-open','folder-documents','folder-download','folder-pictures','user-home'):
        write(icons/'scalable/places'/(name+'.svg'),svg)
    background=wallpaper(brand)
    config('com.system76.CosmicBackground','all',f'(output: "all", source: Path("@DATA@/backgrounds/mxwl/{background}"), filter_by_theme: false, rotation_frequency: 3600, filter_method: Lanczos, scaling_mode: Zoom, sampling_method: Alphanumeric)')
    # Native exports are generated by the same library used by COSMIC Settings.
    write(BUILD/'config/gtk-3.0/settings.ini','[Settings]\ngtk-application-prefer-dark-theme=1\ngtk-font-name=Space Grotesk 10\ngtk-icon-theme-name=mxwl\n')
    write(BUILD/'config/gtk-4.0/settings.ini','[Settings]\ngtk-application-prefer-dark-theme=1\ngtk-font-name=Space Grotesk 10\ngtk-icon-theme-name=mxwl\n')
    for version in ('qt5ct','qt6ct'):
        write(BUILD/'config'/version/(version+'.conf'),'[Appearance]\ncustom_palette=true\ncolor_scheme_path=@CONFIG@/'+version+'/colors/CosmicDark.conf\nicon_theme=mxwl\n')
    write(BUILD/'config/kdeglobals',(BUILD/'data/color-schemes/CosmicDark.colors').read_text())
    write(BUILD/'config/mxwl-os/profile.json',json.dumps({'name':'mxwl','brand':brand},indent=2)+'\n')
    write(BUILD/'data/applications/io.github.kerry.MxwlOSAppearance.desktop',
          '[Desktop Entry]\nName=mxwl OS Appearance\nComment=Choose this machine’s accent color\n'
          f'Type=Application\nExec="{ROOT}/mxwl-os" settings\nIcon=preferences-desktop-theme\n'
          'Terminal=false\nCategories=Settings;DesktopSettings;\n')
    manifest=[]
    for kind in ('config','data'):
        for path in sorted((BUILD/kind).rglob('*')):
            if path.is_file(): manifest.append({'kind':kind,'path':str(path.relative_to(BUILD/kind))})
    for version in ('gtk-3.0','gtk-4.0'):
        manifest.append({'kind':'config','path':version+'/gtk.css','symlink':'@CONFIG@/gtk-4.0/cosmic/dark.css'})
    write(BUILD/'manifest.json',json.dumps(manifest,indent=2)+'\n')
    write(BUILD/'requirements.json',json.dumps({'cosmic-window-list':requirement()},indent=2)+'\n')
    (ROOT/'themes').mkdir(exist_ok=True)
    shutil.copy2(BUILD/'mxwl.ron',ROOT/'themes/mxwl.ron')
    shutil.copy2(BUILD/'mxwl-terminal.ron',ROOT/'themes/mxwl-terminal.ron')
    print(f'Built {len(manifest)} files. Wallpaper: {BUILD}/data/backgrounds/mxwl/mxwl-grid.png')


if __name__=='__main__': build()
