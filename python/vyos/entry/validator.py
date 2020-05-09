import sys
import argparse

from vyos.validators import registered as validators


def make_sys(extract=0):
    prog = sys.argv[0]
    cmd = sys.argv[1]
    sys.argv = sys.argv[1:]

    if extract and len(sys.argv) >= extract:
        extracted = sys.argv[:extract]
        sys.argv = sys.argv[extract:]
    else:
        extracted = []

    sys.argv = [f'{prog} {cmd}'] + sys.argv[1:]
    return extracted


def main():
    choices = validators.registered()
    choices.sort()
    epilog = '\n'.join([f"   {c:<20} {validators.doc(c)}" for c in choices])

    parser = argparse.ArgumentParser(
        description='vyos validator',
        add_help=False,
        formatter_class=(argparse.RawDescriptionHelpFormatter),
        epilog=f"command options:\n{epilog}"
    )
    parser.add_argument('-h', '--help', help='show this help message and exit', action='store_true')
    parser.add_argument('command', help='command to run', nargs='?', choices=choices)

    arg, _ = parser.parse_known_args()

    if not arg.command:
        if arg.help:
            parser.print_help()
            return

    if arg.command not in choices:
        parser.print_help()
        return

    make_sys()
    validators.call(arg.command)


if __name__ == '__main__':
    main()
