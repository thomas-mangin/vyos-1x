import vyos.cli.structure.keywords as kw


class Tree(object):
    def __init__(self, definition):
        self.definition = definition
        # where we are in the defintion tree
        self.search = definition
        # the options which matched the last incomplete world we had
        # or the last word in a list
        self.options = []
        # store all the part of the command we processed
        self.inside = []
        # we have to pass over node twice, the first time when we reach them
        # and once again when the name of the tag was setup (interface dummy dum0)
        # passed_node is set to True when the node is fully passed and
        # is false when only it name was encountered
        self.passed_node = False
        # do we have a perfect match for the last word
        # the word is full and there is no space after it
        self.perfect = False

    def reset(self):
        self.search = self.definition
        self.options = []
        self.inside = []
        self.passed_node = False
        self.perfect = False

    def find(self, command):
        self.reset()

        # using split() intead of split(' ') eats the final ' '
        words = command.split(' ')
        while words:
            word = words.pop(0)

            # complete word
            if word in self.search:
                self.search = self.search[word]
                self.inside.append(word)
                self.passed_node = False
                continue

            # passing a named node
            if self.search.get(kw.node,'') == kw.tagNode:
                # only pass here once per node
                if not self.passed_node:
                    self.inside.append(word)
                    self.passed_node = True
                    continue

            # last incomplete command
            if not words:
                self.options = [_ for _ in self.search if _.startswith(word)]
            return word

        # we got the exact name for the last option
        # but we did not pass it yet, so return it
        self.perfect = True
        return self.inside[-1]

    def _help(self, search):
        yield ('debug', 'help')
        if kw.help in search:
            summary = search[kw.help].get(kw.summary)
            values = search[kw.help].get(kw.valuehelp, [])
            if summary:
                yield(summary,'')
            for value in values:
                yield(value[kw.format], value[kw.description])

    def _constraint(self, search):
        yield ('debug', 'constraint')
        yield('constraint', str(search[kw.error]))

    def _valueless(self, search):
        yield ('debug', 'valuess')
        for option in search:
            if kw.found(option):
                continue
            inner = search[option]
            if kw.help in inner:
                h = inner[kw.help]
                yield (option, h.get(kw.summary,''))

    def help(self):
        search = self.search
        if len(self.options) == 1:
            search = self.search[self.options[0]]
            self.found = True

        yield ('debug', str([_ for _ in search.keys() if '[' in _]))
        yield ('debug', str([_ for _ in search.keys() if '[' not in _]))

        # show the help
        if kw.help in search:
            # on first pass only for the tagNodes
            if not self.passed_node:
                yield from self._help(search)

        # if there is no help the next best is the constraint
        if kw.error in search and kw.help not in search:
            yield from self._constraint(self, search)

        # and the configuration options from there
        if kw.node not in search:
            return

        # only show the details when we passed the tagNode data
        if search[kw.node] == kw.tagNode and not self.passed_node:
            return

        yield from self._valueless(search)
