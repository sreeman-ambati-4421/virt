import os

import libvirt

from virt.lib.core import exception
from virt.lib.core import log_handler
from virt.lib.common.virtual_machine.template import BaseTemplate, BasePool
from virt.lib.linux import storage
from virt.lib.linux.core.libvirt_ei import LibvirtOpen


log = log_handler.get_logger(__name__)


class Pool(BasePool):
    def __init__(self, path):
        super(Pool, self).__init__(path)

    def create(self):
        template = storage.Pool(
            name='template', path=os.path.join(self.path, 'template'))
        vm = storage.Pool(
            name='vm', path=os.path.join(self.path, 'vm'))

        if not template.object:
            template.create()

        elif template.object.isActive() == 0:
            template.object.setAutostart(1)
            template.object.create()

        if not vm.object:
            vm.create()
        elif vm.object.isActive() == 0:
            vm.object.setAutostart(1)
            vm.object.create()

        return True

    def remove(self):
        template = storage.Pool(name='template')
        vm = storage.Pool(name='vm')

        template.remove()
        vm.remove()


class KVMTemplate(BaseTemplate):
    def __init__(self):
        super(KVMTemplate, self).__init__(file_ext='qcow2')

    def validate(self, vswitch_list=None):
        vswitch_list = vswitch_list or []
        with LibvirtOpen() as conn:
            try:
                conn.storagePoolLookupByName('template')
                conn.storagePoolLookupByName('vm')
            except libvirt.libvirtError as err:
                if 'Storage pool not found' in err.message:
                    raise exception.ConfigException(
                        '"template" and/or "vm" storage pools do not exist')
                else:
                    raise

            for vswitch in vswitch_list:
                try:
                    conn.networkLookupByName(vswitch)
                except libvirt.libvirtError as err:
                    if 'Network not found' in err.message:
                        raise exception.ConfigException(
                            '"%s" does not exist' % vswitch)
                    else:
                        raise


class RHEL70(KVMTemplate):
    name = 'rhel-7-u0'
    url = ''
    os_type = 'linux'


class RHEL71(RHEL70):
    name = 'rhel-7-u1'


class RHEL71_Head(RHEL71):
    name = 'rhel-7-u1_head'


class RHEL72_Head(RHEL71):
    name = 'rhel-7-u2'


class RHEL73_Head(RHEL72_Head):
    name = 'rhel-7-u3'


class SLES12SP0(KVMTemplate):
    name = 'sles-12-sp0'
    url = ''
    os_type = 'linux'


def get_template(name, *args, **kwargs):
    for subclass in KVMTemplate._get_all_subclasses(KVMTemplate):
        if subclass.name == name:
            return subclass(*args, **kwargs)
    raise exception.ValueException('No such template %s' % name)


def get_template_list():
    return [
        template.name for template in
        KVMTemplate._get_all_subclasses(KVMTemplate)
    ]

