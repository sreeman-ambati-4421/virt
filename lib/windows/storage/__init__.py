import os
import logging

from virt.lib.core import exception
from virt.lib.common.storage import BasePool
from virt.lib.windows.core import powershell


log = logging.getLogger(__name__)


class Pool(BasePool):
    def __init__(self, name):
        super(Pool, self).__init__(name, file_ext='vhdx', path=None)

    @property
    def path(self):
        """Return a path to the pool

        Due to Windows does not manage pools as a directory level, use the
        combination of default image directory and the given name

        This means "self._path" value will be ignored.
        """
        _path = os.path.join(
            powershell.exec_powershell(
                'get-vmhost',
                select_clause='virtualharddiskpath')[0].VirtualHardDiskPath,
            self.name)

        return _path

    def create(self):
        if not self.path:
            raise exception.ValueException('"path" is None')

        if not os.access(self.path, 0):
            log.info('Creating a directory %s ... ' % self.path)
            os.makedirs(self.path)

        log.info('"%s" is successfully created' % self.name)

    def remove(self):
        """Delete the directory"""
        if self.path:
            log.info('Removing a directory %s ... ' % self.path)
            os.removedirs(self.path)

    @property
    def exist(self):
        return os.access(self.path, 0)
