import os
import sys
import pkgutil
import importlib
from copy import deepcopy

from pprint import pprint

from vyos.xml import kw
from vyos.xml import load_configuration

USE_PROCESS = True
USE_THREAD = False


if USE_PROCESS:
    from multiprocessing import Process as Runner
    from multiprocessing import Queue
    PARALLEL = True
elif USE_THREAD:
    from threading import Thread as Runner
    from queue import Queue
    PARALLEL = True
else:
    PARALLEL = False


def _import_all(package_name):
    package = sys.modules[package_name]
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        yield f'{package_name}.{name}'


def import_all(package_name):
    __import__('vyos.modules.configuration')
    m = {}
    for name in _import_all(package_name):
        try:
            m[name] = importlib.import_module(name,'vyos.modules.configuration')
        except ImportError as exc:
            print(f'issue: could not import {name}')
            print(str(exc))
    return m


xml = load_configuration()

_module_script = None


def init_modules():
    # This import all the configuration modules using python __import__
    # Not all modules may be able to be imported
    # # Not all modules have this owner string, some are prepended by sudo
    global _module_script
    if _module_script is not None:
        return
    module_code = import_all('vyos.modules.configuration')
    _module_script = dict(('${vyos_conf_scripts_dir}/%s.py' % name.split(".")[-1], module_code[name]) for name in module_code)


def _changes(conf):
    priorities = list(xml[kw.priorities])
    priorities.sort()

    for priority in priorities:
        for path in xml[kw.priorities][priority]:
            if path not in xml[kw.owners]:
                print(f'warning: priority {priority}: {path} has a priority but no owner')
                continue

            script = xml[kw.owners][path]
            if script not in _module_script:
                print(f'warning: priority {priority}: could not find module for {path}')
                continue

            module = _module_script[script]

            if path in xml[kw.tags]:
                nodes = set(conf.list_nodes(path)) | set(conf.list_effective_nodes(path))
                for node in nodes:
                    if conf.changed(path):
                        yield(module, path)
                continue

            if conf.changed(path):
                # This is a "normal" node, just run on the whole node
                yield(module, path)


def parrallel(to_commit, function, queue):
    started = []

    for module, path, name, config in to_commit:
        if not PARALLEL:
            function(name, config, queue)
            continue

        # Otherwise set_level / get_level will fight !
        t = Runner(target=function, args=(name, config, queue))
        # useless for multiprocessing
        t.daemon = True
        t.start()
        started.append(t)

    # XXX: timer/alarm here to make sure we do not get stuck
    if not PARALLEL:
        return

    for s in started:
        s.join()


def commit(config):
    to_commit = []
    # Main Executor
    # First we run get_config, because the configurator gets the tag value from an
    # env variable, we need to set that in advance

    modules_to_run = list(_changes(config))

    # getting the parsed configuration for that path
    for module, path in modules_to_run:
        names = set(config.return_values(path)) | set(config.return_effective_values(path))
        for name in names:
            # the module writers did not expect that we would loop !
            config.set_level([])

            # Get the tag and pass it to the configurator
            os.environ["VYOS_TAGNODE_VALUE"] = name
            config_dict = module.get_config()
            to_commit.append((module, path, name, config_dict))

    # Executing the verification
    for module, _, _, config_dict in to_commit:
        try:
            module.verify(config_dict)
        except Exception as exc:
            print(f'failed to validate data for {path}')
            print(str(exc))
            print('aborting commit')

    # generate the config

    def _generate(name, config_dict, queue):
        print(f"generate {path} {name}")
        # the return code of modules are currently ... unpredictable, assume it works
        module.generate(config_dict)
        print(f"generate {path} {name} done.")
        queue.put((module, path))

    generated = Queue()
    parrallel(to_commit, _generate, generated)

    if generated.qsize() != len(to_commit):
        print('could not generate the configuration for some modules')
        return False

    # applying the changes

    def _apply(name, config_dict, queue):
        # the return code of modules are currently ... unpredictable, assume it works
        print(f"Applying {path} {name}")
        module.apply(config_dict)
        print(f"Applying {path} {name} done.")
        queue.put((module, path))

    applied = Queue()
    parrallel(to_commit, _apply, applied)

    if applied.qsize() == len(to_commit):
        print('configuration updated')
        return True

    # Deal with failure, rollback, etc.
    print('configuration update failed')
    return False
