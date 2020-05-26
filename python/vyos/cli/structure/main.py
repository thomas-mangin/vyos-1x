#!/usr/bin/env python3

import sys
import json
import argparse
import pprint

from vyos.cli.structure import load


def structure(definition):
    loaded = load.xml_in(definition)
    if not loaded:
        sys.exit(f'could not parse any xml files for {definition}')
    return loaded


def save_json(fname, loaded):
    with open(fname, 'w') as w:
        print(f'saving {fname}')
        w.write(json.dumps(loaded))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', type=str, help='save json to this file')
    arg = parser.parse_args()

    if arg.file:
        save_json(arg.file, structure('interface-definitions'))
    else:
        pprint.pprint(structure('interface-definitions'))


if __name__ == '__main__':
    main()
