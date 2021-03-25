from . import vswitch
from . import vnic


def get_mgmt_vswitch(iface=None, name='Management Network'):
    if iface:  # Create a new vswitch
        return vswitch.BaseLinuxVSwitch.factory(
            name=name, mode='macvtap', iface_list=[iface])

    # Return a existing vswitch
    return vswitch.BaseLinuxVSwitch.factory(name=name)


def get_vswitch(name, mode=None, **kwargs):
    return vswitch.BaseLinuxVSwitch.factory(name=name, mode=mode, **kwargs)


def get_vswitch_list():
    return vswitch.BaseLinuxVSwitch.get_vswitch_list()


def get_vswitch_mode():
    return [
        _network.get_mode() for _network in
        vswitch.BaseLinuxVSwitch.__subclasses__()] + [
        _network.get_mode() for _network in vswitch.Bridge.__subclasses__()]


def get_vnic(network, mac_addr=None, mgmt_iface=False, **kwargs):
    return vnic.VNIC.factory(
        network, mac_addr=mac_addr, mgmt_iface=mgmt_iface, **kwargs)

def get_pci_vnic(vnic_pci, mac_addr=None, **kwargs):
    return vnic.PciVNIC.factory(
        vnic_pci, mac_addr=mac_addr, **kwargs)
