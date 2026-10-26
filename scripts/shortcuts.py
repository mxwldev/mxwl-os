"""Merge mxwl shortcuts into COSMIC's existing custom shortcut map."""
import json

CONFIG_PATH='cosmic/com.system76.CosmicSettings.Shortcuts/v1/custom'
DEFAULTS='''{
    (modifiers: [Alt], key: "space"): System(Launcher),
}
'''


def parts(text, separator=',', clean=False):
    """Split RON at top-level separators, respecting strings and comments."""
    result=[]; current=[]; stack=[]; quoted=False; escaped=False; i=0
    while i<len(text):
        char=text[i]
        if quoted:
            if escaped: escaped=False
            elif char=='\\': escaped=True
            elif char=='"': quoted=False
        elif text.startswith('//',i) or text.startswith('/*',i):
            start=i
            if text.startswith('//',i):
                end=text.find('\n',i+2); i=len(text) if end<0 else end
            else:
                depth=1; i+=2
                while i<len(text) and depth:
                    if text.startswith('/*',i): depth+=1; i+=2
                    elif text.startswith('*/',i): depth-=1; i+=2
                    else: i+=1
                if depth: raise ValueError('Unclosed COSMIC shortcut comment.')
            current.append(' ' if clean else text[start:i])
            continue
        elif char=='"': quoted=True
        elif char in '([{': stack.append(char)
        elif char in ')]}':
            if not stack or stack.pop()!={')':'(',']':'[','}':'{'}[char]:
                raise ValueError('Unbalanced COSMIC shortcut map.')
        elif char==separator and not stack:
            result.append(''.join(current).strip()); current=[]; i+=1; continue
        current.append(char); i+=1
    if quoted or stack: raise ValueError('Unbalanced COSMIC shortcut map.')
    result.append(''.join(current).strip())
    return result


def merge(original, overlay=DEFAULTS):
    def entries(text):
        text=text.strip() or '{}'
        if not (text.startswith('{') and text.endswith('}')):
            raise ValueError('Unrecognized COSMIC shortcut map; no files changed.')
        return [item for item in parts(text[1:-1]) if parts(item,clean=True)!=['']]

    def identity(entry):
        binding,action=parts(entry,':',clean=True)
        if not (binding.startswith('(') and binding.endswith(')')):
            raise ValueError('Unrecognized COSMIC shortcut binding.')
        fields=dict(parts(field,':') for field in parts(binding[1:-1]) if field)
        modifiers=fields.get('modifiers','[]').strip()
        if not (modifiers.startswith('[') and modifiers.endswith(']')):
            raise ValueError('Unrecognized COSMIC shortcut modifiers.')
        return frozenset(filter(None,parts(modifiers[1:-1]))),json.loads(fields.get('key','null'))

    previous=entries(original); patch=entries(overlay)
    replacements={identity(entry) for entry in patch}
    kept=[entry for entry in previous if identity(entry) not in replacements]
    # A final line comment must not swallow the entry's separator.
    return '{\n'+''.join('    '+entry+('\n    ' if '//' in entry.rsplit('\n',1)[-1] else '')+',\n'
                         for entry in kept+patch)+'}\n'
