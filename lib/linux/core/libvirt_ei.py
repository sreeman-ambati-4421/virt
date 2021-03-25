import libvirt
import logging

from xml.etree import ElementTree
from virt.lib.core import exception


log = logging.getLogger(__name__)


class LibvirtOpen(object):
    def __init__(self, conn=None, uri=None):
        self.conn = conn or libvirt.open(uri)
        self.uri = uri

    def __enter__(self):
        return self.conn

    def __exit__(self, exception_type, exception_value, traceback):
        if self.conn:
            self.conn.close()


class LibBase(object):
    def __init__(self, name, conn=None, uri=None):
        self._name = name
        self._conn = conn
        self._uri = uri

    @property
    def name(self):
        return self._name

    @property
    def conn(self):
        return self._conn

    @property
    def uri(self):
        return self._uri

    def _get_object(self):
        """Return a libvirt object using name.

        Children classes should override this.

        """
        raise NotImplemented('Method is not implemented')

    @property
    def object(self):
        """Return the object which has the name as self.name"""

        try:
            return self._get_object()
        except libvirt.libvirtError as err:
            if 'not found' in err.message:
                return None

    def get_root(self):
        log.warning('This method will be obsolete. Use "_get_root" instead')
        self._get_root()

    def _get_root(self):
        raise NotImplemented('Method is not implemented')

    def get_xml(self):
        return ElementTree.tostring(self._get_root())

    def create(self):
        raise NotImplemented('Method is not implemented')

    def destroy(self):
        log.warning('This method will be obsolete. Use "remove" instead')
        return self.remove()

    def remove(self):
        if not self.object:
            raise exception.NotFoundException('No such object exists')

        if self.object.isActive():
            log.info('Stopping "%s" before destroying ... ' % self.name)
            self.object.destroy()
        self.object.undefine()

        log.info('"%s" is successfully destroyed' % self.name)

    def start(self):
        if not self.object:
            log.error('No such object exists')
            return False

        if self.object.isActive():
            log.info('"%s" is already running' % self.name)
        else:
            log.info('Starting "%s" ... ' % self.name)
            self.object.create()
        return True

    def stop(self):
        if not self.object:
            log.error('No such object exists')
            return False

        if self.object.isActive():
            log.info('Stopping "%s" ... ' % self.name)
            self.object.destroy()
        else:
            log.info('"%s" is not running ' % self.name)
        return True
