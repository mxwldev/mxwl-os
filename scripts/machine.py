"""Per-machine desktop theme preferences and appearance settings."""
import json
import os
from pathlib import Path
import subprocess
import sys

from appearance import build_ui, normalize
from build import ROOT, BUILD, build, effective_brand, machine_path, read_machine


def set_accent(color):
    preferences={**read_machine(),'accent':color}
    # Derive these again after an accent change, including themes saved by the UI.
    for key in ('accentHover','accentInk'):preferences.pop(key,None)
    set_theme(preferences)


def set_theme(preferences):
    from manage import Installer
    preferences=normalize(preferences)
    resolved=effective_brand(preferences)
    refresh_accent=resolved['accent']!=effective_brand()['accent']
    if 'COSMIC' not in os.environ.get('XDG_CURRENT_DESKTOP','').upper():
        raise ValueError('Run theme changes from a COSMIC desktop session.')
    from dependencies import install as install_window_list
    checkout=install_window_list()
    path=machine_path(); original=path.read_bytes() if path.exists() else None
    try:
        Installer.replace_file(path,(json.dumps(preferences,indent=2)+'\n').encode())
        build(checkout,preserve_layout=True,refresh_accent=refresh_accent)
        Installer().apply()
    except Exception:
        if original is None: path.unlink(missing_ok=True)
        else: Installer.replace_file(path,original)
        # Prevent a later apply from reusing a bundle of unsaved preferences.
        (BUILD/'manifest.json').unlink(missing_ok=True)
        raise
    print('Machine theme applied. Accent: '+resolved['accent'])


def run_settings():
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk,Gdk,Gio,GLib
    app=Gtk.Application(application_id='io.github.kerry.MxwlOSAppearance')
    def activate(application):
        existing=application.get_active_window()
        if existing: existing.present(); return
        win=Gtk.ApplicationWindow(application=application,title='mxwl OS Appearance')
        win.set_default_size(620,760)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);win.add(box)
        page,read_values=build_ui(Gtk,Gdk,effective_brand(),effective_brand({}),effective_brand)
        box.pack_start(page,True,True,0)
        status=Gtk.Label(xalign=0);status.set_line_wrap(True);box.pack_start(status,False,False,12)
        actions=Gtk.Box(spacing=8);actions.set_border_width(12)
        window_settings=Gtk.Button(label='Window List Settings')
        window_settings.connect('clicked',lambda _:subprocess.Popen([str(Path.home()/'.local/bin/cosmic-window-list-settings')]))
        actions.pack_start(window_settings,False,False,0)
        apply=Gtk.Button(label='Apply theme');apply.get_style_context().add_class('suggested-action')
        actions.pack_end(apply,False,False,0);box.pack_end(actions,False,False,0)
        def apply_theme(_):
            try: preferences=read_values()
            except ValueError as error:status.set_text(str(error));return
            try:
                process=Gio.Subprocess.new([sys.executable,str(ROOT/'mxwl-os'),'theme','--file','-'],
                    Gio.SubprocessFlags.STDIN_PIPE|Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_MERGE)
            except GLib.Error as error:status.set_text(str(error));return
            apply.set_sensitive(False);page.set_sensitive(False);status.set_text('Building and applying theme…')
            application.hold()
            def completed(process,result):
                try:
                    _,output,_=process.communicate_utf8_finish(result)
                    status.set_text('Theme applied. Saved for this machine.' if process.get_successful() else output[-1200:])
                except GLib.Error as error:status.set_text(str(error))
                finally:
                    apply.set_sensitive(True);page.set_sensitive(True);application.release()
            process.communicate_utf8_async(json.dumps(preferences),None,completed)
        apply.connect('clicked',apply_theme)
        win.show_all()
    app.connect('activate',activate);app.run([])
