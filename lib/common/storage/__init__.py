"""
:mod:`storage` -- Storage/pool library
======================================

.. module:: virt.lib.common.storage
This library provides APIs to interact with storage pool.

KVM and Hyper-V have different definition of a storage pool, Windows does NOT
accept an argument "path" but simply use a combination of default virtual disk
path and a name of pool. On the other hand, you can freely set a path of a new
pool.

For example, on Linux,

>>> from virt.lib.linux.storage import Pool
>>> lnx_pool = Pool(name='vm_test', path='/vm_pool/vm_test')

Will create a storage pool where a directory is '/vm_pool/vm'

>>> lnx_pool.path
'/vm_pool/vm_test'

On the other hand, on Windows,

>>> from virt.lib.windows.storage import Pool
>>> win_pool = Pool(name='vm')

Again, note that Windows "Pool" class does NOT accept the "path" argument.

>>> win_pool.path
u'D:\\\\vm_pool\\\\vm_tset'

The path "D:\\vm_pool" is a directory comes from Hyper-V's setting
"Virtual Hard Disks"

Once you have the instantiated object, you can create a pool by calling the
"create" method

>>> lnx_pool.create()


"""

import platform
import importlib


class BasePool(object):
    """An abstract class to define storage pool

    Args:
        name (str): Name of storage pool
        file_ext (str): virtual disk extension i.e.) vhdx, qcow2 This
            should be passed by a child class
        path (str, None): An absolute path to a storage pool. If None,
            assume a storage pool that has the given name exists and return
            its path. if no such storage pool exists, raise exception
    """

    def __init__(self, name, file_ext, path=None, **kwargs):
        self._name = name
        self._path = path
        self._file_ext = file_ext

    @property
    def name(self):
        """Return a name of a storage pool"""
        return self._name

    @property
    def path(self):
        """Return a path to a virtual disk

        The return value should be different depending on whether "path"
        argument in the constructor is given or not. If it is given, simply
        return it. Otherwise this property should look for a storage pool that
        has the given name and return its path.
        """
        raise NotImplementedError

    @path.setter
    def path(self, new_path):
        """Set a new path of a storage pool"""
        self._path = new_path

    @property
    def exist(self):
        """Return True if the pool exists. otherwise return False"""
        raise NotImplementedError

    @property
    def file_ext(self):
        """Return a file extension i.e.) qcow2, vhdx for this storage pool"""
        return self._file_ext

    def create(self):
        """Create a new storage pool at the given path"""
        raise NotImplementedError

    def remove(self):
        """Remove a storage"""
        raise NotImplementedError


def get_pool(name, path=None, **kwargs):
    """A factory method that return a storage pool object"""
    storage = importlib.import_module(
        'virt.lib.%s.storage' % platform.system().lower())
    return storage.Pool(name=name, path=path, **kwargs)
