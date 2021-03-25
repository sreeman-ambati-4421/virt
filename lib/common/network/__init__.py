"""
:mod:`network` -- Network library
=================================

.. module:: virt.lib.common.network
This library provides APIs to interact with vNIC which will be attached to
a virtual machine at creation as well as vSwitch

For vSwitch, each hypervisor has different types of vSwitches. Please refer
below links for details of each hypervisor type.

* KVM: :ref:`api.network.linux`
* Hyper-V: :ref:`api.network.windows`

Once you created a virtual switch / network, now you can create vNICs that are
attached to it. If you have a vswitch named "Test Network", below will define
a vNIC that is connected to "Test Network"

>>> vnic = BaseVNIC(network='Test Network')

And pass "vnic" as vNIC which is attached to the virtual machine

>>> from virt.lib.common import virtual_machine
>>> vmm = virtual_machine.get_vm_manager()
>>> vmm.create(name='vm-1', disk_file='/vm_pool/vm/vm-1.qcow2', vnic_list=[vnic])

.. warning::

   Depending on hypervisor types, you should pass a child class of BaseVNIC

This will create a new virtual machine that has "vnic" as attached NIC

"""

import logging
import platform
import importlib
import netaddr

from virt.lib.core import exception


__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
log = logging.getLogger(__name__)


class BaseVNIC(object):
    """An abstract class to define vNIC

    Args:
        network (str): Name of network where vNIC is attached to
        mac_addr (str): User-defined MAC address for vNIC. If None,
            assign a random MAc address instead
        mgmt_iface (bool) If True, this network device is a management
            network device
    """

    def __init__(self, network, mac_addr=None, mgmt_iface=False):
        self._network = network
        self._mac_addr = mac_addr
        self._mgmt_iface = mgmt_iface

    @classmethod
    def factory(cls, network, mac_addr=None, mgmt_iface=False, **kwargs):
        """Factory function which returns BaseVNIC or children class"""
        vnic = cls(
            network=network, mac_addr=mac_addr, mgmt_iface=mgmt_iface, **kwargs)
        return vnic

    @property
    def network(self):
        """Return a name of network where vNIC is attached to"""
        return self._network

    @property
    def mac_addr(self):
        """Return MAC address of vNIC"""
        return self._mac_addr

    @property
    def mgmt_iface(self):
        """Return True or False whether this vNIC is a management interface

        For internal use - assume this is a private method
        """
        return self._mgmt_iface

class BasePciVNIC(object):
    """An abstract class to define vNIC

    Args:
        vnic_pci (str): PCI device id of the VF
        mac_addr (str): User-defined MAC address for vNIC. If None,
            assign a random MAc address instead
    """

    def __init__(self, vnic_pci, mac_addr=None):
        self._vnic_pci = vnic_pci
        self._mac_addr = mac_addr

    @classmethod
    def factory(cls, vnic_pci, mac_addr=None, **kwargs):
        """Factory function which returns BaseVNIC or children class"""
        vnic = cls(
            vnic_pci=vnic_pci, mac_addr=mac_addr, **kwargs)
        return vnic

    @property
    def mac_addr(self):
        """Return MAC address of vNIC"""
        return self._mac_addr

    @property
    def vnic_pci(self):
        """Return PCI id"""
        return self._vnic_pci

