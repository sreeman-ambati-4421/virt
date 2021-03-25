"""
:mod:`vswitch` -- Linux vSwitch module
======================================

.. module:: virt.lib.linux.network.vswitch
This module provides to interact with Linux vSwitch / network.

Supported bridge types are

* Bridge
* NAT
* Route
* MacVtap
* OVS
* HostDev

And each switch type requires different arguments. Please refer docstring for
each bridge type for details.

"""


from xml.etree import ElementTree

import netaddr

from virt.lib.core import log_handler
from virt.lib.core import exception
from virt.lib.common.network import BaseVSwitch
from virt.lib.linux.core.libvirt_ei import LibvirtOpen, LibBase


__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
log = log_handler.get_logger(__name__)


class BridgeInterface(object):
    def __init__(self, br_iface, forward_mode, ip_addr=None):
        """
        Args:
            br_iface (str): Bridge interface name. i.e.) test-br0
            mode (str, None): Forward mode. If None, no forward mode
                will be defined
            ip_addr (str, None): IP address/Prefix. If given, ip address and
                prefix will be defined for this bridge
        """
        self._br_iface = br_iface
        self._forward_mode = forward_mode
        self._ip_addr = ip_addr if ip_addr is None else netaddr.IPNetwork(
            ip_addr)

    @property
    def br_iface(self):
        return self._br_iface

    @property
    def forward_mode(self):
        return self._forward_mode

    @property
    def ip_addr(self):
        return str(self._ip_addr)

    def get_sub_element_tree(self, root):
        if not self._ip_addr:
            return root

        ElementTree.SubElement(
            root, 'ip', address=str(self._ip_addr.ip),
            prefix=str(self._ip_addr.prefixlen))

        return root  # Obsolete DHCP, since now we use static IP address


class BaseLinuxVSwitch(LibBase, BaseVSwitch):
    _mode = None

    def __init__(self, name, bridge=None, **kwargs):
        """
        Args:
            name (str): Name of the network
            bridge (Bridge): Bridge object which will be used to communicate to
                the external network.
        """

        super(BaseLinuxVSwitch, self).__init__(name=name)
        self._bridge = bridge

    @property
    def bridge(self):
        return self._bridge

    @classmethod
    def get_vswitch_list(cls):
        with LibvirtOpen() as conn:
            return [
                network.name() for network in conn.listAllNetworks()
            ]

    @classmethod
    def factory(cls, name, mode=None, **kwargs):
        _network = BaseLinuxVSwitch(name=name)

        forward_mode = None
        forward_interface = None
        ip_addr = None
        br_iface = None
        iface_list = None
        virtual_port = None

        if not mode:  # Expect to get an existing switch
            if _network.object is None:
                raise exception.NotFoundException(
                    'vSwitch "%s" does not exist' % name)

            vswitch_xml = ElementTree.fromstring(_network.object.XMLDesc())

            if vswitch_xml.find('forward') is not None:
                forward_mode = vswitch_xml.find('forward').get('mode')
                forward_interface = vswitch_xml.find('forward').get('dev')

            if vswitch_xml.findall('forward/interface') is not None:
                iface_list = [
                    iface.get('dev') for iface in
                    vswitch_xml.findall('forward/interface')]

            if vswitch_xml.find('ip') is not None:
                _ip_addr = vswitch_xml.find('ip').get('address')
                _prefix = vswitch_xml.find('ip').get('prefix')
                ip_addr = _ip_addr + '/' + _prefix

            if vswitch_xml.find('bridge') is not None:
                br_iface = vswitch_xml.find('bridge').get('name')

            if forward_mode == 'nat':  # NAT
                return NAT(name=name, br_iface=br_iface, ip_addr=ip_addr)

            elif forward_mode == 'hostdev':  # SR-IOV:
                iface = vswitch_xml.find('forward/pf').get('dev')
                return HostDev(name=name, iface=iface)

            if iface_list:  # MacVTAP
                return MacVtap(
                    name=name, iface_list=iface_list, macvtap_mode=forward_mode)

            if virtual_port:  # OVS
                return OVS(name=name, br_iface=br_iface)

            if forward_interface:  # routed
                return Route(
                    name=name, br_iface=br_iface, iface=forward_interface)

            if forward_mode:
                return Bridge(
                    name=name, br_iface=br_iface,
                )

            raise exception.ValueException(
                'Failed to detect the vswitch mode. XML output: %s'
                % _network.get_xml()
            )

        if _network.object is not None:
            # vswitch exists. Compare the mode, and if they are same, return
            # that object otherwise raise exception

            # _vswitch = cls.factory(name=name, **kwargs)
            # if _vswitch._mode == mode:
            #     return _vswitch

            raise exception.ConfigException('vSwitch %s already exists' % name)

        # Creating a new vswitch
        for subclass in BaseLinuxVSwitch._get_all_subclasses(BaseLinuxVSwitch):
            if subclass.get_mode() == mode:
                return subclass(name, **kwargs)

        raise exception.ValueException('Invalid mode %s' % mode)

    def _get_object(self):
        with LibvirtOpen() as conn:
            return conn.networkLookupByName(self.name)

    def _get_root(self, **kwargs):
        root = ElementTree.Element('network')
        ElementTree.SubElement(root, 'name').text = self.name

        if self.bridge:
            if not self.bridge.br_iface:
                raise exception.ValueException(
                    'Bridge name cannot be None for NAT')
            ElementTree.SubElement(root, 'bridge', name=self.bridge.br_iface)

            if self.bridge.forward_mode:
                ElementTree.SubElement(
                    root, 'forward', mode=self.bridge.forward_mode, **kwargs)

            # Add "ip" element
            root = self.bridge.get_sub_element_tree(root)

        return root

    def create(self):
        with LibvirtOpen() as conn:
            network = conn.networkDefineXML(self.get_xml())
            network.setAutostart(1)
            network.create()

        log.info('"%s" is successfully created' % self.name)

    def remove(self):
        super(BaseLinuxVSwitch, self).remove()


