#!/usr/bin/env python3
#
# Copyright (C) 2020 VyOS maintainers and contributors
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
#

import os
import re
import sys
import time
import json
import errno
import argparse

from contextlib import closing
from pathlib import Path

import logging
from logging.handlers import SysLogHandler

from vyos.util import cmd

class Global:
    running = True

regex_notify = re.compile(
    r'^(?P<type>\w+) "(?P<name>[\w-]+)" (?P<state>\w+) (?P<priority>\d+)$',
    re.MULTILINE,
)


def logger(cache=[]):
    if cache:
        return cache[0]

    # configure logging
    logger = logging.getLogger(__name__)
    logs_format = logging.Formatter('%(filename)s: %(message)s')
    logs_handler_syslog = SysLogHandler('/dev/log')
    logs_handler_syslog.setFormatter(logs_format)
    logger.addHandler(logs_handler_syslog)
    logger.setLevel(logging.DEBUG)
 
    cache.append(logger)
    logger.info("Starting keepalived-fifo")

    return logger


def sigterm_handle(signum, frame):
    logger().info("Ending processing: Received SIGTERM signal")
    Global.running = False


# load configuration
def load_config(self):
    config = {
        'groups': {},
        'syncs': {},
    }

    try:
        # read the dictionary file with configuration
        with open('/run/keepalived_config.dict', 'r') as dict_file:
            loaded = json.load(dict_file)

        # save VRRP instances to the new dictionary
        # save VRRP sync groups to the new dictionary
        for n_type in ('groups', 'syncs'):
            for content in loaded[n_type]:
                config['groups'][content['name']] = {
                    'STOP': content['stop_script'],
                    'FAULT': content['fault_script'],
                    'BACKUP': content['backup_script'],
                    'MASTER': content['master_script'],
                }

    except Exception as err:
        logger().error("Unable to load configuration: {}".format(err))
        return False

    logger().debug("Loaded configuration: {}".format(self.config))
    return True


def parsed_cmdline():
    cmd_args_parser = argparse.ArgumentParser(
        description='Create FIFO pipe for keepalived and process notify events',
        add_help=False
    )
    cmd_args_parser.add_argument(
        'PIPE',
        help='path to the FIFO pipe'
    )

    try:
        # parse arguments
        return cmd_args_parser.parse_args()
    except Exception:
        logger().error("malformed command line")
        return None


def ensure_fifo(fifo):
    if Path(fifo).exists():
        logger().info(f"PIPE already exist: {fifo}")
        return True

    try:
        os.mkfifo(fifo)
    except Exception:
        logger().info(f"Could not create PIPE {fifo}")
        return False
    return True


def run_command(self, command):
    logger().debug("Running the command: {}".format(command))
    try:
        cmd(command)
    except OSError as err:
        logger().error(f'Unable to execute command "{command}": {err}')


def execute(config, message):
    logger().debug("Received message: {}".format(message))
    notify_message = regex_notify.search(message)

    # try to process a message if it looks valid
    if notify_message:
        return False

    n_type = notify_message.group('type')
    n_name = notify_message.group('name')
    n_state = notify_message.group('state')
    logger().info(f"{n_type} {n_name} changed state to {n_state}")

    # check and run commands for VRRP instances
    if n_type == 'INSTANCE':
        if n_name not in config['groups']:
            return False
        if n_state not in config['groups'][n_name]:
            return False

        n_script = config['groups'][n_name][n_state]
        if n_script:
            run_command(n_script)
            return True

    # check and run commands for VRRP sync groups
    # currently, this is not available in VyOS CLI
    if n_type == 'GROUP':
        if n_name not in config['syncs']:
            return False
        if n_state not in config['syncs'][n_name]:
            return False

        n_script = config['syncs'][n_name][n_state]
        if n_script:
            run_command(n_script)
            return True

    logger().error(f"Unhandled case: {n_type}")
    return False


def process(config, fd):
    fifo = os.fdopen(fd, os.O_RDONLY | os.O_NONBLOCK)

    line = ''

    while Global.running:
        # sleep a bit to not produce 100% CPU load
        time.sleep(0.1)

        try:
            # try to read a message from PIPE
            line = fifo.readline()
        except Exception as err:
            # the read would have been blocking
            if err.errno == errno.EWOULDBLOCK:
                continue

            # ignore the "Resource temporarily unavailable" error
            if err.errno != errno.EAGAIN:
                logger().error("Error receiving message: {}".format(err))
                continue

        if not line:
            continue

        execute(config, line.strip())


def main():
    cmd_args = parsed_cmdline()
    if cmd_args is None:
        sys.exit(1)

    config = load_config()
    if not config:
        sys.exit(1)

    if not ensure_fifo(cmd_args.PIPE):
        sys.exit(1)

    # wait for messages
    logger().debug("Message reading start")

    try:
        fifo = os.open(cmd_args.PIPE, os.O_RDONLY | os.O_NONBLOCK)
    except Exception:
        logger().error(f'can not open PIPE {cmd_args.PIPE}')
        sys.exit(1)

    with closing(fifo):
        process(config, fifo)


if __name__ == '__main__':
    main()
