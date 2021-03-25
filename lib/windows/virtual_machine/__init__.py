import re
import netaddr

from virt.lib.core import exception
from virt.lib.common.virtual_machine import BaseManager
from virt.lib.common.network import test_network
from virt.lib.windows.core import powershell


class PowerShellManager(BaseManager):
    @classmethod
    def create(
            cls, name, disk_file, vnic_list=None, cpu=1, memory=512, **kwargs):

        # Create a VM (new-vm)
        powershell.exec_powershell(
            'new-vm', name=name, memorystartupbytes=str(memory) + "MB",
            vhdpath=disk_file)

        # Set CPU (set-vmprocessor)
        powershell.exec_powershell('set-vmprocessor', vmname=name, count=cpu)

        # Remove any existing NIC interfaces
        powershell.exec_powershell(
            'remove-vmnetworkadapter', vmname=name)

        # Add NIC interfaces to VM (add-vmnetworkadapter)
        for vnic in vnic_list:
            powershell.exec_powershell(
                'add-vmnetworkadapter', vmname=name, switchname=vnic.network,
                staticmacaddress=vnic.mac_addr, name=vnic.mac_addr)

    @classmethod
    def update(
            cls, name, vnic_list=None, cpu=1, memory=512, **kwargs):

        # Updating memory ( set-vm )
        # Create a VM (new-vm)
        powershell.exec_powershell(
            'set-vm', name=name, memorystartupbytes=str(memory) + "MB")

        # Set CPU (set-vmprocessor)
        powershell.exec_powershell('set-vmprocessor', vmname=name, count=cpu)

        # Remove the existing network adapters except for Management Network.
        # Retaining management networks helps in saving MLTT licenses...
        mgmt_net_found = False
        if powershell.exec_powershell('get-vmnetworkadapter', vmname=name):
            for vnic in powershell.exec_powershell('get-vmnetworkadapter', vmname=name):
                if vnic.SwitchName != 'Management Network':
                    powershell.exec_powershell('remove-vmnetworkadapter',
                                vmname=name, name=vnic.Name)
                else:
                    mgmt_net_found = True

        # Add NIC interfaces to VM (add-vmnetworkadapter)
        for vnic in vnic_list:
            if vnic.network == 'Management Network' and mgmt_net_found:
                continue
            powershell.exec_powershell(
                'add-vmnetworkadapter', vmname=name, switchname=vnic.network,
                staticmacaddress=vnic.mac_addr, name=vnic.mac_addr)

    @classmethod
    def remove(cls, name):
        vm = powershell.exec_powershell(
            'get-vm', name=name, select_clause='State')

        if len(vm) == 0:
            raise exception.NotFoundException(
                'No such virtual machine %s' % name)

        vm = vm[0]
        if vm.State != 3:
            cls.power(name=name, oper='off')

        powershell.exec_powershell('remove-vm', name=name, force=True)

    @classmethod
    def power(cls, name, oper):
        mapping = {'on': 'start-vm', 'off': 'stop-vm'}

        if oper not in mapping:
            raise exception.ValueException(
                'invalid operation %s. choices=[on|off]' % oper)

        try:
            if oper == 'off':
                powershell.exec_powershell(mapping[oper], name=name, force=True)
            else:
                powershell.exec_powershell(mapping[oper], name=name)
        except exception.ValueException:
            return True

    @classmethod
    def set_vnic(cls, name, test_ip_addr, **kwargs):
        test_mac_addr = test_network.get_mac_addr(test_ip_addr)
        powershell.exec_powershell(
            'set-vmnetworkadapter', vmname=name, name=test_mac_addr, **kwargs)

    @classmethod
    def get_vm_list(cls):
        vm_list = powershell.exec_powershell('get-vm')
        return [vm.Name for vm in vm_list] if vm_list else []

    @classmethod
    def get_mgmt_ip_addr(cls, vm_name, ip_network):
        mgmt_ip_network = netaddr.IPNetwork(ip_network)

        iface_list = powershell.exec_powershell(
            'get-vm', name=vm_name, select_clause='networkadapters'
        )[0].NetworkAdapters

        mgmt_ip_addr_list = []

        for iface in iface_list:
            for ip_network in iface['IPAddresses'].split():
                if netaddr.IPAddress(ip_network) in mgmt_ip_network:
                    mgmt_ip_addr_list.append(ip_network)

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
        test_ip_addr_dict ={}
        iface_list = powershell.exec_powershell(
            'get-vmnetworkadapter', vmname=vm_name,
            select_clause='IPAddresses,MacAddress'
        )

        for iface in iface_list:
            mac_addr = ':'.join(
                digit.encode('hex') for digit in iface.MacAddress.decode('hex'))
            if not mac_addr.startswith('b2'):
                continue

            test_ip_addr_dict[mac_addr] = {'ipv4': [], 'ipv6': []}

            for ip_addr in iface.IPAddresses:
                if re.match('\d+\.\d+\.\d+\.\d+', ip_addr):  # IPv4
                    test_ip_addr_dict[mac_addr]['ipv4'].append(ip_addr)
                else:  # Assume IPv6
                    if ip_addr.startswith('fe80:'):
                        continue
                    test_ip_addr_dict[mac_addr]['ipv6'].append(ip_addr)

        return test_ip_addr_dict





