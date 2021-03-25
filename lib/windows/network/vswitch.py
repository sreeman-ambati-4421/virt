"""
:mod:`vswitch` -- Windows Hyper-V vSwitch Library
=================================================

.. module:: virt.lib.windows.network.vswitch
This module provides to interact with Linux vSwitch / network.

Supported bridge types are

* Private
* Internal
* External
* SrIov

And each switch type requires different arguments. Please refer docstring for
each bridge type for details.

"""

from virt.lib.core import exception
from virt.lib.core import log_handler
from virt.lib.common.network import BaseVSwitch
from virt.lib.windows.core import powershell


log = log_handler.get_logger(__name__)


__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
class BaseHyperVSwitch(BaseVSwitch):
    _mode = None

    def __init__(
            self, name, iface=None, sriov=None, switch_id=None, **kwargs):
        super(BaseHyperVSwitch, self).__init__(name=name)
        self._id = switch_id
        self._iface = iface
        self._sriov = sriov

    @property
    def id(self):
        return self._id

    @property
    def iface(self):
        return self._iface

    @property
    def sriov(self):
        if self.iface:
            return self._sriov
        return False

    @classmethod
    def get_vswitch_list(cls):
        vswitch_list = powershell.exec_powershell('get-vmswitch')
        if not vswitch_list:
            return []

        return [vswitch.Name for vswitch in vswitch_list]

    @classmethod
    def _get_mode_by_int(cls, value):
        """Return a switch mode name using the given value"""
        mapping = {0: 'private', 1: 'internal', 2: 'external'}
        return mapping[value]

    def _get_object(self):
        try:
            network_object = powershell.exec_powershell(
                'get-vmswitch', name=self.name)
        except exception.ExeExitcodeException as err:
            if 'No switch can be found' in err.output:
                raise exception.NotFoundException(
                    'vSwitch "%s" does not exist' % self.name)
            raise

        if len(network_object) > 1:
            if self.id is None:
                raise exception.ValueException(
                    'Found more than one switch that has the name %s. Need '
                    '"switch_id" argument additionally'
                )
            network_object = [
                _no for _no in network_object if _no.Id == self.id]

        if not network_object:
            raise exception.NotFoundException(
                'vSwitch "%s" %s does not exist' % (
                    self.name, '' if self.id is None else
                    '(ID: ' + str(self.id) + ')'))

        return network_object[0]

    @classmethod
    def factory(cls, name, mode=None, switch_id=None, **kwargs):
        _network = BaseHyperVSwitch(name=name, switch_id=switch_id, **kwargs)

        if not mode:  # Expect to get an exisiting switch
            network_object = _network._get_object()

            ifdesc = network_object.NetAdapterInterfaceDescription
            iface = kwargs.pop('iface', None)  # remove "iface" argument

            for _iface in powershell.exec_powershell(
                'get-netadapter', select_clause='InterfaceDescription,Name',
                max_depth=1
            ):
                if _iface.InterfaceDescription == ifdesc:
                    iface = _iface.Name
                    break

            for subclass in BaseHyperVSwitch._get_all_subclasses(
                    BaseHyperVSwitch):
                if subclass.get_mode() == cls._get_mode_by_int(
                        network_object.SwitchType):
                    if network_object.IovEnabled:
                        return SrIov(
                            name=name, switch_id=network_object.Id,
                            iface=iface, **kwargs)
                    return subclass(
                        name=name, switch_id=network_object.Id, iface=iface,
                        **kwargs)

            raise exception.NotFoundException(
                'Failed to detect the vswitch mode %s' % cls._get_mode_by_int(
                    network_object.SwitchType))

        for subclass in BaseHyperVSwitch._get_all_subclasses(BaseHyperVSwitch):
            if subclass.get_mode() == mode:
                return subclass(name=name, **kwargs)

        raise exception.ValueException('Invalid mode %s' % mode)

    def create(self):
        raise NotImplementedError

    def remove(self):
        powershell.exec_powershell(
            'remove-vmswitch', name=self.name, force=True)
        log.info('"%s" is successfully removed' % self.name)


class Private(BaseHyperVSwitch):
    """Private mode vSwitch

    Args:
        name (str): Name of vSwitch
        switch_id (str, None): Unique ID of vSwitch. If given, this will be
            used to get the existing vSwitch since Windows allows to have the
            same vSwitch name
    """
    _mode = 'private'

    def __init__(self, name, switch_id=None, **kwargs):
        super(Private, self).__init__(name=name, switch_id=switch_id)

    def create(self):
        powershell.exec_powershell(
            'new-vmswitch', name=self.name, switchtype=self.get_mode())
        log.info('"%s" is successfully created' % self.name)


class Internal(Private):
    """Internal mode vSwitch

    Args:
        name (str): Name of vSwitch
        switch_id (str, None): Unique ID of vSwitch. If given, this will be
            used to get the existing vSwitch since Windows allows to have the
            same vSwitch name
    """

    _mode = 'internal'

    def __init__(self, name, switch_id=None, **kwargs):
        super(Internal, self).__init__(name=name, switch_id=switch_id)


class External(BaseHyperVSwitch):
    """External mode vSwitch

    Args:
        name (str): Name of vSwitch
        iface (str): Name of NIC
        sriov (bool): Enable/disable SR-IOV. Should not override this.
        switch_id (str, None): Unique ID of vSwitch. If given, this will be
            used to get the existing vSwitch since Windows allows to have the
            same vSwitch name
    """
    _mode = 'external'

    def __init__(self, name, iface, sriov=False, switch_id=None, **kwargs):
        super(External, self).__init__(
            name=name, iface=iface, sriov=sriov, switch_id=switch_id)

    def create(self):
        powershell.exec_powershell(
            'new-vmswitch', name=self.name, enableiov=self.sriov,
            netadaptername=self.iface
        )
        log.info('"%s" is successfully created' % self.name)


class SrIov(External):
    """External and SR-IOV mode vSwitch

    Args:
        name (str): Name of vSwitch
        iface (str): Name of NIC
        switch_id (str, None): Unique ID of vSwitch. If given, this will be
            used to get the existing vSwitch since Windows allows to have the
            same vSwitch name
    """
    _mode = 'sriov'

    def __init__(self, name, iface, switch_id=None, **kwargs):
        super(SrIov, self).__init__(
            name=name, iface=iface, sriov=True, switch_id=switch_id, **kwargs)