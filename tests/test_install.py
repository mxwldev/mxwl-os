"""Exercise actual apply, repeated apply, rollback and restore in isolated XDG roots."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import manage
import shortcuts


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.installer=manage.Installer(self.root/'config',self.root/'data',self.root/'state')
        self.config=self.installer.config; self.config.mkdir()
        # A fresh checkout has no build/ directory; installation tests own a small
        # representative bundle and never depend on generated local artifacts.
        bundle=self.root/'bundle'
        files={
            ('config','gtk-3.0/settings.ini'):b'[Settings]\ngtk-font-name=Space Grotesk 10\n',
            ('config','gtk-4.0/cosmic/dark.css'):b'/* mxwl */\n',
            ('config','cosmic/com.system76.CosmicTerm/v1/color_schemes_dark'):b'{1919514476: (name: "mxwl")}\n',
            ('config','cosmic/com.system76.CosmicBackground/v1/all'):b'mxwl background',
            ('config',shortcuts.CONFIG_PATH):shortcuts.DEFAULTS.encode(),
            ('config','mxwl-os/profile.json'):b'{"name":"mxwl"}',
            ('data','fonts/mxwl/spacegrotesk/SpaceGrotesk[wght].ttf'):b'font fixture',
        }
        manifest=[]
        for (kind,name),data in files.items():
            path=bundle/kind/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            manifest.append({'kind':kind,'path':name})
        manifest.append({'kind':'config','path':'gtk-3.0/gtk.css','symlink':'@CONFIG@/gtk-4.0/cosmic/dark.css'})
        (bundle/'manifest.json').write_text(json.dumps(manifest))
        patcher=patch.object(manage,'BUILD',bundle);patcher.start();self.addCleanup(patcher.stop)

    def test_merge_ini_preserves_other_settings(self):
        result=manage.merge_ini('[Settings]\ncustom=keep\ngtk-font-name=Old\n','[Settings]\ngtk-font-name=Space Grotesk 10\n')
        self.assertIn('custom=keep',result); self.assertIn('gtk-font-name=Space Grotesk 10',result)

    def test_scheme_merge_handles_nested_values_and_commas_in_names(self):
        previous='{42: (name: "Other, scheme", normal: (red: "#ffffff")), 1919514476: (name: "old mxwl")} '
        result=manage.merge_scheme(previous,'{1919514476: (name: "mxwl")}')
        self.assertIn('Other, scheme',result); self.assertEqual(result.count('1919514476:'),1)
        self.assertNotIn('old mxwl',result)

    def test_shortcut_update_preserves_other_bindings_and_restores_original(self):
        target=self.config/shortcuts.CONFIG_PATH;target.parent.mkdir(parents=True)
        original='''{
    // Keep the uploader shortcut, including its command and description.
    (modifiers: [Ctrl, Shift, Alt], key: "u", description: Some("Upload, now")): Spawn("upload --title \\\"a,b\\\""),
    (key: "space", description: Some("Old launcher"), modifiers: [Alt]): Spawn("old-launcher"),
    (modifiers: [Ctrl, Alt], key: "t"): System(Terminal) // terminal
}
'''
        target.write_text(original)
        backup=self.installer.apply(refresh=False)
        updated=target.read_text()
        self.assertIn('Upload, now',updated)
        self.assertIn('Spawn("upload --title \\\"a,b\\\"")',updated)
        self.assertIn('System(Terminal)',updated)
        self.assertIn('// terminal',updated)
        self.assertNotIn('old-launcher',updated)
        self.assertEqual(updated.count('System(Launcher)'),1)
        self.assertEqual(self.installer.plan(),[])
        self.installer.restore(backup,refresh=False)
        self.assertEqual(target.read_text(),original)

    def test_invalid_shortcuts_abort_before_any_files_are_written(self):
        target=self.config/shortcuts.CONFIG_PATH;target.parent.mkdir(parents=True)
        target.write_text('{invalid shortcut map')
        with self.assertRaises(ValueError):self.installer.apply(refresh=False)
        self.assertEqual(target.read_text(),'{invalid shortcut map')
        self.assertFalse((self.config/'gtk-3.0/settings.ini').exists())
        self.assertFalse((self.installer.state/'backups').exists())

    def test_apply_is_idempotent_and_restore_recovers_symlinks_and_files(self):
        ini=self.config/'gtk-3.0/settings.ini'; ini.parent.mkdir()
        original='[Settings]\ncustom=keep\ngtk-font-name=Old\n'
        ini.write_text(original)
        css=self.config/'gtk-3.0/gtk.css'; css.symlink_to('/original/style.css')
        terminal=self.config/'cosmic/com.system76.CosmicTerm/v1/color_schemes_dark'
        terminal.parent.mkdir(parents=True); terminal.write_text('{42: (name: "Other")}')
        backup=self.installer.apply(refresh=False)
        self.assertIn('custom=keep',ini.read_text())
        self.assertIn('42:',terminal.read_text())
        self.assertEqual(self.installer.plan(),[])
        self.assertIsNone(self.installer.apply(refresh=False))
        self.installer.restore(backup,refresh=False)
        self.assertEqual(ini.read_text(),original)
        self.assertEqual(str(css.readlink()),'/original/style.css')
        self.assertEqual(terminal.read_text(),'{42: (name: "Other")}')
        self.assertFalse((self.installer.data/'fonts/mxwl/spacegrotesk/SpaceGrotesk[wght].ttf').exists())

    def test_failed_write_restores_previous_files(self):
        original=self.config/'cosmic/com.system76.CosmicBackground/v1/all'
        original.parent.mkdir(parents=True); original.write_text('original background')
        replace=self.installer.replace_file; calls=0
        def fail_once(target,data):
            nonlocal calls
            calls+=1
            if calls==3: raise OSError('simulated disk failure')
            replace(target,data)
        with patch.object(self.installer,'replace_file',side_effect=fail_once):
            with self.assertRaises(OSError): self.installer.apply(refresh=False)
        self.assertEqual(original.read_text(),'original background')
        self.assertFalse((self.config/'mxwl-os/profile.json').exists())


if __name__=='__main__': unittest.main()
