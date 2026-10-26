"""Fetch and install the required, pinned COSMIC Window List applet."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
APP_ID='io.github.kerry.CosmicWindowList'
STOCK_ID='com.system76.CosmicAppList'


def requirement():
    value=json.loads((ROOT/'dependencies.json').read_text())['cosmic-window-list']
    if not re.fullmatch(r'[0-9a-f]{40}',value['revision']):
        raise ValueError('Window List dependency must be pinned to a full commit SHA.')
    return value


def git(path,*args):
    return subprocess.check_output(['git','-C',str(path),*args],text=True).strip()


def validate_source(path):
    for name in ('appearance.py','settings.py','install.py','build.sh'):
        if not (path/name).is_file():raise ValueError(f'Window List source is missing {name}: {path}')
    return path


def source(override=None):
    if override is not None:return validate_source(Path(override).expanduser().resolve())
    required=requirement()
    sibling=ROOT.parents[1]/'cosmic-window-list'
    if (sibling/'.git').exists():
        if git(sibling,'rev-parse','HEAD')==required['revision'] and not git(sibling,'status','--porcelain'):
            return validate_source(sibling)
    cache=Path(os.environ.get('XDG_CACHE_HOME',Path.home()/'.cache'))/'mxwl-os/dependencies'
    checkout=cache/('cosmic-window-list-'+required['revision'])
    if checkout.exists():
        if git(checkout,'rev-parse','HEAD')!=required['revision']:
            raise ValueError('Cached Window List checkout has the wrong revision: '+str(checkout))
        if git(checkout,'status','--porcelain'):
            raise ValueError('Cached Window List source has local edits; use --window-list for a development checkout.')
        return validate_source(checkout)
    cache.mkdir(parents=True,exist_ok=True)
    staged=Path(tempfile.mkdtemp(prefix='.window-list-',dir=cache))
    try:
        print('Fetching required cosmic-window-list '+required['revision'][:12]+'…',flush=True)
        subprocess.run(['git','init','--quiet',str(staged)],check=True)
        subprocess.run(['git','-C',str(staged),'remote','add','origin',required['repository']],check=True)
        subprocess.run(['git','-C',str(staged),'fetch','--depth','1','origin',required['revision']],check=True)
        subprocess.run(['git','-C',str(staged),'checkout','--quiet','--detach','FETCH_HEAD'],check=True)
        validate_source(staged)
        if git(staged,'rev-parse','HEAD')!=required['revision']:raise ValueError('Window List revision verification failed.')
        staged.rename(checkout)
    finally:
        if staged.exists():shutil.rmtree(staged)
    return checkout


def installed_files():
    home=Path.home()
    return [home/'.local/bin/cosmic-window-list',home/'.local/bin/cosmic-window-list-settings',
            home/'.local/share/cosmic-window-list/settings.py',home/'.local/share/cosmic-window-list/appearance.py',
            home/'.local/share/applications/io.github.kerry.CosmicWindowList.desktop',
            home/'.local/share/applications/io.github.kerry.CosmicWindowListSettings.desktop']


def installation_marker():
    return Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'mxwl-os/window-list.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ready():
    marker=installation_marker()
    if not marker.is_file():return False
    try:
        record=json.loads(marker.read_text())
        return (record['revision']==requirement()['revision'] and all(
            path.is_file() and record['files'].get(str(path))==digest(path) for path in installed_files()))
    except (KeyError,ValueError,OSError):return False


def install(override=None):
    if override is None and ready():return None
    checkout=source(override)
    print('Building and installing required COSMIC Window List…',flush=True)
    subprocess.run(['bash',str(checkout/'build.sh')],cwd=checkout,check=True)
    # Use the existing slot if present. Fresh panels are activated by the profile.
    panel=Path.home()/'.config/cosmic/com.system76.CosmicPanel.Panel/v1'
    has_slot=any(path.is_file() and any(json.dumps(ident) in path.read_text() for ident in (APP_ID,STOCK_ID))
                 for path in (panel/'plugins_wings',panel/'plugins_center'))
    option='--preserve-panel-icons' if has_slot else '--no-enable'
    subprocess.run(['/usr/bin/python3',str(checkout/'install.py'),option],cwd=checkout,check=True)
    files=installed_files()
    if not all(path.is_file() for path in files):raise ValueError('Window List installation did not produce all required files.')
    record={'revision':git(checkout,'rev-parse','HEAD'),'files':{str(path):digest(path) for path in files}}
    marker=installation_marker();marker.parent.mkdir(parents=True,exist_ok=True)
    staged=marker.with_suffix('.new');staged.write_text(json.dumps(record,indent=2)+'\n');staged.replace(marker)
    return checkout


def panel_layout(config_home=None):
    """Enable Window List in the existing slot, or append it on a fresh panel."""
    config_home=Path(config_home or os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))
    panel=config_home/'cosmic/com.system76.CosmicPanel.Panel/v1'
    system=Path('/usr/share/cosmic/com.system76.CosmicPanel.Panel/v1')
    def read(key,default):
        for root in (panel,system):
            if (root/key).is_file():return (root/key).read_text().strip()
        return default
    def strings(text):return [json.loads(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"',text)]
    wings=read('plugins_wings','None')
    match=re.fullmatch(r'Some\(\(\s*\[(.*?)\]\s*,\s*\[(.*?)\]\s*,?\s*\)\)',wings,re.S)
    if match:left,right=(strings(part) for part in match.groups())
    elif wings=='None':left,right=[],[]
    else:raise ValueError('Unrecognized panel layout; refusing to replace existing applets.')
    center_text=read('plugins_center','None')
    if center_text!='None' and not re.fullmatch(r'Some\(\s*\[.*\]\s*\)',center_text,re.S):
        raise ValueError('Unrecognized center panel layout.')
    center=strings(center_text)
    lists=[left,right,center]
    # Remove the stock taskbar only if Window List already has a slot.
    present=any(APP_ID in items for items in lists)
    for items in lists:
        items[:]=[item for item in items if not (present and item==STOCK_ID)]
        for index,item in enumerate(items):
            if item==STOCK_ID:items[index]=APP_ID;present=True
    if not present:left.append(APP_ID)
    return {'plugins_wings':'Some(('+json.dumps(left)+', '+json.dumps(right)+'))\n',
            'plugins_center':center_text+'\n' if center==strings(center_text) else 'Some('+json.dumps(center)+')\n'}
