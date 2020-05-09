#!/usr/bin/env python3

import sys
import pkgutil
import importlib

from vyos.registerer import Registerer


def import_all(package_name):
    package = sys.modules[package_name]
    return {
        name: importlib.import_module(package_name + '.' + name)
        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__)
    }


__MODULES = import_all(__name__)
__all__ = __MODULES.keys()


# register the entry points in the module

registered = Registerer()
for name, module in __MODULES.items():
    registered(name, module.main)
