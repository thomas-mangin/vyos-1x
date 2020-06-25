import os
import re
import json
from copy import deepcopy

from vyos.xml import load_configuration
from vyos.xml import kw

from vyos.conf.local import commit

DEBUG = True


def _unquote(value):
    if not value:
        return value
    if value.startswith("'"):
        value = value[1:]
    if value.endswith("'"):
        value = value[:-1]
    return value


class VyOSError(Exception):
    pass


class Config(object):
    __conf = {
        'live': {},
        'edit': {},
    }
    __level = {}

    # list of the commit currently editing
    __editing = []

    xml = load_configuration()

    def __init__(self, commit=None):
        self._commit = commit if commit else os.getpid()
        if self._commit not in self.__conf['edit']:
            self.__conf['edit'][self._commit] = deepcopy(self.__conf['live'])
            self.__level[self._commit] = []

    def _full_path(self, path):
        if isinstance(path, str):
            path = re.split(r'\s+', path)
        return self.__level[self._commit] + path

    def set_level(self, path):
        if isinstance(path, str):
            self.__level[self._commit] = re.split(' ', path) if path else []
        elif isinstance(path, list):
            self.__level[self._commit] = path.copy()

    def get_level(self):
        return(self.__level[self._commit].copy())

    def _find(self, path, config):
        for p in path:
            if p in config:
                config = config[p]
                continue
            break
        else:
            return config
        return {}

    def _get_live(self):
        return self.__conf['live']

    def _get_edit(self):
        return self.__conf['edit'][self._commit]

    def _find_live(self, lpath):
        return self._find(lpath, self._get_live())

    def _find_edit(self, lpath):
        return self._find(lpath, self._get_edit())

    def _go_edit(self, lpath):
        conf = self._get_edit()
        for p in lpath:
            if p not in conf:
                conf[p] = {}
            conf = conf[p]
        return conf

    def exists(self, path):
        lpath = self._full_path(path)
        # XXX: need to deal with valueless node
        if self._find_edit(lpath):
            return True
        return False

    def exists_effective(self, path):
        lpath = self._full_path(path)
        if self._find_live(lpath):
            return True
        return False

    def session_changed(self):
        return self._commit in self.editing

    def in_session(self):
        # TODO
        return False

    def show(self, lpath=[], default=None, effective=False, format='raw'):
        def _show_leaf(depth, inside, edit, live):
            k = inside[-1]
            tab = '   ' * depth

            if self.is_multi(inside):
                if k in edit and k in live:
                    for v in edit[k]:
                        yield f'{tab}{k} {v}'
                elif k in edit:
                    for v in edit[k]:
                        yield f'+{tab[:-1]}{k} {v}'
                elif k in live:
                    for v in live[k]:
                        yield f'-{tab[:-1]}{k} {v}'
            else:
                if k in edit and k in live:
                    yield f'{tab}{k} {edit[k]}'
                elif k in edit:
                    yield f'+{tab[:-1]}{k} {edit[k]}'
                elif k in live:
                    yield f'-{tab[:-1]}{k} {live[k]}'

        def _show_tag(depth, inside, tag, edit, live):
            tab = '   ' * depth
            keys = list(set(edit).union(set(live)))
            keys.sort()
            for k in keys:
                new_edit = edit[k] if k in edit else {}
                new_live = live[k] if k in live else {}
                if k in edit and k in live:
                    if new_edit or new_live:
                        yield f'{tab}{tag} {k} {{'
                        yield from _show_node(depth + 1, inside + [k], new_edit, new_live)  # 1
                        yield f'{tab}}}'
                    else:
                        yield f'{tab}{tag} {k}'
                elif k in edit:
                    if new_edit:
                        yield f'+{tab[:-1]}{tag} {k} {{'
                        yield from _show_node(depth + 1, inside + [k], new_edit, new_live)  # 2
                        yield f'+{tab[:-1]}}}'
                    else:
                        yield f'+{tab[:-1]}{tag} {k}'
                elif k in live:
                    if new_live:
                        yield f'-{tab[:-1]}{tag} {k} {{'
                        yield from _show_node(depth + 1, inside + [k], new_edit, new_live)  # 3
                        yield f'-{tab[:-1]}}}'
                    else:
                        yield f'-{tab[:-1]}{tag} {k}'

        def _show_node(depth, inside, edit, live):
            if not edit and not live:
                return
            tab = '   ' * depth

            if isinstance(edit, list) and isinstance(live, list):
                keys = list(set(edit).union(set(live)))
                keys.sort()
                while keys:
                    k = keys.pop(0)
                    if k in edit and k in live:
                        yield f'{tab}{inside[-1]} {k}'
                    elif k in edit:
                        yield f'+{tab[:-1]}{inside[-1]} {k}'
                    elif k in live:
                        yield f'-{tab[:-1]}{inside[-1]} {k}'
                return
            elif isinstance(edit, list):
                for k in edit:
                    yield f'+{tab[:-1]}{inside[-1]} {k}'
                return
            elif isinstance(live, list):
                for k in live:
                    yield f'-{tab[:-1]}{inside[-1]} {k}'
                return

            keys = list(set(edit).union(set(live)))
            keys.sort()
            while keys:
                k = keys.pop(0)

                if self.is_leaf(inside + [k]):
                    yield from _show_leaf(depth, inside + [k], edit, live)
                    continue

                new_live = live[k] if k in live else {}
                new_edit = edit[k] if k in edit else {}

                if self.is_tag(inside + [k]):
                    yield from _show_tag(depth, inside + [k], k, new_edit, new_live)
                    continue

                if k in edit and k in live:
                    if new_edit or new_live:
                        yield f'{tab}{k} {{'
                        yield from _show_node(depth + 1, inside + [k], new_edit, new_live)  # 4
                        yield f'{tab}}}'
                    else:
                        yield f'{tab}{k}'
                elif k in edit:
                    if new_edit:
                        yield f'+{tab[:-1]}{k} {{'
                        yield from _show_node(depth + 1, inside + [k], new_edit, new_live)  # 5
                        yield f'+{tab[:-1]}}}'
                    else:
                        yield f'+{tab[:-1]}{k}'
                elif k in live:
                    if new_live:
                        yield f'-{tab[:-1]}{k} {{'
                        yield from _show_node(depth + 1, inside + [k], new_edit, new_live)  # 6
                        yield f'-{tab[:-1]}}}'
                    else:
                        yield f'-{tab[:-1]}{k}'

        edit = self._find_edit(lpath)
        live = self._find_live(lpath)
        return '\n'.join(_show_node(0, [], edit, live)) + '\n'

    def show_config(self, path=[], default=None, effective=False, format='raw'):
        lpath = self._full_path(path)
        conf = self._find_live(lpath) if effective else self._find_edit(lpath)
        return json.dumps(conf, indent=3)

    def get_config_dict(self, path=[], effective=False):
        lpath = self._full_path(path)
        conf = self.__live if effective else self._get_edit()
        conf = self._find(lpath, conf)
        return deepcopy(conf)

    def is_multi(self, path):
        return self.xml.is_multi(self._full_path(path))

    def is_tag(self, path):
        return self.xml.is_tag(self._full_path(path))

    def is_leaf(self, path):
        return self.xml.is_leaf(self._full_path(path))

    def return_value(self, path, default=None):
        lpath = self._full_path(path)
        value = self._find_edit(lpath)
        if not value:
            return default
        return value

    def return_effective_value(self, path, default=None):
        lpath = self._full_path(path)
        value = self._find_live(lpath)
        if not value:
            return default
        return value

    def return_values(self, path, default=[]):
        lpath = self._full_path(path)
        values = self._find_edit(lpath)
        if not values:
            return default.copy()
        if self.is_tag(lpath):
            values = list(values.keys())
        return values

    def return_effective_values(self, path, default=[]):
        lpath = self._full_path(path)
        values = self._find_live(lpath)
        if not values:
            return default.copy()
        if self.is_tag(lpath):
            values = list(values.keys())
        return values

    def list_nodes(self, path, default=[]):
        lpath = self._full_path(path)
        values = self._find_edit(lpath)
        if not values:
            return default.copy()
        return list(values.keys())

    def list_effective_nodes(self, path, default=[]):
        lpath = self._full_path(path)
        values = self._find_live(lpath)
        if not values:
            return default.copy()
        return list(values.keys())

    #

    def changed(self, path):
        lpath = self._full_path(path)
        changed = self._find_live(lpath) != self._find_edit(lpath)
        return changed

    #

    def set(self, lpath, value=None):
        if not self.xml.exists(lpath[:-1]):
            return False

        if value is None:
            value = lpath[-1]
            lpath = lpath[:-1]

        value = _unquote(value)


        # XXX: Do we deal with valueless node correctly ?
        if self.is_multi(lpath):
            self._go_edit(lpath[:-1]).setdefault(lpath[-1], []).append(value)
        else:
            root = self._go_edit(lpath[:-1])
            if self.is_leaf(lpath):
                if self.is_multi(lpath):
                    root.setdefault(lpath[-1], [])
                    root[lpath[-1]].append(value)
                else:
                    root.setdefault(lpath[-1], [])
                    root[lpath[-1]] = value
            else:
                root.setdefault(lpath[-1],{})
                root[lpath[-1]].update({value: {}})
        return True

    def _cleanup(self,lpath):
        conf = self._go_edit(lpath)
        keys = list(conf.keys())
        while keys:
            k = keys.pop()
            if not conf[k]:
                del conf[k]
                self._cleanup(lpath[:-1])

    def _delete(self, lpath, value):
        conf = self._go_edit(lpath)

        if self.is_multi(lpath):
            if self.is_leaf(lpath):
                conf.remove(value)
            else:
                del conf[value]
            self._cleanup(lpath[:-1])
        else:
            del conf[value]

    def delete(self, path, value=None):
        lpath = self._full_path(path)
        if value is None:
            length = len(lpath)
            if not length:
                return
            if len(lpath) == 1:
                return self._delete([],lpath[0])
            return self._delete(lpath[:-1], lpath[-1])
        self._delete(lpath, value)

    def comment(self, path, value=None):
        # TODO
        pass

    def commit(self, memory_only=False):
        if memory_only or commit(self):
            self.__conf['live'] = deepcopy(self.__conf['edit'][self._commit])
            return True
        return False

    def discard(self):
        # TODO
        pass

    # XXX: should be load()
    def load_config(self, fname, verbose=False):
        with open(fname, 'r') as r:
            for raw in r.readlines():
                line = raw.strip()
                if line.startswith('#'):
                    continue
                elif line.startswith('set '):
                    if verbose:
                        print(f'loading: {line}')
                    if not self.set(line[4:].split()):
                        print(f'-- N/A : {line}')
                elif line.startswith('commit'):
                    if verbose:
                        print('commiting')
                    if self.commit():
                        print('commited')
                else:
                    if DEBUG:
                        print(f'{line}')
                        from vyos.cli.command import run
                        run(self, line)
                    else:
                        raise VyOSError(f'invalid line "{raw.rstrip()}"')
        return True

    # XXX: should be save()
    def save_config(self, fname):
        if os.path.exists(fname):
            os.rename(fname, f'{fname}.backup')
        with open(fname, 'w') as w:
            w.write('# vyos-config-version: 0\n')
            w.write(self.commands([]))
        # XXX: permission and ownership of the file if root

    def commands(self, lpath):
        def _save(inside, conf):
            if not conf:
                yield ' '.join(inside)
                return

            for k, v in conf.items():
                if isinstance(v, dict):
                    yield from _save(inside + [k], conf[k])
                elif isinstance(v, list):
                    for o in v:
                        yield from _save(inside + [k, o], {})
                else:
                    yield ' '.join(inside + [k, v])

        conf = self._find_live(lpath)
        return 'set ' + '\nset '.join(_save([], conf)) + '\n'

    # what is it in Config / ConfigSession?
    def install_image(self, url):
        # TODO
        return

    # what is it in Config / ConfigSession?
    def remove_image(self, name):
        # TODO
        return

    # what is it in Config / ConfigSession?
    def generate(self, path):
        # TODO
        return
