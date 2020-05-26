import argparse

from vyos.cli.command.exit import exit


_dispatch = {
    'confirm': lambda _:_,
    'comment': lambda _:_,
    'commit': lambda _:_,
    'commit-confirm': lambda _:_,
    'compare': lambda _:_,
    'copy': lambda _:_,
    'delete': lambda _:_,
    'discard': lambda _:_,
    'edit': lambda _:_,
    'exit': exit,
    'load': lambda _:_,
    'loadkey': lambda _:_,
    'merge': lambda _:_,
    'rename': lambda _:_,
    'rollback': lambda _:_,
    'run': lambda _:_,
    'save': lambda _:_,
    'set': lambda _:_,
    'show': lambda _:_,
}


def dispatch(notification):
    def _accept(self, **kargs):
        # notification.text = '\n'.join(_ for _ in dir(self) if _[0] == 't')

        command = self.document.text
        if not command:
            notification.text = 'no command'
            return

        order = command.split()[0]
        if order in dispatch:
            _dispatch[order](command)

        notification.text = 'received: ' + self.document.text

    return _accept

