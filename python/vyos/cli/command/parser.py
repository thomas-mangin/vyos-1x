import argparse

from vyos.cli.structure.root import commands

_parser = argparse.ArgumentParser(description='Possible completions:')

_command = list(commands.keys())

_subparsers = _parser.add_subparsers()
for k, v in commands.items():
    _sub = _subparsers.add_parser(k, help=v, description=v)
    _sub.add_argument('command', nargs='*', type=str)

__format = _parser.format_help().split('\n')
_format = __format[2] + '\n' + '\n'.join(__format[6:-2])


def parse(args):
    return _parser.parse_known_args(args)


def format_help():
    return _format


def print_help():
    return _parser.print_help()