class BaseVSwitch(object):
    """An abstract class to define vSwitch

    Attributes:
        _mode (str): Mode of vswitch. i.e.) external, bridge, sriov ... This
            should be set by children classes
    """
    _mode = None

    def __init__(self, name, **kwargs):
        """
        Args:
            name (str): A name of network
        """
        self._name = name

    @staticmethod
    def _get_all_subclasses(cls):
        all_subclasses = []
        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(cls._get_all_subclasses(subclass))
        return all_subclasses

    @property
    def name(self):
        """Return a name of a vswitch"""
        return self._name

    @classmethod
    def get_vswitch_list(cls):
        """Return a list of names of vswitches"""
        raise NotImplementedError

    @classmethod
    def get_mode(cls):
        """Return a mode of a vswitch"""
        return cls._mode

    @classmethod
    def factory(cls, name, mode=None, **kwargs):
        """Return a instantiated object of BaseNetwork

        If only "name" is given, assume the switch already exists and tries to
        return the switch object of the existing one. If no such switch exists
        with that name, will raise exception.

        If mode is given, assume the switch is a new one. No error checking
        is necessary since low-level API (libvirt / powershell) should raise
        exceptions properly. When instantiate a new object, this method should
        instantiate from the right class which matches with the given "mode".
        If mode is invalid, should raise exception

        """
        raise NotImplementedError

    def create(self):
        """Create a new vSwitch"""
        raise NotImplementedError

    def remove(self):
        """Remove a existing vSwitch"""
        raise NotImplementedError


def _get_virt_network():
    try:
        virt_network = importlib.import_module(
            'virt.lib.%s.network' % platform.system().lower())
    except ImportError:
        raise exception.ConfigException(
            'Not supported OS %s' % platform.system())
    return virt_network


def get_mgmt_vswitch(iface=None, name='Management Network'):
    """Return the management vswitch

    If iface is None, expect to get the existing vswitch object - namely
    only "name" argument should be passed to get_vswitch()

    Otherwise return a vswitch object which is created with the name and mode
    """
    virt_network = _get_virt_network()
    return virt_network.get_mgmt_vswitch(iface=iface, name=name)


def get_vswitch(name, mode=None, **kwargs):
    """Return an instantiated vswitch object that has the given name

    If mode is "None", assume that the switch that has the given name exists,
    and return its object. If fails to find one, raise exception as no such
    vswitch exists.

    Args:
        name (str): Name of vSwitch
        mode (str, None): vSwitch mode. If None, will look for an existing
            vSwitch that has the given name. If no such switch exists, will
            raise exception
    """
    virt_network = _get_virt_network()
    return virt_network.get_vswitch(name, mode, **kwargs)


def get_vswitch_list():
    """Return a list of existing vSwitches"""
    virt_network = _get_virt_network()
    return virt_network.get_vswitch_list()


def get_vswitch_mode():
    """Return a list of available vswitch mode"""
    virt_network = _get_virt_network()
    return virt_network.get_vswitch_mode()


def get_vnic(network, mac_addr=None, mgmt_iface=False, **kwargs):
    """Return an instantiated vnic object that has the given name

    If mode is "None", assume that the vNIC that has the given name exists, and
    return its object. If fails to find one, raise exception as no such vswitch
    exists.

    Args:
        network (str): Name of network where vNIC is attached to
        mac_addr (str, None): If given, assign the given MAC address to the
            vNIC. If None, assign a random MAC address
        mgmt_iface (bool): For internal use
    """
    virt_network = _get_virt_network()
    return virt_network.get_vnic(
        network=network, mac_addr=mac_addr, mgmt_iface=mgmt_iface, **kwargs)

def get_pci_vnic(vnic_pci, mac_addr=None, **kwargs):
    """Return an instantiated vnic object that has the given name

    If mode is "None", assume that the vNIC that has the given name exists, and
    return its object. If fails to find one, raise exception as no such vswitch
    exists.

    Args:
        vnic_pci (str) : PCI device id of the VF
        mac_addr (str, None): If given, assign the given MAC address to the
            vNIC. If None, assign a random MAC address
    """
    virt_network = _get_virt_network()
    return virt_network.get_pci_vnic(
        vnic_pci=vnic_pci, mac_addr=mac_addr, **kwargs)


def get_ipnetwork(ip_addr):
    """Convert string to netaddr.IPNetwork object

    Args:
        ip_addr (str): IP address/prefix|netmask (x.x.x.x/x.x.x.x or x.x.x.x/x)

    """
    if isinstance(ip_addr, (netaddr.IPNetwork,)):
        return ip_addr

    return netaddr.IPNetwork(ip_addr)
