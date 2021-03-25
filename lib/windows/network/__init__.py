from virt.lib.common.network import BaseVNIC
from . import vswitch


def get_vswitch(name, mode=None, **kwargs):
    return vswitch.BaseHyperVSwitch.factory(name=name, mode=mode, **kwargs)


def get_vswitch_list():
    return vswitch.BaseHyperVSwitch.get_vswitch_list()


def get_vswitch_mode():
    return [
        _network.get_mode() for _network in
        vswitch.BaseHyperVSwitch._get_all_subclasses(vswitch.BaseHyperVSwitch)
    ]


def get_mgmt_vswitch(iface=None, sriov=False, name='Management Network'):
    if iface:  # Create a new vswitch
        return vswitch.BaseHyperVSwitch.factory(
            name=name, mode='external', iface=iface, sriov=sriov)

    return vswitch.BaseHyperVSwitch.factory(name=name)


def get_vnic(network, mac_addr=None, mgmt_iface=False, **kwargs):
    return BaseVNIC.factory(
        network, mac_addr=mac_addr, mgmt_iface=mgmt_iface, **kwargs)
