"""
:mod:`virtual_machine` -- Virtual machine library
=================================================

.. module:: virt.lib.common.virtual_machine
This module provides low-level APIs to create / remove virtual machines.

Basic examples is available at :ref:`api.virtual_machine.index`

"""

import platform
import importlib

from virt.lib.core import exception


class BaseManager(object):
    """Hypervisor manager"""
    @classmethod
    def create(
            cls, name, disk_file, vnic_list=None, cpu=1, memory=512, **kwargs):
        """Create a virtual machine using a template

        The adapter will have one management NIC and test NICs as many as the
        IP addresses that are defined in the test_ip_addr. The test network
        IP addresses will be bound to the given network.

        Args:
            disk_file (str): virtual disk filename with full path
            mgmt_ip_addr (str): Management IP address x.x.x.x/x format or a
                VM name. If hostname is given, MAC address will be random. If
                None, "name" argument must be given
            vnic_list (list): List of virt.lib.common.network.BaseVNIC
            name (None, str): Name of the virtual machine. If None and
                "mgmt_ip_addr" is given, automatically name will be assigned
                using the management IP address
            cpu (int): A number of vCPU. Default=1
            memory (int): A size of memory in MB. Default=512
        """
        raise NotImplementedError

    @classmethod
    def remove(cls, name):
        """Stop and remove a virtual machine

        Args:
            name (str): A name of the virtual machine to be destroyed
        """
        raise NotImplementedError

    # def set_network(self, name, network_name, test_ip_addr, oper):
    #     """Change the network binding setting.
    #
    #     Args:
    #         name (str): A name of the virtual machine
    #         network_name (str): Network name
    #         test_ip_addr (str): IP address which will be bind or unbind from
    #             the network
    #         oper (oper): choices=[add|remove]. If add, adding the NIC which
    #             will have a test IP address to the network. If remove,
    #             removing the NIC from the network
    #     """
    #     raise NotImplementedError

    @classmethod
    def set_vnic(cls, name, test_ip_addr, **kwargs):
        """Change the setting fo the vNIC

        Args:
            name (str): Name of the virutal machine
            test_ip_addr (str): IP address/prefix of the vNIC
            **kwargs (kwargs): keyword arguments which will be passed to
                platform specific method
        """
        raise NotImplementedError

    @classmethod
    def power(cls, name, oper):
        """Power control the virtual machine

        Args:
            name (str): A name of the virtual machine
            oper (str): choices=[on|off|status] If on, power on. If off, power
                off. If status, return the current power status
        """
        raise NotImplementedError

    @classmethod
    def get_vm_list(cls):
        """Return a list of virtual machine names"""
        raise NotImplementedError

    @classmethod
    def get_mgmt_ip_addr(cls, vm_name, ip_addr):
        """Return a management IP address of the virtual machine

        Args:
            vm_name (str): A name of the virtual machine
            ip_addr (str): IP network and prefix in x.x.x.x/x where the
                management IP address should be belong to. This will be
                used to determine the actual IP address. For example,
                for VLAN 240 lab network, this should be "10.13.240.0/20"
        """
        raise NotImplementedError

    @classmethod
    def get_test_ip_addr(cls, vm_name):
        """Return a list of IP addresses that are assigned to non-management
        network (any vNIC that has MAC address which starts with "b2")

        Return value is a dictionary

        {
            <Interface MAC address>: {
                'ipv4': [<IPv4 address>, ... ],
                'ipv6': [<IPv6 address>, ... ],
            }
        }

        Args:
            vm_name (str): A name of the virtual machine
        """
        raise NotImplementedError


def get_vm_manager():
    """A factory function to return an BaseManager or its child class"""
    _system = platform.system()
    if _system == 'Linux':
        vm_module = importlib.import_module('virt.lib.linux.virtual_machine')
        return vm_module.LibvirtManager()
    elif _system == 'Windows':
        vm_module = importlib.import_module('virt.lib.windows.virtual_machine')
        return vm_module.PowerShellManager()
    raise exception.ValueException('Unsupported OS type')
