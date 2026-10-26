"""Exercise the shell bootstrap with isolated tools, never real sudo or apt."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
try:
    SUPPORTED=os.geteuid()!=0 and 'ID=pop\n' in Path('/etc/os-release').read_text()
except (AttributeError,OSError):
    SUPPORTED=False


@unittest.skipUnless(SUPPORTED,'Bootstrap targets a normal user on Pop!_OS')
class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.project=self.root/'mxwl checkout';self.project.mkdir()
        shutil.copy2(ROOT/'install.sh',self.project/'install.sh')
        shutil.copy2(ROOT/'dependencies.json',self.project/'dependencies.json')
        scripts=self.project/'scripts';scripts.mkdir()
        shutil.copy2(ROOT/'scripts/dependencies.py',scripts/'dependencies.py')
        self.dependency=self.root/'window list checkout';self.dependency.mkdir()
        for name in ('appearance.py','settings.py','install.py','build.sh'):
            (self.dependency/name).write_text('# fixture\n')
        self.record=self.root/'installer.json';self.sudo_log=self.root/'sudo.jsonl'
        home=self.root/'home';bin_dir=home/'.cargo/bin';bin_dir.mkdir(parents=True)
        self.env={**os.environ,'HOME':str(home),'XDG_CURRENT_DESKTOP':'COSMIC',
                  'PATH':str(bin_dir)+os.pathsep+os.environ['PATH'],
                  'MXWL_TEST_RECORD':str(self.record),'MXWL_TEST_SUDO_LOG':str(self.sudo_log)}
        def tool(name,code):
            path=bin_dir/name;path.write_text(code);path.chmod(0o755)
        tool('rustc',"#!/bin/sh\nprintf 'rustc 1.99.1 (fixture)\\n'\n")
        tool('cargo','#!/bin/sh\nexit 0\n')
        tool('dpkg-query','#!/bin/sh\nfor package do :; done\n'
             'if [ "$package" = libxkbcommon-dev ]; then exit 1; fi\nprintf installed\n')
        tool('sudo','#!/usr/bin/python3\nimport os,json,sys\n'
             'with open(os.environ["MXWL_TEST_SUDO_LOG"],"a") as log: log.write(json.dumps(sys.argv[1:])+"\\n")\n')
        (self.project/'mxwl-os').write_text('import json,os,sys\n'
            'from pathlib import Path\n'
            'Path(os.environ["MXWL_TEST_RECORD"]).write_text(json.dumps(sys.argv[1:]))\n')

    def run_script(self,*args):
        return subprocess.run(['bash',str(self.project/'install.sh'),*args,
                               '--window-list',str(self.dependency)],env=self.env,
                              capture_output=True,text=True,timeout=20)

    def test_check_reports_missing_packages_without_running_sudo_or_install(self):
        result=self.run_script('--check')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('libxkbcommon-dev',result.stdout)
        self.assertFalse(self.sudo_log.exists())
        self.assertFalse(self.record.exists())

    def test_install_uses_sudo_only_for_missing_packages_and_forwards_checkout(self):
        result=self.run_script()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        commands=[json.loads(line) for line in self.sudo_log.read_text().splitlines()]
        self.assertEqual(commands,[['apt-get','update'],['apt-get','install','-y','--','libxkbcommon-dev']])
        self.assertEqual(json.loads(self.record.read_text()),['install','--window-list',str(self.dependency)])

    def test_skip_packages_check_has_no_install_side_effects(self):
        result=self.run_script('--check','--skip-system-packages')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('Checks passed',result.stdout)
        self.assertFalse(self.sudo_log.exists())
        self.assertFalse(self.record.exists())

    def test_old_rust_is_upgraded_before_the_desktop_installer_runs(self):
        tools=Path(self.env['HOME'])/'.cargo/bin'
        (tools/'rustc').write_text("#!/bin/sh\nprintf 'rustc 1.85.0 (fixture)\\n'\n")
        rustup=tools/'rustup'
        rustup.write_text('#!/usr/bin/python3\nimport json,sys\nfrom pathlib import Path\n'
            'Path(__file__).with_name("rustup-args.json").write_text(json.dumps(sys.argv[1:]))\n'
            'Path(__file__).with_name("rustc").write_text("#!/bin/sh\\nprintf \'rustc 1.99.1 (fixture)\\\\n\'\\n")\n')
        rustup.chmod(0o755)
        result=self.run_script('--skip-system-packages')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(json.loads((tools/'rustup-args.json').read_text()),
                         ['toolchain','install','stable','--profile','minimal'])
        self.assertTrue(self.record.exists())
        self.assertFalse(self.sudo_log.exists())

    def test_wrong_desktop_fails_before_package_changes(self):
        self.env.pop('XDG_CURRENT_DESKTOP')
        result=self.run_script()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('COSMIC session',result.stderr)
        self.assertFalse(self.sudo_log.exists())
        self.assertFalse(self.record.exists())


if __name__=='__main__':unittest.main()
