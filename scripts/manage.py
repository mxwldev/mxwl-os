#!/usr/bin/env python3
"""Build, inspect, apply and restore the user-local mxwl desktop profile."""
import argparse
import configparser
import datetime
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build'
sys.path.insert(0,str(ROOT/'scripts'))
from shortcuts import CONFIG_PATH as SHORTCUTS_PATH, merge as merge_shortcuts


def merge_ini(original, overlay):
    parser=configparser.ConfigParser(interpolation=None,strict=False)
    parser.optionxform=str
    parser.read_string(original or '')
    patch=configparser.ConfigParser(interpolation=None,strict=False)
    patch.optionxform=str; patch.read_string(overlay)
    for section in patch.sections():
        if not parser.has_section(section): parser.add_section(section)
        for key,value in patch.items(section): parser.set(section,key,value)
    stream=io.StringIO(); parser.write(stream,space_around_delimiters=False)
    return stream.getvalue().rstrip()+'\n'


def merge_scheme(original, overlay):
    """Keep existing COSMIC terminal schemes when adding our reserved map entry."""
    text=original.strip() or '{}'
    if not (text.startswith('{') and text.endswith('}')):
        raise ValueError('Unrecognized terminal color scheme map; no files changed.')
    parts=[]; start=1; depth=0; quoted=False; escaped=False
    for i,char in enumerate(text[1:-1],1):
        if quoted:
            if escaped: escaped=False
            elif char=='\\': escaped=True
            elif char=='"': quoted=False
        elif char=='"': quoted=True
        elif char in '([{': depth+=1
        elif char in ')]}': depth-=1
        elif char==',' and depth==0:
            parts.append(text[start:i].strip()); start=i+1
    if quoted or depth: raise ValueError('Unbalanced terminal color scheme map.')
    parts.append(text[start:-1].strip())
    parts=[part for part in parts if part and not part.lstrip().startswith('1919514476:')]
    parts.append(overlay.strip()[1:-1].strip())
    return '{\n'+',\n'.join(parts)+'\n}\n'


