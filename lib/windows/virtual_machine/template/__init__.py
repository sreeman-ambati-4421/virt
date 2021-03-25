import os

from virt.lib.core import exception
from virt.lib.core import log_handler
from virt.lib.common.virtual_machine.template import BaseTemplate, BasePool
from virt.lib.windows import storage
from virt.lib.windows import network


log = log_handler.get_logger(__name__)


class Pool(BasePool):
    def __init__(self, path):
        super(Pool, self).__init__(path=path)

    def create(self):
        # Set the new default location
        storage.powershell.exec_powershell(
            'set-vmhost', virtualharddiskpath=self.path)

        template = storage.Pool(name='template')
        vm = storage.Pool(name='vm')

        if not os.access(template.path, 0):
            template.create()

        if not os.access(vm.path, 0):
            vm.create()

        return True

    def remove(self):
        template = storage.Pool(name='template')
        vm = storage.Pool(name='vm')
        template.remove()
        vm.remove()


class HyperVTemplate(BaseTemplate):
    def __init__(self):
        super(HyperVTemplate, self).__init__(file_ext='vhdx')

    def validate(self, vswitch_list=None):
        # Validate the pool
        template_pool = storage.Pool('template')
        vm_pool = storage.Pool('vm')

        if not template_pool.exist:
            raise exception.ConfigException('"template" pool not found')
        if not vm_pool.exist:
            raise exception.ConfigException('"vm" pool not found')

        # Validate the network
        if vswitch_list:
            for vswitch in vswitch_list:
                try:
                    network.get_vswitch(name=vswitch)
                except exception.NotFoundException:
                    raise exception.ConfigException(
                        'vSwitch "%s" not found' % vswitch)
        return True


class Windows2012_R2(HyperVTemplate):
    name = 'win2k12-r2'
    url = ""
    os_type = 'windows'

class Windows2012(HyperVTemplate):
    name = 'win2k12'
    url = ""
    os_type = 'windows'

class Windows2016(HyperVTemplate):
    name = 'win2k16'
    url = ""
    os_type = 'windows'

def get_template(name, *args, **kwargs):
    for subclass in HyperVTemplate._get_all_subclasses(HyperVTemplate):
        if subclass.name == name:
            return subclass(*args, **kwargs)
    raise exception.ValueException('No such template %s' % name)


def get_template_list():
    return [
        template.name for template in
        HyperVTemplate._get_all_subclasses(HyperVTemplate)
    ]


