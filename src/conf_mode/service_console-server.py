#!/usr/bin/env python3
#
# Copyright (C) 2018-2020 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from sys import exit

from vyos.config import Config
from vyos.configdict import dict_merge
from vyos.template import render
from vyos.util import default_mangler
from vyos.util import call
from vyos.xml import defaults
from vyos import ConfigError

config_file = r'/run/conserver/conserver.cf'

def get_config():
    conf = Config(mangler=default_mangler)
    base = ['service', 'console-server']

    if not conf.exists(base):
        return None

    # Retrieve CLI representation as dictionary
    proxy = conf.get_config_dict(base)
    # The retrieved dictionary will look something like this:
    #
    # {'device': {'usb0b2.4p1.0': {'speed': '9600'},
    #             'usb0b2.4p1.1': {'data_bits': '8',
    #                              'parity': 'none',
    #                              'speed': '115200',
    #                              'stop_bits': '2'}}}

    # We have gathered the dict representation of the CLI, but there are default
    # options which we need to update into the dictionary retrived.
    default_values = defaults(base + ['device'])
    for device in proxy['device'].keys():
        tmp = dict_merge(default_values, proxy['device'][device])
        proxy['device'][device] = tmp

    return proxy

def verify(proxy):
    if not proxy:
        return None

    for device in proxy['device']:
        keys = proxy['device'][device].keys()
        if 'speed' not in keys:
            raise ConfigError(f'Serial port speed must be defined for "{tmp}"!')

        if 'ssh' in keys:
            ssh_keys = proxy['device'][device]['ssh'].keys()
            if 'port' not in ssh_keys:
                raise ConfigError(f'SSH port must be defined for "{tmp}"!')

    return None

def generate(proxy):
    if not proxy:
        return None

    render(config_file, 'conserver/conserver.conf.tmpl', proxy)
    return None

def apply(proxy):
    call('systemctl stop dropbear@*.service conserver-server.service')

    if not proxy:
        if os.path.isfile(config_file):
            os.unlink(config_file)
        return None

    call('systemctl restart conserver-server.service')

    for device in proxy['device']:
        if 'ssh' in proxy['device'][device].keys():
            port = proxy['device'][device]['ssh']['port']
            call(f'systemctl restart dropbear@{device}.service')

    return None

if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        exit(1)
