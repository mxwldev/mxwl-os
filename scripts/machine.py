"""Per-machine accent preference and its desktop color picker."""
import json
import os
from pathlib import Path
import subprocess
import sys

from build import ROOT, build, effective_brand, machine_path, read_machine


def set_accent(color):
    from manage import Installer
    if 'COSMIC' not in os.environ.get('XDG_CURRENT_DESKTOP','').upper():
        raise ValueError('Run accent changes from a COSMIC desktop session.')
    from dependencies import install as install_window_list
    install_window_list()
    preferences={**read_machine(),'accent':color}
    effective_brand(preferences)  # Validate before saving or building.
    path=machine_path(); original=path.read_bytes() if path.exists() else None
    try:
        Installer.replace_file(path,(json.dumps(preferences,indent=2)+'\n').encode())
        build(preserve_layout=True,refresh_accent=True)
        Installer().apply()
    except Exception:
        if original is None: path.unlink(missing_ok=True)
        else: Installer.replace_file(path,original)
        raise
    print('Machine accent: '+color.lower())


def run_settings():
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk,Gdk,Gio,GLib
    app=Gtk.Application(application_id='io.github.kerry.MxwlOSAppearance')
    def activate(application):
        existing=application.get_active_window()
        if existing: existing.present(); return
        win=Gtk.ApplicationWindow(application=application,title='mxwl OS Appearance')
        win.set_default_size(460,260);win.set_border_width(24)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16);win.add(box)
        title=Gtk.Label(xalign=0);title.set_markup('<big><b>Machine accent</b></big>')
        box.pack_start(title,False,False,0)
        hint=Gtk.Label(label='Choose a color to identify this machine. It updates the desktop,\n'
                           'window hints, active window tiles, terminal and folder icons.',xalign=0)
        hint.set_line_wrap(True);box.pack_start(hint,False,False,0)
        rgba=Gdk.RGBA();rgba.parse(effective_brand()['accent'])
        picker=Gtk.ColorButton.new_with_rgba(rgba);picker.set_use_alpha(False)
        entry=Gtk.Entry();entry.set_text(effective_brand()['accent']);entry.set_width_chars(9)
        row=Gtk.Box(spacing=12);row.pack_start(picker,False,False,0);row.pack_start(entry,False,False,0)
        box.pack_start(row,False,False,0)
        def changed(widget):
            c=widget.get_rgba()
            entry.set_text('#%02x%02x%02x'%tuple(round(v*255) for v in (c.red,c.green,c.blue)))
        picker.connect('color-set',changed)
        def text_changed(widget):
            c=Gdk.RGBA()
            if c.parse(widget.get_text()):picker.set_rgba(c)
        entry.connect('changed',text_changed)
        presets=Gtk.Box(spacing=8)
        for name,color in (('Green','#91bd7d'),('Sky','#8ccfe5'),('Lavender','#c2b4ff'),('Peach','#f2b68d')):
            button=Gtk.Button(label=name)
            button.connect('clicked',lambda _,color=color:entry.set_text(color));presets.pack_start(button,False,False,0)
        box.pack_start(presets,False,False,0)
        status=Gtk.Label(xalign=0);status.set_line_wrap(True);box.pack_start(status,False,False,0)
        actions=Gtk.Box(spacing=8)
        window_settings=Gtk.Button(label='Window List Settings')
        window_settings.connect('clicked',lambda _:subprocess.Popen([str(Path.home()/'.local/bin/cosmic-window-list-settings')]))
        actions.pack_start(window_settings,False,False,0)
        apply=Gtk.Button(label='Apply accent');apply.get_style_context().add_class('suggested-action')
        actions.pack_end(apply,False,False,0);box.pack_end(actions,False,False,0)
        def apply_color(_):
            color=entry.get_text().strip()
            try: effective_brand({'accent':color})
            except ValueError as error:status.set_text(str(error));return
            apply.set_sensitive(False);status.set_text('Applying '+color+'…')
            process=subprocess.Popen([sys.executable,str(ROOT/'mxwl-os'),'accent',color],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            def completed():
                if process.poll() is None:return True
                output=process.communicate()[0]
                apply.set_sensitive(True)
                status.set_text('Applied '+color+'. Saved for this machine.' if process.returncode==0 else output[-1200:])
                return False
            GLib.timeout_add(250,completed)
        apply.connect('clicked',apply_color)
        win.show_all()
    app.connect('activate',activate);app.run([])
