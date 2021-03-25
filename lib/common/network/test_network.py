"""
:mod:`test_network` -- The test script template
===========================================

.. module:: virt.lib.common.network.test_network
"""

import re

import netaddr

from virt.lib.core import exception


__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
def get_mac_addr(ip_addr, mgmt_network=False):
    if ip_addr is None:
        return None

    if isinstance(ip_addr, (str, unicode)):
        ip_addr = netaddr.IPNetwork(ip_addr)

    # Use b2:<netmask> which is a locally administrated address range
    return ':'.join(
        digit.encode('hex') for digit in (
            ('b4' if mgmt_network else 'b2') +
            ('00' if mgmt_network else format(ip_addr.prefixlen, '02x')) +
            format(int(ip_addr.ip), '08x')).decode('hex'))


def get_ip_addr(mac_addr):
    if not re.match(r'([0-9a-f]{2}:){5}([0-9a-f]{2})', mac_addr, re.I):
        raise exception.ValueException('MAC address "%s" is invalid' % mac_addr)
    return '.'.join(
        [str(int(octet, 16)) for octet in mac_addr.split(':')[2:]]
    ) + '/' + str(int(mac_addr.split(':')[1]))


def get_hostname(ip_addr=None, mac_addr=None):
    if ip_addr:
        if isinstance(ip_addr, (str,)):
            ip_addr = netaddr.IPNetwork(ip_addr)
    elif mac_addr:
        ip_addr = netaddr.IPNetwork(get_ip_addr(mac_addr))
        f_mac_addr = mac_addr.split(':')[0].lower()
        if f_mac_addr != 'b2' and f_mac_addr != 'b4':
            # Reject invalid MAC address by returning None
            return None

    return 'vm-%s-%s' % (
        ip_addr.ip.words[2], ip_addr.ip.words[3]
    )
