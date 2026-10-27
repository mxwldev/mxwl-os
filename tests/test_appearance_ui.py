"""Exercise real GTK controls without applying anything to the desktop."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import appearance
import build

try:
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk,Gdk
    GTK_AVAILABLE=Gtk.init_check()[0]
except (ImportError,ValueError):
    GTK_AVAILABLE=False


@unittest.skipUnless(GTK_AVAILABLE,'GTK 3 and a display are required for appearance UI checks')
class AppearanceUITests(unittest.TestCase):
    def setUp(self):
        self.defaults=build.effective_brand({})
        self.initial=build.effective_brand({'background':'#181a20','accent':'#8ccfe5',
                                          'accentHover':'#ffffff','inner_gap':12,
                                          'interface_font':'IBM Plex Mono'})
        self.page,self.read=appearance.build_ui(Gtk,Gdk,self.initial,self.defaults,build.effective_brand)
        self.addCleanup(self.page.destroy)
        self.widgets=list(self.walk(self.page))

    def walk(self,widget):
        yield widget
        if isinstance(widget,Gtk.Container):
            for child in widget.get_children():yield from self.walk(child)

    def click(self,label):
        next(widget for widget in self.widgets if isinstance(widget,Gtk.Button) and widget.get_label()==label).clicked()

    def test_initial_custom_values_are_retained_and_invalid_hex_is_rejected(self):
        self.assertEqual(self.read(),{key:self.initial[key] for key in (*appearance.COLORS,*appearance.DEFAULTS)})
        entry=next(widget for widget in self.widgets if isinstance(widget,Gtk.Entry) and widget.get_text()=='#181a20')
        entry.set_text('#abc')
        with self.assertRaisesRegex(ValueError,'Desktop background'):self.read()
        entry.set_text('#121314')
        self.assertEqual(self.read()['background'],'#121314')

    def test_presets_update_accent_without_resetting_customizations_and_reset_restores_defaults(self):
        self.click('Lavender')
        values=self.read()
        self.assertEqual(values['accent'],'#c2b4ff')
        self.assertEqual(values['accentHover'],build.effective_brand({'accent':'#c2b4ff'})['accentHover'])
        for key in ('background','interface_font','inner_gap'):self.assertEqual(values[key],self.initial[key])
        self.click('mxwl defaults')
        self.assertEqual(self.read(),{key:self.defaults[key] for key in (*appearance.COLORS,*appearance.DEFAULTS)})


if __name__=='__main__':unittest.main()
