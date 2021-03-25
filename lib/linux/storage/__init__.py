import os
import logging
from xml.etree import ElementTree as ET
from libvirt import libvirtError

from virt.lib.core import exception
from virt.lib.common.storage import BasePool
from virt.lib.linux.core.libvirt_ei import LibvirtOpen
from virt.lib.linux.core.libvirt_ei import LibBase


log = logging.getLogger(__name__)


class Pool(LibBase, BasePool):
    def __init__(self, name, path=None, conn=None, uri=None):
        super(Pool, self).__init__(name, conn, uri)
        self._path = path
        self._file_ext = 'qcow2'

    @property
    def path(self):
        if not self._path:  # When path is expected to be returned by libvirt
            if not self.object:  # No such libvirt object exists. Return None
                return None

            root = ET.fromstring(self.object.XMLDesc())
            target = root.find('target')
            return target.find('path').text

        return self._path

    def _get_object(self):
        with LibvirtOpen(self.conn, self.uri) as conn:
            return conn.storagePoolLookupByName(self.name)

    def _get_root(self):
        root = ET.Element('pool', type='dir')
        ET.SubElement(root, 'name').text = self.name
        target = ET.SubElement(root, 'target')
        ET.SubElement(target, 'path').text = self.path

        return root

    def create(self):
        if not self.path:
            raise exception.ValueException('"path" is None')

        if not os.access(self.path, 0):
            log.info('Creating a directory %s ... ' % self.path)
            os.makedirs(self.path)

        with LibvirtOpen(conn=self._conn, uri=self._uri) as conn:
            pool = conn.storagePoolDefineXML(self.get_xml())
            pool.setAutostart(1)
            pool.create()

        log.info('"%s" is successfully created' % self.name)

    @property
    def exist(self):
        try:
            self._get_object()
        except libvirtError as err:
            if 'Storage pool not found' in err.message:
                return False
            raise
        return True
