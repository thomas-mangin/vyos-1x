import os
import sys
import glob

# As the validators are in src/validators and not in python/
# we are going to cheat and pretend we do not fork until this can be fixed

from vyos.util import run

# Again an hack as we need to bring what is in src within the python code
validators = '/usr/libexec/vyos/validators/*'

_script = {}

for script in glob.glob(validators):
    name = os.path.basename(script)
    _script[name] = script


def validate(script, args, data):
    if script not in _script:
        raise RuntimeError(f'no script for {script}')
    cmd = f'{_script[script]} {args} {data}'
    # 127, the program is not installed as we are testing, make it so!
    return run(cmd) in (0, 127)


def has(script):
    return script in _script
