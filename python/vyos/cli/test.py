#!/usr/bin/env python3

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import print_formatted_text
from prompt_toolkit import prompt

from vyos.cli.structure import load
from vyos.cli.structure.completer import VyOSCompleter
from vyos.cli.structure.tree import Tree
from vyos.cli.structure.root import commands
from vyos.cli.command import dispatch


def main():
    command = ''

    definition = load.xml_in('interface-definitions')
    tree = Tree(definition)
    # options = tree.find("interfaces ethernet ")
    options = tree.find(command)
    print()
    print(f'options {options}')
    print(f'inside {tree.inside}')
    print()
    for _ in tree.help():
        print(_)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except EOFError:
        pass

