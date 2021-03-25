#!/usr/bin/env python
"""
:mod:`virt_switch` -- Controller virtual switches
=================================================

.. module:: controller.bin.virt_switch
"""


import subprocess
import argparse
import sys

from virt.lib.core import log_handler
from virt.lib.common import network


log = log_handler.get_logger(__name__)


__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
def parse_args():
    mode_list = network.get_vswitch_mode()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--debug', help='Display debug messages', default=False,
        action='store_true')

    switch_parser = parser.add_argument_group('Manage a virtual switch')
    switch_parser.add_argument(
        '--mgmt', action='store_true',
        help='Create a management network')
    switch_parser.add_argument('-n', '--name', help='A name of network')
    switch_parser.add_argument(
        '--br-iface', help='A name of network bridge interface i.e.) test-br0')

    switch_parser.add_argument(
        '--iface', help='Interface name as an external port for the switch')

    switch_parser.add_argument(
        '-m', '--mode',
        help='A mode of virtual switch. choices=%s ' % mode_list,
    )

    if 'macvtap' in mode_list:
        switch_parser.add_argument(
            '--macvtap-mode',
            help='A mode of macvtap. choices=[bridge|private|vepa|passthrough] '
                 'Default=bridge',
            default='bridge',
        )

    switch_parser.add_argument(
        '--ip-addr',
        help='IP address and netmask of the virtual switch. '
             'e.g.) 192.168.0.1/24 or 192.168.0.1/255.255.255.0')

    switch_parser.add_argument(
        '--show', action='store_true', help='Show defined network')
    switch_parser.add_argument(
        '--remove', action='store_true', help='Remove the network')

    options = parser.parse_args()

    if options.debug:
        log.setLevel(log_handler.logging.DEBUG)

    return parser, options


def show():
    log.info('vSwitch: %s' % ', '.join([
        '"' + name + '"' for name in network.get_vswitch_list()
    ]))


def set_mgmt_network(options):
    if options.remove:
        mgmt_network = network.get_mgmt_vswitch()
        mgmt_network.remove()
        return

    if not options.iface:
        log.error(
            'Missing "--iface" option. Cannot create a vswitch for a '
            'management network')
        sys.exit(1)

    mgmt_network = network.get_mgmt_vswitch(iface=options.iface)
    mgmt_network.create()


def set_test_network(options):
    if options.remove:
        virt_switch = network.get_vswitch(**options.__dict__)
        virt_switch.remove()
        return

    if not options.mode:
        log.error('Missing "--mode" option')
        sys.exit(1)

    virt_switch = network.get_vswitch(**options.__dict__)
    virt_switch.create()


def main():
    parser, options = parse_args()

    if options.show:
        return show()

    if options.mgmt:
        return set_mgmt_network(options)

    if options.name:
        return set_test_network(options)

    parser.print_help()


if __name__ == '__main__':
    main()
