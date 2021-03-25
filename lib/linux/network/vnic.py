"""
:mod:`vnic` -- vNIC module
==========================

.. module:: virt.lib.linux.network.vnic
"""

from xml.etree import ElementTree

from virt.lib.common.network import BaseVNIC
from virt.lib.common.network import BasePciVNIC
from virt.lib.linux.virtual_machine import BaseDevice


__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
class VNIC(BaseVNIC, BaseDevice):
    def __init__(
            self, network, mac_addr=None, nic_type='virtio', mgmt_iface=False,
            **kwargs
    ):
        """
        Args:
            network (str): Name of network where vNIC is attached to
            mac_addr (str): MAC address for the vNIC. If None, use the random
                MAC address
            nic_type (str): Type of the vNIC. Default=virtio.
            mgmt_iface (bool) If True, this network device is a management
                network device
        """
        super(VNIC, self).__init__(network, mac_addr, mgmt_iface)
        self._tag = 'interface'
        self._type = nic_type

    @property
    def type(self):
        return self._type

    def _get_root(self, tag=None):
        root = super(VNIC, self)._get_root()

        interface = ElementTree.SubElement(root, 'interface', type='network')
        ElementTree.SubElement(interface, 'source', network=self.network)
        ElementTree.SubElement(interface, 'model', type=self.type)

        if self.mac_addr:
            ElementTree.SubElement(interface, 'mac', address=self.mac_addr)
        return root

class PciVNIC(BasePciVNIC, BaseDevice):
    def __init__(
            self, vnic_pci, mac_addr=None, nic_type='pci', **kwargs):
        """
        Args:
            network (str): Name of network where vNIC is attached to
            mac_addr (str): MAC address for the vNIC. If None, use the random
                MAC address
            nic_type (str): Type of the vNIC. Default=virtio.
            mgmt_iface (bool) If True, this network device is a management
                network device
        """
        super(PciVNIC, self).__init__(vnic_pci, mac_addr)
        self._tag = 'hostdev'
        self._vnic_pci = vnic_pci
        self._type = nic_type

    @property
    def type(self):
        return self._type

    @property
    def vnic_pci(self):
        return self._vnic_pci

    def _get_root(self, tag=None):
        root = super(PciVNIC, self)._get_root()
	
        hostdev = ElementTree.SubElement(root, 'hostdev', mode='subsystem', 
					type=self.type, managed='yes')
        source = ElementTree.SubElement(hostdev, 'source')

        import re
        _o = re.compile('(\d+):([a-f|\d]+):([a-f|\d]+).(\d)',re.I)
        _o = _o.match(self.vnic_pci)
        _domain = '0x' + _o.group(1)
        _bus = '0x' + _o.group(2)
        _slot = '0x' + _o.group(3)
        _fuction = '0x' + _o.group(4)
        
        ElementTree.SubElement(source, 'address', domain=_domain,
            bus=_bus, slot=_slot, function=_fuction)
        return root
