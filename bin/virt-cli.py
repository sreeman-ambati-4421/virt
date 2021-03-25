#!/usr/bin/env python
"""
:mod:`virt_cli` -- Controller virt module CLI interface
=======================================================

.. module:: controller.bin.virt_cli
"""

import re
import sys
import logging
import argparse

from virt.lib.core import log_handler
from virt.lib.common import virtual_machine
from virt.lib.common.virtual_machine import template


__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
log = log_handler.get_logger(__name__)


def parse_args():
    template_list = template.get_template_list()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--debug', help='Display debug messages', default=False,
        action='store_true')
    parser.add_argument(
        '--name',
        help='A name of the virtual machine. If not given, will use the '
             'automatically assigned name but "--mgmt-ip-addr" is required. ')
    parser.add_argument(
        '--mgmt-ip-addr',
        help='Management IP address of a new virtual machine. If not given, '
             '"--name" must be given')

    # Pool related options
    pool_parser = parser.add_argument_group('Create and delete pools')
    pool_parser.add_argument(
        '-p', '--pool',
        help='Directory of storage pool where template and vm images will be '
             'stored')

    # Deploy related options
    create_parser = parser.add_argument_group(
        'Create and delete a virtual machine')
    create_parser.add_argument(
        '-t', '--template', dest='template',
        help='Template name. choice=%s' % template_list)
    create_parser.add_argument(
        '--network', action='append', nargs=2,
        help='A name of test network with a mapped IP address/Prefix'
             'i.e.) --network "Test Network #1" 192.168.0.1/23 will add a NIC '
             'which will be connected to "Test Network #1" and the static IP '
             '192.168.0.1/23 will be assigned to it. You can define this '
             'multiple times')
    create_parser.add_argument(
        '--exist',
        help='Specify a policy to handle existing virtual machine or virtual '
             'disk. Default=None, namely will raise exception if there are '
             'already existing ones. choices=[None|overwrite|reuse]',
        default=None)
    create_parser.add_argument(
        '--remove', help='Destroy pool or template', action='store_true')
    create_parser.add_argument(
        '--cpu', default=1, type=int,
        help='A number of vCPUs to be assigned to the virtual machine. '
             'Default=1')
    create_parser.add_argument(
        '--memory', default=512, type=int,
        help='A size of memory of the virtual machine in MB. Default=512')

    ctrl_parser = parser.add_argument_group('Control virtual machine')
    ctrl_parser.add_argument(
        '--oper',
        help='choices=[on|off|reset] to control virtual machine. '
             'Need --start-ip and --end-ip options')
    ctrl_parser.add_argument(
        '-g', '--get-mgmt-ip-addr',
        help='Return a management IP address of the virtual machine. Expected '
             'value is a IP network in x.x.x.x/x i.e.) 10.13.240.0/20 which is '
             'a range where the network IP address should be belong to. '
    )


    options = parser.parse_args()

    if options.debug:
        logging.root.level = logging.DEBUG

    if options.pool:
        return parser, options

    if not options.name and not options.mgmt_ip_addr:
        log.error('"--mgmt-ip_addr" or "--name" must be given')
        sys.exit(1)

    return parser, options


def set_pool(options):
    pool = template.get_pool(options.pool)

    if options.remove:
        return pool.remove()

    pool.create()


def create(options):
    _template = template.get_template(options.template)

    test_ip_addr_dict = {}
    network_list = options.network or []

    for network_name, ip_addr in network_list:
        if not re.match('\d+\.\d+\.\d+\.\d+/\d+', ip_addr):
            log.error('IP address %s is not in format x.x.x.x/x' % ip_addr)
            sys.exit(1)

        if network_name not in test_ip_addr_dict:
            test_ip_addr_dict[network_name] = [ip_addr]
        else:
            test_ip_addr_dict[network_name].append(ip_addr)

    _template.create(
        name=options.name,
        mgmt_ip_addr=options.mgmt_ip_addr,
        test_ip_addr_dict=test_ip_addr_dict,
        cpu=options.cpu,
        memory=options.memory,
        exist=options.exist,
    )

    return


def remove(options):
    if not options.mgmt_ip_addr and not options.name:
        log.error('Both "--mgmt-ip-addr" and "--name" cannot be "None"')
        sys.exit(1)

    name = template.BaseTemplate._get_name(options.mgmt_ip_addr, options.name)
    vm_manager = virtual_machine.get_vm_manager()
    log.info('Powering off the virtual machine %s ... ' % name)
    vm_manager.power(name=name, oper='off')
    log.info('Removing the virtual machine %s ... ' % name)
    vm_manager.remove(name)

    return


def set_oper(options):
    vm_manager = virtual_machine.get_vm_manager()
    name = template.BaseTemplate._get_name(options.mgmt_ip_addr, options.name)
    vm_manager.power(name=name, oper=options.oper)

    return


def get_mgmt_ip_addr(options):
    vm_manager = virtual_machine.get_vm_manager()
    mgmt_ip_addr = vm_manager.get_mgmt_ip_addr(
        vm_name=options.name, ip_network=options.get_mgmt_ip_addr)
    log.info('Management IP address: %s' % mgmt_ip_addr)

    return


def main():
    parser, options = parse_args()

    # Handle to get a maangement IP address
    if options.get_mgmt_ip_addr:
        return get_mgmt_ip_addr(options)

    # Handle pool
    if options.pool:
        return set_pool(options)

    # Handle destroy
    if options.remove:
        return remove(options)

    # Handle template
    if options.template:
        return create(options)

    if options.oper:
        return set_oper(options)

    log.error(
        'Require at least "--pool", "--remove", "--oper", "--get-mgmt-ip-addr" '
        'or "--template"')


if __name__ == '__main__':
    main()
