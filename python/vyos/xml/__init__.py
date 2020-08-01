# Copyright (C) 2020 VyOS maintainers and contributors
#
# This library is free software; you can redistribute it and/or modify it under the terms of
# the GNU Lesser General Public License as published by the Free Software Foundation;
# either version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with this library;
# if not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA


from vyos.xml import definition
from vyos.xml import load
from vyos.xml import kw


def load_configuration(cache=[]):
    if cache:
        return cache[0]

    xml = definition.XML()

    try:
        from vyos.xml.cache import configuration
        xml.update(configuration.definition)
        cache.append(xml)
    except Exception:
        xml = definition.XML()
        print('no xml configuration cache')
        xml.update(load.xml(load.configuration_definition))

    return xml


# def is_multi(lpath):
#     return load_configuration().is_multi(lpath)


def is_tag(lpath):
    return load_configuration().is_tag(lpath)


def is_leaf(lpath, flat=True):
    return load_configuration().is_leaf(lpath, flat)


def defaults(lpath, flat=False):
    return load_configuration().defaults(lpath, flat)


def multi_to_list(lpath, conf):
    return load_configuration().multi_to_list(lpath, conf)


if __name__ == '__main__':
    print(defaults(['service'], flat=True))
    print(defaults(['service'], flat=False))

    print(is_tag(["system", "login", "user", "vyos", "authentication", "public-keys"]))
    print(is_tag(['protocols', 'static', 'multicast', 'route', '0.0.0.0/0', 'next-hop']))
