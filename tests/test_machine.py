"""Per-machine colors never modify the shared brand and survive rebuilds."""
import json
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build
import machine
import appearance
import manage


class MachineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        patcher=patch.dict('os.environ',{'XDG_CONFIG_HOME':str(self.root/'config'),'XDG_CURRENT_DESKTOP':'COSMIC'})
        patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(machine,'BUILD',self.root/'bundle')
        patcher.start();self.addCleanup(patcher.stop)

    def test_custom_accent_derives_coherent_colors_without_changing_shared_brand(self):
        original=(build.ROOT/'brand.json').read_bytes()
        result=build.effective_brand({'accent':'#8CCFE5'})
        self.assertEqual(result['accent'],'#8ccfe5')
        self.assertNotEqual(result['accentHover'],'#a2cc90')
        self.assertEqual((build.ROOT/'brand.json').read_bytes(),original)

    def test_invalid_color_is_rejected(self):
        for value in ('green','#abc','#12345678','garbage',None):
            with self.assertRaises(ValueError):build.effective_brand({'accent':value})

    def test_saved_color_is_local_to_each_xdg_directory(self):
        with tempfile.TemporaryDirectory() as root:
            first=Path(root)/'machine1';second=Path(root)/'machine2'
            path=first/'mxwl-os/machine.json';path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'accent':'#c2b4ff'}))
            with patch.dict('os.environ',{'XDG_CONFIG_HOME':str(first)}):
                self.assertEqual(build.effective_brand()['accent'],'#c2b4ff')
            with patch.dict('os.environ',{'XDG_CONFIG_HOME':str(second)}):
                self.assertEqual(build.effective_brand()['accent'],'#91bd7d')

    def test_custom_theme_overrides_palette_fonts_and_geometry(self):
        preferences={'background':'#181A20','foreground':'#EEEEEE','accent':'#8ccfe5',
                     'accentHover':'#ffffff','interface_font':'Pixelify Sans',
                     'monospace_font':'Monospace','terminal_font_size':16,'outer_gap':12,
                     'inner_gap':8,'corner_radius':6,'active_hint':3}
        original=(build.ROOT/'brand.json').read_bytes()
        result=build.effective_brand(preferences)
        for key,value in preferences.items():
            self.assertEqual(result[key],value.lower() if key in appearance.COLORS else value)
        self.assertEqual((build.ROOT/'brand.json').read_bytes(),original)
        self.assertEqual(build.effective_brand({})['corner_radius'],2)

    def test_invalid_theme_is_rejected_before_dependency_or_desktop_changes(self):
        with patch('dependencies.install') as install,patch.object(machine,'build') as compile_theme,patch.object(manage.Installer,'apply') as apply:
            for preferences in ([],None,{'background':'red'},{'accentHover':'#fff'},
                                {'typo':'#ffffff'},{'outer_gap':True},{'inner_gap':1.5},
                                {'corner_radius':-1},{'terminal_font_size':100},{'interface_font':'Sans\nInjected=1'}):
                with self.subTest(preferences=preferences),self.assertRaises(ValueError):
                    machine.set_theme(preferences)
            install.assert_not_called();compile_theme.assert_not_called();apply.assert_not_called()
        self.assertFalse(build.machine_path().exists())

    def test_theme_save_survives_reload_and_retains_applet_appearance(self):
        preferences={'background':'#181a20','interface_font':'Pixelify Sans','inner_gap':8}
        with patch('dependencies.install',return_value=None),patch.object(machine,'build') as compile_theme,patch.object(manage.Installer,'apply'):
            machine.set_theme(preferences)
        self.assertEqual(build.read_machine(),preferences)
        self.assertEqual(build.effective_brand()['interface_font'],'Pixelify Sans')
        compile_theme.assert_called_once_with(None,preserve_layout=True,refresh_accent=False)

    def test_accent_change_preserves_custom_theme_and_rederives_highlights(self):
        preferences={'accent':'#91bd7d','accentHover':'#ffffff','accentInk':'#000000',
                     'background':'#181a20','monospace_font':'Monospace','inner_gap':8}
        path=build.machine_path();path.parent.mkdir(parents=True);path.write_text(json.dumps(preferences))
        with patch('dependencies.install',return_value=None),patch.object(machine,'build') as compile_theme,patch.object(manage.Installer,'apply'):
            machine.set_accent('#8CCFE5')
        saved=build.read_machine()
        self.assertEqual(saved['accent'],'#8ccfe5')
        self.assertEqual(saved['background'],preferences['background'])
        self.assertEqual(saved['monospace_font'],'Monospace')
        self.assertNotIn('accentHover',saved);self.assertNotIn('accentInk',saved)
        self.assertNotEqual(build.effective_brand()['accentHover'],'#ffffff')
        compile_theme.assert_called_once_with(None,preserve_layout=True,refresh_accent=True)

    def test_failed_build_or_apply_restores_preference_and_invalidates_bundle(self):
        path=build.machine_path();path.parent.mkdir(parents=True)
        manifest=machine.BUILD/'manifest.json';manifest.parent.mkdir(parents=True)
        for failure in ('build','apply'):
            for original in (None,b'{"background":"#181a20"}\n'):
                with self.subTest(failure=failure,original=original):
                    if original is None:path.unlink(missing_ok=True)
                    else:path.write_bytes(original)
                    manifest.write_text('[]')
                    with patch('dependencies.install',return_value=None),patch.object(machine,'build') as compile_theme,patch.object(manage.Installer,'apply') as apply:
                        (compile_theme if failure=='build' else apply).side_effect=OSError('simulated failure')
                        with self.assertRaises(OSError):machine.set_theme({'accent':'#8ccfe5'})
                    self.assertEqual(path.read_bytes() if path.exists() else None,original)
                    self.assertFalse(manifest.exists())

    def test_theme_cli_exports_importable_preferences_and_reads_stdin(self):
        stream=io.StringIO()
        with patch.object(sys,'argv',['mxwl-os','theme']),patch.object(sys,'stdout',stream):manage.main()
        exported=json.loads(stream.getvalue())
        self.assertEqual(appearance.normalize(exported),exported)
        with patch.object(sys,'argv',['mxwl-os','theme','--file','-']),patch.object(sys,'stdin',io.StringIO(stream.getvalue())),patch.object(machine,'set_theme') as apply:
            manage.main()
            apply.assert_called_once_with(exported)
        with patch.object(sys,'argv',['mxwl-os','theme','--reset']),patch.object(machine,'set_theme') as apply:
            manage.main()
            apply.assert_called_once_with({})


if __name__=='__main__':unittest.main()
