#!/usr/bin/env python

import platform
import sys
import os
import json
from virt.lib.core import log_handler

__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
log = log_handler.get_logger(__name__)


class BaseIfcfg(object):
    def __init__(self):
        self.hostname = None

    def set_hostname(self):
        raise NotImplementedError

    def set_static_ip_addr(self, iface, mac_addr):
        if mac_addr.split(':')[0] == 'b4':
            log.info('Management NIC is detected.')
            self.hostname = False  # Will get a hostname from DHCP
            return False

        elif not mac_addr.split(':')[0] == 'b2':
            log.info (
                'MAC address %s is not locally administrated address'
                % mac_addr)
            return False

        prefix = int(mac_addr.split(':')[1], 16)
        ip_addr = '.'.join([
            str(int(octet, 16)) for octet in mac_addr.split(':')[2:]])

        log.info('Assign IP address %s/%s to MAC address %s' % (
            ip_addr, prefix, mac_addr
        ))

        self.set_ip_addr(iface, ip_addr, prefix)

        if self.hostname is None:
            self.hostname = 'vm-{}-{}'.format(*ip_addr.split('.')[2:])

        return True

    def set_ip_addr(self, iface, ip_addr, prefix):
        raise NotImplementedError

    def run(self):
        self.set_hostname()


class Linux(BaseIfcfg):
    def __init__(self):
        super(Linux, self).__init__()

    def set_hostname(self):
        if self.hostname:
            log.info('Set the hostname to %s' % self.hostname)
            os.system('hostname %s' % self.hostname)
        else:
            log.info('Hostname is not found. Skip to configure')

    def set_ip_addr(self, iface, ip_addr, prefix):
        os.system('ip addr add %(ip_addr)s/%(prefix)s dev %(iface)s' % {
            'iface': iface, 'ip_addr': ip_addr, 'prefix': prefix,
        })
        os.system('ip link set dev %(iface)s up' % {'iface': iface})

        return True

    def run(self):
        for iface in os.listdir('/sys/class/net'):
            with open('/sys/class/net/%s/address' % iface, 'r') as fileobj:
                mac_addr = fileobj.read().strip()

            self.set_static_ip_addr(iface, mac_addr)
        super(Linux, self).run()


class Windows(BaseIfcfg):
    def __init__(self):
        super(Windows, self).__init__()

    def set_hostname(self):
        if self.hostname:
            os.system(
                'netdom renamecomputer %%COMPUTERNAME%% /Newname %s /Force'
                % self.hostname)
        else:
            log.info('Hostname is not found. Skip to configure')

    def set_ip_addr(self, iface, ip_addr, prefix):
        # Disable DHCP
        os.system(
            'powershell "& {set-netipinterface -interfacealias \'%s\' '
            '-dhcp disabled -policystore persistentstore}' % iface
        )

        # Remove any assigned IP address
        os.system(
            'powershell "& {remove-netipaddress -interfacealias \'%s\' '
            '-confirm:$false' % iface
        )

        # Assign a static IP address
        os.system(
            'powershell "& {new-netipaddress -interfacealias \'%s\' '
            '-ipaddress %s -prefixlength %s} -confirm:$false' % (
                iface, ip_addr, prefix
            )
        )

    def run(self):
        output = os.popen(
            'powershell "& {gwmi win32_networkadapter} | '
            'select Name,NetConnectionID,MACAddress | convertto-json"'
        ).read()
        iface_list = json.loads(output)

        for iface in iface_list:
            if 'NetConnectionID' not in iface or not iface['NetConnectionID']:
                log.info (
                    '"%s" does not have a valid NetConnectionID name. Skip.'
                    % iface['Name'])
                continue
            elif not iface['MACAddress']:
                log.info ('"%s" does not have a valid MAC address. Skip.'
                       % (iface['NetConnectionID']))
                continue
            mac_addr = iface['MACAddress'].lower()
            self.set_static_ip_addr(iface['NetConnectionID'], mac_addr)

        super(Windows, self).run()


def main():
    if platform.system() == 'Linux':
        ifcfg = Linux()
    elif platform.system() == 'Windows':
        ifcfg = Windows()
    else:
        raise NotImplemented('Not supported OS type %s' % platform.system())

    ifcfg.run()

    return True


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
