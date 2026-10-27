"""Desktop appearance controls and validation shared by the UI and builder."""
import re

COLORS = {
    'background': 'Desktop background', 'surface': 'Surface background',
    'elevated': 'Raised surface', 'foreground': 'Text', 'muted': 'Muted / disabled text',
    'faint': 'Disabled borders', 'line': 'Borders and dividers', 'accent': 'Accent',
    'accentHover': 'Accent highlight', 'accentInk': 'Text on accent',
    'lavender': 'Terminal magenta', 'peach': 'Warning / terminal yellow',
    'sky': 'Terminal blue / cyan', 'error': 'Error / terminal red',
}
NUMBERS = {
    'terminal_font_size': (13, 8, 36, 'Terminal font size'),
    'outer_gap': (4, 0, 64, 'Outer window gap'),
    'inner_gap': (4, 0, 64, 'Inner window gap'),
    'active_hint': (1, 0, 8, 'Active window border width'),
    'corner_radius': (2, 0, 24, 'Corner radius'),
}
FONTS = {'interface_font': 'Space Grotesk', 'monospace_font': 'IBM Plex Mono'}
DEFAULTS = {**FONTS, **{key: spec[0] for key, spec in NUMBERS.items()}}


def normalize(preferences):
    """Validate the entire preference before any build or desktop write."""
    if not isinstance(preferences, dict):
        raise ValueError('Machine theme must be a JSON object.')
    unknown = preferences.keys() - COLORS.keys() - DEFAULTS.keys()
    if unknown:
        raise ValueError('Unknown theme setting: ' + ', '.join(sorted(unknown)))
    result = dict(preferences)
    for key, value in result.items():
        if key in COLORS:
            if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                raise ValueError(f'{COLORS[key]} must be a six-digit hex color, e.g. #8ccfe5.')
            result[key] = value.lower()
        elif key in NUMBERS:
            _, low, high, label = NUMBERS[key]
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'{label} must be an integer between {low} and {high}.')
        elif not isinstance(value, str) or not value.strip() or len(value) > 100 or any(ord(c) < 32 for c in value):
            raise ValueError(f'{key.replace("_", " ")} must be a font family name.')
        else:
            result[key] = value.strip()
    return result


