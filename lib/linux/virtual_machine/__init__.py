import netaddr
import json

from xml.etree import ElementTree

from virt.lib.core import exe
from virt.lib.core import exception
from virt.lib.core import log_handler
from virt.lib.common.virtual_machine import BaseManager
from virt.lib.linux.virtual_machine import domain


log = log_handler.get_logger(__name__)


class LibvirtManager(BaseManager):
    @classmethod
    def _get_network(cls, vm_name):
        """Run qemu-agent command to get guest-network-get-interfaces"""
        output = exe.block_run([
            'virsh', 'qemu-agent-command', vm_name,
            '{"execute": "guest-network-get-interfaces"}'])

        return json.loads(output)['return']


    @classmethod
    def create(
            cls, name, disk_file, vnic_list=None, cpu=1, memory=512, **kwargs):

        _domain = domain.Domain(
            name=name, disk_file=None, vcpus=cpu, memory=memory, **kwargs)

        _domain._disk_file = disk_file

        vnic_list = vnic_list or []
        for _vnic in vnic_list:
            _domain.add_device(_vnic._get_root())

        _domain.create()

    @classmethod
    def remove(cls, name):
        _domain = domain.Domain(name=name, disk_file=None)

        _domain.remove()

        # Do not remove the file. Should require user's permission by "--force"
        # disk_file = _domain.disk_file
        # if disk_file and os.access(disk_file, 0):
        #     log.info('Removing the file %s ... ' % disk_file)
        #     os.remove(disk_file)

    @classmethod
    def power(cls, name, oper):
        _domain = domain.Domain(name=name, disk_file=None)

        if oper == 'on':
            _domain.start()
        elif oper == 'off':
            _domain.stop()
        elif oper == 'status':
            raise NotImplementedError('status is not supported yet')
        else:
            raise exception.ValueException(
                'Invalid operation %s. choices=[on|off]' % oper)

    @classmethod
    def get_vm_list(cls):
        with domain.LibvirtOpen() as conn:
            return [_domain.name() for _domain in conn.listAllDomains()]

    @classmethod
    def set_vnic(cls, name, test_ip_addr, **kwargs):
        raise NotImplementedError

    @classmethod
    def get_mgmt_ip_addr(cls, vm_name, ip_network):
        """Return the management IP address of the virtual machine

        Due to livirtd-python does not provide APIs for guest agent yet, use
        shell command "virsh" to get the information.

        Args:
            vm_name (str): A name of the virtual machine
            ip_network (str): IP address/prefix (x.x.x.x/x) for network where
                the management IP address should be be long to
        """

        mgmt_ip_addr_list = []
        iface_list = cls._get_network(vm_name)

        for iface in iface_list:
            if 'ip-addresses' not in iface:
                log.debug('No IP addresses detected on %s (%s)' % (
                    iface['name'], iface['hardware-address']))
                continue

            for ip_addr in iface['ip-addresses']:
                if netaddr.IPAddress(
                        ip_addr['ip-address']) in netaddr.IPNetwork(ip_network):
                    mgmt_ip_addr_list.append(ip_addr['ip-address'])

        if len(mgmt_ip_addr_list) == 1:
            return mgmt_ip_addr_list[0]

        elif len(mgmt_ip_addr_list) > 1:
            raise exception.ConfigException(
                '%s has two management IP addresses (%s) that are belong to '
                'the same subnet. This is likely a configuration error' % (
                    vm_name, ', '.join(mgmt_ip_addr_list)))
        else:
            raise exception.ValueException(
                'No management IP addresses are discovered')

    @classmethod
    def get_test_ip_addr(cls, vm_name):
        test_ip_addr_dict = {}

        for iface in cls._get_network(vm_name):
            mac_addr = iface['hardware-address']
            if not mac_addr.startswith('b2:'):
                # Not the test network vNIC. Skip.
                continue

            if 'ip-addresses' not in iface:
                log.debug('No IP addresses detected on %s (%s)' %(
                    iface['name'], iface['hardware-address']))
                test_ip_addr_dict[iface['name']] = None
                continue

            test_ip_addr_dict[iface['hardware-address']] = {
                'ipv4': [], 'ipv6': []
            }

            for ip_addr in iface['ip-addresses']:
                _ip_addr_dict = test_ip_addr_dict[iface['hardware-address']][
                    ip_addr['ip-address-type']]
                if str(ip_addr['ip-address']).startswith('fe80:'):
                    # Skip the local-link IPv6 IP address
                    continue
                _ip_addr_dict.append(str(ip_addr['ip-address']))

        return test_ip_addr_dict


class BaseDevice(object):
    def __init__(self, tag):
        self._tag = tag

    @property
    def tag(self):
        return self._tag

    def _get_root(self):
        root = ElementTree.Element('device_root')
        root.text = self.tag
        return root

    def get_xml(self):
        return ElementTree.tostring(self._get_root())
