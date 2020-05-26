import os

from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion

from vyos.util import cmd
from vyos.ifconfig.section import Section

import vyos.cli.structure.keywords as kw
from vyos.cli.structure.tree import Tree
from vyos.cli.structure.root import commands


TAB = '     '

# TODO ..
paths = {
    'vyos_completion_dir' : os.environ.get('vyos_completion_dir', './src/conf_mode')
}


class VyOSCompleter(Completer):
    # debug
    counter = 0
    command = ''
    # /debug

    def __init__(self, definition, buff):
        self.tree = Tree(definition)
        self.ignore_case = True
        self.buffer = buff

    def get_completions(self, document, complete_event):
        command = document.text.lstrip()
        while '  ' in command:
            command = command.replace('  ', ' ')

        yield from self._completions(command)

    def _completions(self, command):
        # debug
        self.command = command

        # update the buffers as we may have added ' '
        self.buffer.command = command

        order = command.split(' ')[0]

        # provide the root command completion
        if order not in commands or ' ' not in command:
            yield from self._root(command)
            return

        # provide completion for set
        if order == 'set':
            yield from self._set(command)
            return

    def _debug(self):
        self.counter += 1
        return '-- debug\n' \
            f'counter: {self.counter}\n' \
            f'command: "{self.command}"\n' \
            f'passed: {self.tree.passed_node}\n' \
            '-- /debug\n'

    def _root(self, command):
        # we have a perfect match, look ahead to the next word
        matches = [order for order in commands if order.startswith(command)]
        if len(matches) == 1:
            if matches[0] == command:
                yield Completion(' ')
                return
            yield Completion(matches[0][len(command):])
            return

        for option in commands.keys():
            if option.startswith(command):
                yield Completion(option + ' ', -len(command))

        r = self._debug()

        r += '\nPossible completions:\n'

        word = command.strip()
        for k, v in commands.items():
            if k.startswith(word):
                r += f'{TAB}{k:<20} {v}\n'

        self.buffer.helping = r

    def _help_set(self):
        r = self._debug()

        r += '\n'
        r += '\nPossible completions:\n'
        for option in self.tree.help():
            r += f'{TAB}{option[0]:<20} {option[1]}\n'

        self.buffer.helping = r

    def _set(self, command):
        # remove the 'set '
        without_set = command[3:].lstrip()
        last = self.tree.find(without_set)

        if self.tree.perfect and not command.endswith(' '):
            yield Completion(' ')
            self._help_set()
            return

        if len(self.tree.options) == 1 and not self.tree.perfect:
            yield Completion(self.tree.options[0][len(last):])
            # yield Completion(self.tree.options[0][len(last):] + ' ')
            return

        # using split() intead of split(' ') eats the final ' '
        words = without_set.split(' ')
        # hardcoded search for words
        if len(words) == 3 and words[0] == 'interfaces' and words[1] in Section.sections():
            word = words[2] if len(words) == 3 else ''
            # for option in Section.interfaces(words[0]):
            prefix = Section.interface_prefix(words[1])
            for option in (f'{prefix}0', f'{prefix}1'):
                yield Completion(option[len(word):])
            self._help_set()
            return

        # tab mid-word
        for option in self.tree.options:
            if not kw.found(option):
                yield Completion(option[len(words[-1]):])
        self._help_set()