def build_ui(Gtk, Gdk, values, default_values, resolve):
    """Return editable appearance controls and their validated value reader."""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    page.set_border_width(16)
    presets = Gtk.Box(spacing=8)
    presets.pack_start(Gtk.Label(label='Preset', xalign=0), False, False, 0)
    reset = Gtk.Button(label='mxwl defaults')
    presets.pack_start(reset, False, False, 0)
    for name, color in (('Green', '#91bd7d'), ('Sky', '#8ccfe5'),
                        ('Lavender', '#c2b4ff'), ('Peach', '#f2b68d')):
        button = Gtk.Button(label=name)
        button.connect('clicked', lambda _, color=color: set_accent(color))
        presets.pack_start(button, False, False, 0)
    page.pack_start(presets, False, False, 0)

    preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    preview.set_name('mxwl-theme-preview')
    heading = Gtk.Label(label='Desktop preview', xalign=0)
    heading.set_name('mxwl-theme-heading')
    preview.pack_start(heading, False, False, 0)
    sample = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    sample.set_name('mxwl-theme-surface')
    sample.pack_start(Gtk.Label(label='Applications and windows', xalign=0), False, False, 0)
    muted = Gtk.Label(label='Secondary text and dividers', xalign=0)
    muted.set_name('mxwl-theme-muted'); sample.pack_start(muted, False, False, 0)
    terminal = Gtk.Label(label='~/Workspaces $ mxwl-os', xalign=0)
    terminal.set_name('mxwl-theme-terminal'); sample.pack_start(terminal, False, False, 0)
    action = Gtk.Label(label='Selected item')
    action.set_name('mxwl-theme-accent'); sample.pack_start(action, False, False, 0)
    preview.pack_start(sample, False, False, 0)
    page.pack_start(preview, False, False, 0)
    provider = Gtk.CssProvider()
    for widget in (preview, heading, sample, muted, terminal, action):
        widget.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    grid = Gtk.Grid(column_spacing=18, row_spacing=8)
    controls.pack_start(grid, False, False, 0)
    widgets = {}
    def field(key, label, widget):
        row = len(widgets)
        grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
        grid.attach(widget, 1, row, 1, 1)
        widgets[key] = widget

    def update_preview(*_):
        import json
        try: style = resolve(read())
        except ValueError: return
        css = f'''
            #mxwl-theme-preview {{ background-color: {style['background']}; color: {style['foreground']};
                padding: {12 + style['outer_gap']}px; font-family: {json.dumps(style['interface_font'], ensure_ascii=False)}; }}
            #mxwl-theme-heading {{ color: {style['foreground']}; }}
            #mxwl-theme-surface {{ background-color: {style['surface']}; color: {style['foreground']};
                border: {style['active_hint']}px solid {style['accent']};
                border-radius: {style['corner_radius']}px; padding: {12 + style['inner_gap']}px; }}
            #mxwl-theme-muted {{ color: {style['muted']}; border-bottom: 1px solid {style['line']}; padding-bottom: 8px; }}
            #mxwl-theme-terminal {{ background-color: {style['elevated']}; color: {style['foreground']};
                font-family: {json.dumps(style['monospace_font'], ensure_ascii=False)}; font-size: {style['terminal_font_size']}pt; padding: 8px; }}
            #mxwl-theme-accent {{ background-color: {style['accent']}; color: {style['accentInk']};
                border: 1px solid {style['accentHover']}; padding: 6px; }}
        '''
        provider.load_from_data(css.encode())

    def set_accent(color):
        derived = resolve({'accent': color})
        for key in ('accent', 'accentHover', 'accentInk'):
            widgets[key].set_text(derived[key])

    for key, label in COLORS.items():
        row = Gtk.Box(spacing=8)
        rgba = Gdk.RGBA(); rgba.parse(values[key])
        picker = Gtk.ColorButton.new_with_rgba(rgba)
        picker.set_use_alpha(False); picker.set_title(label)
        entry = Gtk.Entry(); entry.set_width_chars(10); entry.set_text(values[key])
        def picked(button, entry=entry):
            rgba = button.get_rgba()
            entry.set_text('#%02x%02x%02x' % tuple(round(v * 255) for v in (rgba.red, rgba.green, rgba.blue)))
        def typed(entry, picker=picker, key=key):
            color = entry.get_text().strip()
            valid = bool(re.fullmatch(r'#[0-9a-fA-F]{6}', color))
            entry.get_style_context().remove_class('error') if valid else entry.get_style_context().add_class('error')
            if valid:
                rgba = Gdk.RGBA(); rgba.parse(color); picker.set_rgba(rgba)
                if key == 'accent':
                    derived = resolve({'accent': color})
                    for related in ('accentHover', 'accentInk'):
                        widgets[related].set_text(derived[related])
            update_preview()
        picker.connect('color-set', picked); entry.connect('changed', typed)
        row.pack_start(picker, False, False, 0); row.pack_start(entry, True, True, 0)
        field(key, label, row)
        widgets[key] = entry

    for key, label in (('interface_font', 'Interface font'), ('monospace_font', 'Monospace font')):
        widget = Gtk.FontButton(); widget.set_font(values[key])
        widget.set_level(Gtk.FontChooserLevel.FAMILY); widget.set_show_size(False)
        widget.connect('font-set', update_preview); field(key, label, widget)
    for key, (_, low, high, label) in NUMBERS.items():
        widget = Gtk.SpinButton.new_with_range(low, high, 1); widget.set_value(values[key])
        widget.connect('value-changed', update_preview); field(key, label, widget)

    def read():
        return normalize({key: widget.get_text().strip() if key in COLORS else
                          widget.get_font_desc().get_family() if key in FONTS else widget.get_value_as_int()
                          for key, widget in widgets.items()})

    def reset_values(_):
        # Set the derived accent colors after the accent's automatic update.
        for key in ('accent', *[key for key in COLORS if key != 'accent']):
            widgets[key].set_text(default_values[key])
        for key in FONTS: widgets[key].set_font(default_values[key])
        for key in NUMBERS: widgets[key].set_value(default_values[key])
        update_preview()
    reset.connect('clicked', reset_values)
    update_preview()
    hint = Gtk.Label(label='Changes are saved for this machine when you choose Apply theme.\n'
                     'Accent changes derive highlight and text colors; you can edit them afterward.\n'
                     'Use Window List Settings for tile colors and panel dimensions.', xalign=0)
    hint.set_line_wrap(True); controls.pack_start(hint, False, False, 0)
    scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.add(controls); page.pack_start(scroll, True, True, 0)
    return page, read