class Bridge(BaseLinuxVSwitch):
    """Bridge mode vSwitch

    Use the existing bridge interface as it is, which means before creating
    vSwitch, the bridge interface should be fully configured already and
    libvirt has no control over the bridge interface.

    Args:
        name (str): Name of vSwitch
        br_iface (str): Name of existing bridge interface. i.e.) test-br0
        forward_mode (str, None): Forward mode for bridge. Should not be
            changed since this is meant to be overriden by child classes
        ip_addr (str, None): IP address/prefix to be assigned to the
            bridge. If None, no IP address will be assigned

    """
    _mode = 'bridge'

    def __init__(
            self, name, br_iface, forward_mode=None, ip_addr=None, **kwargs):
        if not br_iface:
            raise exception.ValueException('"br_iface" argument is required')

        bridge = BridgeInterface(
            br_iface=br_iface, forward_mode=forward_mode or self._mode,
            ip_addr=ip_addr)
        super(Bridge, self).__init__(name=name, bridge=bridge)


class NAT(Bridge):
    """NAT mode vSwitch

    libvirt will take care of configuring bridge interface - namely the vswitch
    can be created even if a given bridge interface does not exist. It will be
    dynamically created / destroyed by libvirt when virtual machines start
    running.

    Args:
        name (str): Name of vSwitch
        br_iface (str): Name of bridge interface (i.e. test-br0)
        ip_addr (str, None): IP address/prefix to be assigned to the bridge.
            If None, no IP address will be assigned.

    """
    _mode = 'nat'

    def __init__(self, name, br_iface, ip_addr=None, **kwargs):
        if not br_iface:
            raise exception.ValueException('"br_iface" argument is required')

        super(NAT, self).__init__(
            name=name, br_iface=br_iface, forward_mode='nat', ip_addr=ip_addr)


class Route(Bridge):
    """Route mode vSwitch

    Like NAT, libvirt will take care of configuring bridge interface

    Args:
        name (str): Name of vSwitch
        br_iface (str): Name of bridge interface (i.e. test-br0)
        iface (str): ethX name where packets will be routed to
        ip_addr (str): IP address/prefix to be assigned to the bridge. This is
            required.

    """
    _mode = 'route'

    def __init__(self, name, br_iface, iface, ip_addr, **kwargs):
        if not br_iface:
            raise exception.ValueException('"br_iface" argument is required')

        super(Route, self).__init__(
            name=name, br_iface=br_iface, forward_mode='route', ip_addr=ip_addr)
        self._iface = iface

    @property
    def iface(self):
        return self._iface

    def _get_root(self):
        return super(Route, self)._get_root(dev=self.iface)


class MacVtap(BaseLinuxVSwitch):
    """MacVtap mode vSwitch

    New MacVtap interfaces will be dynamically created by libvirt

    Args:
        name (str): Name of vSwitch
        iface_list (list, None): A list of ethX names which will be
            belong to the MacVtap interface. If None, "iface" argument
            must be given
        iface (str, None): A single ethX name which will be belong to the
            MacVtap interface. If None, "iface_list" argument must be given
        macvtap_mode (str): MacVtap mode. choices are whatever libvirt
            supports, but for now, [bridge|private|vepa|passthrough]

    """
    _mode = 'macvtap'

    def __init__(
            self, name, iface_list=None, iface=None,
            macvtap_mode='bridge', **kwargs):
        if not iface_list and not iface:
            raise exception.ValueException(
                'Both "iface_list" and "iface" arguments cannot be "None"')

        iface_list = iface_list or [iface]

        super(MacVtap, self).__init__(name=name)
        self._iface_list = iface_list
        self._macvtap_mode = macvtap_mode

    @property
    def iface_list(self):
        return self._iface_list

    @property
    def macvtap_mode(self):
        return self._macvtap_mode

    def _get_root(self):
        if not self.iface_list or None in self.iface_list:
            raise exception.ValueException('"iface_list" is None or has None')

        root = super(MacVtap, self)._get_root()
        forward = ElementTree.SubElement(
            root, 'forward', mode=self.macvtap_mode)
        for iface in self.iface_list:
            ElementTree.SubElement(forward, 'interface', dev=iface)

        return root


class OVS(Bridge):
    """OVS mode vSwitch

    Args:
        name (str): Name of vSwitch
        br_iface (str): Name of OVS interface
    """

    _mode = 'ovs'

    def __init__(self, name, br_iface, **kwargs):
        if not br_iface:
            raise exception.ValueException('"br_iface" argument is required')

        super(OVS, self).__init__(
            name=name, br_iface=br_iface, forward_mode='bridge')

    def _get_root(self, **kwargs):
        root = super(OVS, self)._get_root(**kwargs)
        ElementTree.SubElement(root, 'virtualport', type='openvswitch')
        return root


class HostDev(BaseLinuxVSwitch):
    """SR-IOV mode vSwitch

    Args:
        name (str): Name of vswitch
        iface (str): ethX name of SR-IOV enabled PF
    """
    _mode = 'sriov'

    def __init__(self, name, iface, **kwargs):
        if not iface:
            raise exception.ValueException('"iface" argument is required')

        super(HostDev, self).__init__(name=name)
        self._iface = iface

    @property
    def iface(self):
        return self._iface

    def _get_root(self):
        root = super(HostDev, self)._get_root()
        forward = ElementTree.SubElement(
            root, 'forward', mode='hostdev', managed='yes')
        ElementTree.SubElement(forward, 'pf', dev=self.iface)
        return root
