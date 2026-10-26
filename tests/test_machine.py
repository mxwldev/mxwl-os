"""Per-machine colors never modify the shared brand and survive rebuilds."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build
import machine


class MachineTests(unittest.TestCase):
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


if __name__=='__main__':unittest.main()
