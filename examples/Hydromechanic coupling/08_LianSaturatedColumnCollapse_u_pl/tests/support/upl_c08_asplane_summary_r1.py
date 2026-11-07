"""Strict Run.csv reader; only the known unquoted AS_Bui2008(0.2;2.55) Configuration separator is repairable."""
import re,struct
from pathlib import Path

def summary(path):
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines()
    if len(lines)!=2:raise ValueError('Exactly one Run.csv header and one data row required')
    match=re.match(r'^#?RunName([;,])',lines[0])
    if match is None:raise ValueError('Unsupported Run.csv header')
    sep=match[1];header=lines[0][1:] if lines[0].startswith('#') else lines[0];keys=header.split(sep);values=lines[1].split(sep)
    if len(set(keys))!=len(keys) or any(not key for key in keys) or keys.count('Configuration')!=1:raise ValueError('Unique nonempty Run.csv keys and one Configuration required')
    index=keys.index('Configuration');extra=len(values)-len(keys)
    if extra==1 and sep==';':values=values[:index]+[values[index]+';'+values[index+1]]+values[index+2:]
    elif extra!=0:raise ValueError('Only one embedded Configuration AS semicolon is admitted')
    configuration=values[index]
    if extra==1 or 'AS_Bui2008' in configuration:
        number=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
        matches=list(re.finditer(r'(?:^| - )AS_Bui2008\(('+number+r');('+number+r')\)(?= - |$)',configuration))
        if len(matches)!=1 or configuration.count(';')!=1 or configuration.count('AS_Bui2008')!=1:raise ValueError('Complete unique AS_Bui2008 coefficient/exponent token required')
        if any(struct.pack('<f',float(matches[0][j+1]))!=struct.pack('<f',expected) for j,expected in enumerate((.2,2.55))):raise ValueError('Run.csv AS coefficient/exponent differs from0.2f/2.55f')
    if len(values)!=len(keys):raise ValueError('Run.csv reconstructed width differs')
    # Strings before/after Configuration are not stripped, converted, normalized or rewritten.
    return dict(zip(keys,values))
