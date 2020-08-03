# Copyright 2020 VyOS maintainers and contributors <maintainers@vyos.io>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

from enum import IntFlag, auto

from vyos.config import Config
from vyos.configdict import dict_merge
from vyos.util import get_sub_dict
from vyos.xml import defaults

class ConfigDiffError(Exception):
    """
    Raised on config dict access errors, for example, calling get_value on
    a non-leaf node.
    """
    pass

def enum_to_key(e):
    return e.name.lower()

class Diff(IntFlag):
    MERGE = auto()
    DELETE = auto()
    ADD = auto()
    STABLE = auto()

requires_effective = [enum_to_key(Diff.DELETE)]
target_defaults = [enum_to_key(Diff.MERGE)]

def _key_sets_from_dicts(session_dict, effective_dict):
    session_keys = list(session_dict)
    effective_keys = list(effective_dict)

    ret = {}
    stable_keys = [k for k in session_keys if k in effective_keys]

    ret[enum_to_key(Diff.MERGE)] = session_keys
    ret[enum_to_key(Diff.DELETE)] = [k for k in effective_keys if k not in stable_keys]
    ret[enum_to_key(Diff.ADD)] = [k for k in session_keys if k not in stable_keys]
    ret[enum_to_key(Diff.STABLE)] = stable_keys

    return ret

def _dict_from_key_set(key_set, d):
    # This will always be applied to a key_set obtained from a get_sub_dict,
    # hence there is no possibility of KeyError, as get_sub_dict guarantees
    # a return type of dict
    ret = {k: d[k] for k in key_set}

    return ret

def get_config_diff(config):
    """
    Check type and return ConfigDiff instance.
    """
    if not config or not isinstance(config, Config):
        raise TypeError("argument must me a Config instance")

    return ConfigDiff(config)

class ConfigDiff(object):
    """
    The class of config changes as represented by comparison between the
    session config dict and the effective config dict.
    """
    def __init__(self, config):
        self._level = config.get_level()
        self._session_config_dict = config.get_cached_dict()
        self._effective_config_dict = config.get_cached_dict(effective=True)
        self._mangler = config.mangler

    def _make_path(self, path):
        return Config._make_path(self, path)

    def set_level(self, path):
        return Config.set_level(self, path)

    def get_level(self):
        return Config.get_level(self)

    def get_child_nodes_diff(self, path=[], expand_nodes=Diff(0), no_defaults=False):
        """
        Args:
            path (str|list): config path
            expand_nodes=Diff(0): bit mask of enum indicating for which nodes
                                  to provide full dict; for example, Diff.MERGE
                                  will expand dict['merge'] into dict under
                                  value
            no_detaults=False: if expand_nodes & Diff.MERGE, do not merge default
                               values to ret['merge']

        Returns: dict of lists, representing differences between session
                                and effective config, under path
                 dict['merge']  = session config values
                 dict['delete'] = effective config values, not in session
                 dict['add']    = session config values, not in effective
                 dict['stable'] = config values in both session and effective
        """
        session_dict = get_sub_dict(self._session_config_dict,
                                    self._make_path(path), get_first_key=True)
        effective_dict = get_sub_dict(self._effective_config_dict,
                                      self._make_path(path), get_first_key=True)

        ret = _key_sets_from_dicts(session_dict, effective_dict)

        if not expand_nodes:
            return ret

        for e in Diff:
            if expand_nodes & e:
                k = enum_to_key(e)
                if k in requires_effective:
                    ret[k] = _dict_from_key_set(ret[k], effective_dict)
                else:
                    ret[k] = _dict_from_key_set(ret[k], session_dict)

                if self._mangler:
                    ret[k] = self._mangler(ret[k])

                if k in target_defaults and not no_defaults:
                    default_values = defaults(self._make_path(path))
                    ret[k] = dict_merge(default_values, ret[k])

        return ret

    def get_node_diff(self, path=[], expand_nodes=Diff(0), no_defaults=False):
        """
        Args:
            path (str|list): config path
            expand_nodes=Diff(0): bit mask of enum indicating for which nodes
                                  to provide full dict; for example, Diff.MERGE
                                  will expand dict['merge'] into dict under
                                  value
            no_detaults=False: if expand_nodes & Diff.MERGE, do not merge default
                               values to ret['merge']

        Returns: dict of lists, representing differences between session
                                and effective config, at path
                 dict['merge']  = session config values
                 dict['delete'] = effective config values, not in session
                 dict['add']    = session config values, not in effective
                 dict['stable'] = config values in both session and effective
        """
        session_dict = get_sub_dict(self._session_config_dict, self._make_path(path))
        effective_dict = get_sub_dict(self._effective_config_dict, self._make_path(path))

        ret = _key_sets_from_dicts(session_dict, effective_dict)

        if not expand_nodes:
            return ret

        for e in Diff:
            if expand_nodes & e:
                k = enum_to_key(e)
                if k in requires_effective:
                    ret[k] = _dict_from_key_set(ret[k], effective_dict)
                else:
                    ret[k] = _dict_from_key_set(ret[k], session_dict)

                if self._mangler:
                    ret[k] = self._mangler(ret[k])

                if k in target_defaults and not no_defaults:
                    default_values = defaults(self._make_path(path))
                    ret[k] = dict_merge(default_values, ret[k])

        return ret

    def get_value_diff(self, path=[]):
        """
        Args:
            path (str|list): config path

        Returns: (new, old) tuple of values in session config/effective config
        """
        # one should properly use is_leaf as check; for the moment we will
        # deduce from type, which will not catch call on non-leaf node if None
        new_value_dict = get_sub_dict(self._session_config_dict, self._make_path(path))
        old_value_dict = get_sub_dict(self._effective_config_dict, self._make_path(path))

        new_value = None
        old_value = None
        if new_value_dict:
            new_value = next(iter(new_value_dict.values()))
        if old_value_dict:
            old_value = next(iter(old_value_dict.values()))

        if new_value and isinstance(new_value, dict):
            raise ConfigDiffError("get_value_changed called on non-leaf node")
        if old_value and isinstance(old_value, dict):
            raise ConfigDiffError("get_value_changed called on non-leaf node")

        return new_value, old_value
