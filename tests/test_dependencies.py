"""Real local Git fetches and fixture installs exercise fresh-machine requirements."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import dependencies
import manage


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        home=self.root/'home';home.mkdir()
        env={'HOME':str(home),'XDG_CACHE_HOME':str(self.root/'cache'),
             'XDG_CONFIG_HOME':str(home/'.config'),'XDG_STATE_HOME':str(self.root/'state'),
             'XDG_CURRENT_DESKTOP':'COSMIC'}
        patcher=patch.dict(os.environ,env);patcher.start();self.addCleanup(patcher.stop)
        source=self.root/'origin';source.mkdir()
        files=[str(path.relative_to(home)) for path in dependencies.installed_files()]
        (source/'appearance.py').write_text('MXWL={}\n')
        (source/'settings.py').write_text('# settings fixture\n')
        (source/'build.sh').write_text('#!/bin/sh\nexit 0\n')
        (source/'install.py').write_text(
            'from pathlib import Path\nimport sys\n'
            f'for name in {files!r}:\n'
            ' p=Path.home()/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("installed")\n'
            'with (Path.home()/"install.log").open("a") as log:log.write(sys.argv[-1]+"\\n")\n')
        subprocess.run(['git','init','--quiet',str(source)],check=True)
        subprocess.run(['git','-C',str(source),'add','.'],check=True)
        subprocess.run(['git','-C',str(source),'-c','user.name=Test','-c','user.email=test@example.invalid',
                        'commit','--quiet','-m','Dependency fixture'],check=True)
        self.revision=dependencies.git(source,'rev-parse','HEAD')
        project=self.root/'workspace/mxwl/mxwl-os';project.mkdir(parents=True)
        (project/'dependencies.json').write_text(json.dumps({'cosmic-window-list':
            {'repository':source.as_uri(),'revision':self.revision}}))
        patcher=patch.object(dependencies,'ROOT',project);patcher.start();self.addCleanup(patcher.stop)

    def test_fresh_checkout_fetches_exact_revision_and_rejects_edits(self):
        checkout=dependencies.source()
        self.assertEqual(dependencies.git(checkout,'rev-parse','HEAD'),self.revision)
        self.assertEqual(dependencies.source(),checkout)
        (checkout/'appearance.py').write_text('local edit')
        with self.assertRaises(ValueError):dependencies.source()

    def test_missing_dependency_is_installed_and_repaired_without_manual_step(self):
        self.assertFalse(dependencies.ready())
        dependencies.install()
        self.assertTrue(dependencies.ready())
        self.assertIsNone(dependencies.install())
        log=Path.home()/'install.log'
        self.assertEqual(log.read_text(),'--no-enable\n')
        dependencies.installed_files()[0].unlink()
        self.assertFalse(dependencies.ready())
        dependencies.install()
        self.assertTrue(dependencies.ready())
        self.assertEqual(log.read_text(),'--no-enable\n--no-enable\n')

    def test_existing_taskbar_is_reloaded_without_hiding_panel_icons(self):
        panel=Path.home()/'.config/cosmic/com.system76.CosmicPanel.Panel/v1'
        panel.mkdir(parents=True)
        (panel/'plugins_wings').write_text('Some((["com.system76.CosmicAppList"], ["custom.tray"]))')
        dependencies.install()
        self.assertEqual((Path.home()/'install.log').read_text(),'--preserve-panel-icons\n')
        self.assertIn('custom.tray',(panel/'plugins_wings').read_text())

    def test_panel_activation_preserves_custom_applets_and_stock_position(self):
        panel=Path.home()/'.config/cosmic/com.system76.CosmicPanel.Panel/v1'
        panel.mkdir(parents=True)
        (panel/'plugins_wings').write_text('Some((["custom.launcher", "com.system76.CosmicAppList"], ["custom.tray"]))')
        (panel/'plugins_center').write_text('Some(["custom.clock"])')
        layout=dependencies.panel_layout()
        self.assertIn('"custom.launcher", "io.github.kerry.CosmicWindowList"',layout['plugins_wings'])
        self.assertIn('custom.tray',layout['plugins_wings'])
        self.assertEqual(layout['plugins_center'],'Some(["custom.clock"])\n')
        self.assertNotIn('com.system76.CosmicAppList',layout['plugins_wings'])

    def test_fresh_panel_gets_window_list_without_an_existing_taskbar(self):
        panel=Path.home()/'.config/cosmic/com.system76.CosmicPanel.Panel/v1'
        panel.mkdir(parents=True)
        (panel/'plugins_wings').write_text('None')
        (panel/'plugins_center').write_text('None')
        self.assertIn('io.github.kerry.CosmicWindowList',dependencies.panel_layout()['plugins_wings'])

    def test_failed_dependency_blocks_desktop_application(self):
        with (patch.object(dependencies,'install',side_effect=ValueError('dependency unavailable')),
             patch.object(manage.Installer,'apply') as apply,
             patch.object(sys,'argv',['mxwl-os','apply'])):
            with self.assertRaisesRegex(ValueError,'dependency unavailable'):manage.main()
            apply.assert_not_called()


if __name__=='__main__':unittest.main()
