#!/usr/bin/env python3

import socket
import getpass

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


corrections = {
    "neighbour": "neighbor",
}


class Buffer:
    command = ''
    helping = ''


running = True


def main():
    definition = load.xml_in('interface-definitions')
    completer = VyOSCompleter(definition, Buffer)

    kb = KeyBindings()

    # @kb.add(" ")
    # def _(event):
    #     b = event.app.current_buffer
    #     w = b.document.get_word_before_cursor()

    #     if w is not None:
    #         if w in corrections:
    #             b.delete_before_cursor(count=len(w))
    #             b.insert_text(corrections[w])

    #     b.insert_text(" ")

    @kb.add('c-c', eager=True)
    def _(event):
        global running
        running = False
        event.app.exit()

    @kb.add('?')
    def _(event):
        b = event.app.current_buffer

        if b.complete_state:
            b.complete_next()
        else:
            b.start_completion(select_first=False)

        Buffer.command = b.text
        event.app.exit()

    session = PromptSession(
        history=FileHistory('./myhistory'),
        # completer=FuzzyCompleter(completer),
        completer=completer,
        enable_history_search=True,
        complete_while_typing=True,
        complete_in_thread=False,
        auto_suggest=AutoSuggestFromHistory(),
        multiline=False,
        wrap_lines=True,
        enable_system_prompt=True,
        key_bindings=kb,
        mouse_support=False,
        vi_mode=True,
    )
        # validator=,
        # validate_while_typing=True,

    user = getpass.getuser()
    host = socket.gethostname()

    while running:
        print('[edit]')
        r = session.prompt(f'{user}@{host}# ', default=Buffer.command)
        if r:
            print('input is: ' + str(r))
            dispatch(r)
            continue
        print()
        print(Buffer.helping)
        print()
    print('exit')


def _main():
    definition = load.xml_in('interface-definitions')
    tree = Tree(definition)
    # options = tree.find("interfaces ethernet ")
    options = tree.find("interfaces ethernet eth0 d")
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