class Installer:
    def __init__(self,config=None,data=None,state=None):
        self.config=Path(config or os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config')).absolute()
        self.data=Path(data or os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share')).absolute()
        self.state=Path(state or os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state')).absolute()/'mxwl-os'
        self.roots={'config':self.config,'data':self.data}

    def expand(self,text):
        return text.replace('@CONFIG@',str(self.config)).replace('@DATA@',str(self.data))

    def plan(self):
        if not (BUILD/'manifest.json').exists(): raise ValueError('Run ./mxwl-os build first.')
        changes=[]
        for entry in json.loads((BUILD/'manifest.json').read_text()):
            relative=Path(entry['path'])
            if relative.is_absolute() or '..' in relative.parts: raise ValueError('Invalid manifest path')
            target=self.roots[entry['kind']]/relative
            change={**entry,'target':str(target)}
            if 'symlink' in entry:
                change['symlink']=self.expand(entry['symlink'])
                same=target.is_symlink() and os.readlink(target)==change['symlink']
            else:
                source=BUILD/entry['kind']/relative
                data=source.read_bytes()
                if source.suffix not in ('.ttf','.png'):
                    text=self.expand(data.decode())
                    if target.name in ('settings.ini','qt5ct.conf','qt6ct.conf','kdeglobals'):
                        text=merge_ini(target.read_text() if target.exists() else '',text)
                    elif target.name=='color_schemes_dark':
                        text=merge_scheme(target.read_text() if target.exists() else '{}',text)
                    elif str(relative)==SHORTCUTS_PATH:
                        text=merge_shortcuts(target.read_text() if target.exists() else '{}',text)
                    data=text.encode()
                change['data']=data
                same=target.is_file() and not target.is_symlink() and target.read_bytes()==data
            if not same: changes.append(change)
        # Fonts and icons must exist before native apps receive their new names.
        return sorted(changes,key=lambda item:item['kind']=='config')

    @staticmethod
    def replace_file(target,data):
        target.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.mxwl-',delete=False) as stream:
            temp=Path(stream.name)
            try:
                stream.write(data); stream.flush(); os.fchmod(stream.fileno(),0o644)
                temp.replace(target)
            finally: temp.unlink(missing_ok=True)

    def apply(self,refresh=True):
        changes=self.plan()
        if not changes: print('mxwl is already applied.'); return None
        was_applied=(self.config/'mxwl-os/profile.json').exists()
        stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup=self.state/'backups'/stamp; backup.mkdir(parents=True)
        records=[]
        # Snapshot every target before the first write, including symlink identity.
        for change in changes:
            target=Path(change['target'])
            record={k:v for k,v in change.items() if k not in ('data','symlink')}
            if target.is_symlink(): record.update(previous='symlink',link=os.readlink(target))
            elif target.exists():
                if not target.is_file(): raise ValueError(f'Expected a file: {target}')
                stored=backup/change['kind']/change['path']; stored.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(target,stored); record['previous']='file'
            else: record['previous']='absent'
            records.append(record)
        manifest={'version':1,'roots':{k:str(v) for k,v in self.roots.items()},'files':records}
        (backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        try:
            refreshed=False
            for change in changes:
                if refresh and change['kind']=='config' and not refreshed:
                    self.refresh(); refreshed=True
                target=Path(change['target']); target.parent.mkdir(parents=True,exist_ok=True)
                if 'symlink' in change:
                    temporary=target.with_name('.mxwl-link-'+stamp)
                    try: temporary.symlink_to(change['symlink']); temporary.replace(target)
                    finally: temporary.unlink(missing_ok=True)
                else: self.replace_file(target,change['data'])
        except Exception:
            self.restore(backup,refresh=False)
            raise
        self.state.mkdir(parents=True,exist_ok=True)
        baseline_marker=self.state/'baseline'
        previous_marker=baseline_marker if baseline_marker.exists() else self.state/'latest'
        if was_applied and previous_marker.exists():
            baseline=Path(previous_marker.read_text().strip())
            baseline_manifest=json.loads((baseline/'manifest.json').read_text())
            known={(entry['kind'],entry['path']) for entry in baseline_manifest['files']}
            for record in records:
                if (record['kind'],record['path']) not in known:
                    baseline_manifest['files'].append(record)
                    if record['previous']=='file':
                        target=baseline/record['kind']/record['path']; target.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copy2(backup/record['kind']/record['path'],target)
            (baseline/'manifest.json').write_text(json.dumps(baseline_manifest,indent=2)+'\n')
        else: baseline=backup
        baseline_marker.write_text(str(baseline)+'\n')
        (self.state/'latest').write_text(str(backup)+'\n')
        if refresh and not refreshed: self.refresh()
        print(f'Applied mxwl ({len(changes)} files). Backup: {backup}')
        return backup

    def restore(self,backup=None,refresh=True):
        if backup is None:
            marker=self.state/'baseline'
            if not marker.exists(): marker=self.state/'latest'
            if not marker.exists(): raise ValueError('No mxwl backup found.')
            backup=Path(marker.read_text().strip())
        backup=Path(backup)
        manifest=json.loads((backup/'manifest.json').read_text())
        if manifest['roots']!={k:str(v) for k,v in self.roots.items()}:
            raise ValueError('Backup belongs to different XDG directories.')
        for record in reversed(manifest['files']):
            relative=Path(record['path'])
            if relative.is_absolute() or '..' in relative.parts: raise ValueError('Invalid backup path')
            target=self.roots[record['kind']]/relative
            if str(target)!=record['target']: raise ValueError('Backup target mismatch')
            if record['previous']=='file':
                self.replace_file(target,(backup/record['kind']/relative).read_bytes())
                shutil.copystat(backup/record['kind']/relative,target)
            else:
                target.unlink(missing_ok=True)
                if record['previous']=='symlink':
                    target.parent.mkdir(parents=True,exist_ok=True); target.symlink_to(record['link'])
        if refresh: self.refresh()
        print('Restored '+str(backup))

    def refresh(self):
        if shutil.which('fc-cache'):
            result=subprocess.run(['fc-cache','-f',str(self.data/'fonts')],capture_output=True,text=True)
            if result.returncode: print('Font cache refresh: '+result.stderr.strip(),file=sys.stderr)
        if shutil.which('gtk-update-icon-cache') and (self.data/'icons/mxwl').exists():
            subprocess.run(['gtk-update-icon-cache','-f','-t',str(self.data/'icons/mxwl')],capture_output=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('build',help='Generate theme assets; does not change the desktop')
    build.add_argument('--window-list',type=Path)
    install=sub.add_parser('install',help='Install required Window List, build mxwl, and apply the profile')
    install.add_argument('--window-list',type=Path,help='Use a local Window List development checkout')
    accent=sub.add_parser('accent',help='Show or set this machine’s desktop accent color')
    accent.add_argument('color',nargs='?',help='Hex color, e.g. #8ccfe5 (quote it in the shell)')
    sub.add_parser('settings',help='Open the machine accent color picker')
    sub.add_parser('status',help='Report desktop and pending changes')
    apply=sub.add_parser('apply',help='Apply to this user with a complete file backup')
    apply.add_argument('--dry-run',action='store_true')
    apply.add_argument('--window-list',type=Path,help='Use a local Window List development checkout')
    restore=sub.add_parser('restore',help='Restore the desktop from before mxwl, or a specific backup')
    restore.add_argument('backup',nargs='?',type=Path)
    args=parser.parse_args()
    installer=Installer()
    if args.command=='build':
        from build import build
        build(args.window_list)
    elif args.command=='install':
        if 'COSMIC' not in os.environ.get('XDG_CURRENT_DESKTOP','').upper():
            raise ValueError('Run install from a COSMIC desktop session.')
        from dependencies import install as install_window_list
        from build import build
        checkout=install_window_list(args.window_list)
        build(checkout or args.window_list,preserve_layout=(installer.config/'mxwl-os/profile.json').exists())
        installer.apply()
    elif args.command=='settings':
        from machine import run_settings
        run_settings()
    elif args.command=='accent':
        if args.color is None:
            from build import effective_brand
            print(effective_brand()['accent'])
        else:
            from machine import set_accent
            set_accent(args.color)
    elif args.command=='restore': installer.restore(args.backup)
    elif args.command=='status':
        print('Desktop: '+os.environ.get('XDG_CURRENT_DESKTOP','unknown'))
        profile=installer.config/'mxwl-os/profile.json'
        print('Profile: '+('mxwl' if profile.exists() else 'not applied'))
        if profile.exists(): print('Machine accent: '+json.loads(profile.read_text())['brand']['accent'])
        from dependencies import ready
        print('Window List: '+('installed at required revision' if ready() else 'installation required (run ./mxwl-os install)'))
        print('Pending files: '+str(len(installer.plan())))
        for name in ('Space Grotesk','IBM Plex Mono'):
            if shutil.which('fc-match'):
                print(name+': '+subprocess.check_output(['fc-match','-f','%{family}',name],text=True))
    elif args.dry_run:
        changes=installer.plan()
        for change in changes: print(change['target'])
        print(f'{len(changes)} files would change. No desktop settings changed.')
    else:
        if 'COSMIC' not in os.environ.get('XDG_CURRENT_DESKTOP','').upper():
            raise ValueError('Run apply from a COSMIC desktop session.')
        from dependencies import install as install_window_list
        checkout=install_window_list(args.window_list)
        if checkout is not None or not (BUILD/'manifest.json').exists():
            from build import build
            build(checkout or args.window_list,preserve_layout=True)
        installer.apply()


if __name__=='__main__':
    try: main()
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        print('mxwl-os: '+str(error),file=sys.stderr); sys.exit(1)
