import libvirt

import logging
import os
from xml.etree import ElementTree

from virt.lib.linux.core.libvirt_ei import LibvirtOpen
from virt.lib.linux.core.libvirt_ei import LibBase

log = logging.getLogger(__name__)


class Domain(LibBase):
    """Wrapper around the libvirt domain object

    Args:
        name (str): Name of the domain
        memory (int): Memory size in MB. Default=512
        vcpus (int): A number of virtual CPUs. Default=1


    """
    def __init__(
            self, name, disk_file, memory=512, vcpus=1, domain_type='kvm', **kwargs):
        super(Domain, self).__init__(name)
        self._disk_file = disk_file
        self.memory = memory
        self.vcpus = vcpus
        self.device_list = []
        self._domain_type = domain_type

    @property
    def name(self):
        return self._name

    @property
    def disk_file(self):
        if self._disk_file:
            return self._disk_file

        with LibvirtOpen(self._conn, self._uri) as conn:
            _domain = conn.lookupByName(self.name)
            domain_root = ElementTree.fromstring(_domain.XMLDesc())
            return domain_root.find('./devices/disk/source').get('file')

    @name.setter
    def name(self, new_name):
        self._name = new_name

    def _get_object(self):
        with LibvirtOpen(self._conn, self._uri) as conn:
            return conn.lookupByName(self.name)

    @property
    def domain_type(self):
        return self._domain_type

    def add_device(self, device_root):
        """Add a device to domain "devices"

        The device_root must have the root which is named as "device_root" and
        its text should have the name of the subelement tag.

        Args:
            device_root (ElementTree): root object of ElementTree

        """

        self.device_list.append(device_root.find(device_root.text))

    def _get_root(self):
        root = ElementTree.Element('domain', type='kvm')
        ElementTree.SubElement(root, 'name').text = self.name
        ElementTree.SubElement(
            root, 'memory', unit='MiB').text = str(self.memory)
        ElementTree.SubElement(
            root, 'currentMemory', unit='MiB').text = str(self.memory)
        ElementTree.SubElement(
            root, 'vcpu', placement='static').text = str(self.vcpus)
        os_element = ElementTree.SubElement(root, 'os')
        ElementTree.SubElement(os_element, 'type', arch='x86_64').text = 'hvm'
        ElementTree.SubElement(os_element, 'boot', dev='hd')

        feature_element = ElementTree.SubElement(root, 'features')
        ElementTree.SubElement(feature_element, 'acpi')
        ElementTree.SubElement(feature_element, 'apic')

        #cpu_element = ElementTree.SubElement(root, 'cpu', mode='host-model')
        #ElementTree.SubElement(cpu_element, 'model', fallback='allow')
        cpu_element = ElementTree.SubElement(root, 'cpu', mode='custom')
        ElementTree.SubElement(cpu_element, 'model', fallback='allow').text = 'Haswell-noTSX'
        devices = ElementTree.SubElement(root, 'devices')

        # Add the HDD. Default. Should this be modularized like any other
        # devices?
        disk = ElementTree.SubElement(
            devices, 'disk', type='file', device='disk')
        ElementTree.SubElement(disk, 'driver', name='qemu', type='qcow2')
        ElementTree.SubElement(disk, 'source', file=self.disk_file)
        ElementTree.SubElement(disk, 'target', dev='vda', bus='virtio')

        # Some basic serial console devices
        serial_element = ElementTree.SubElement(devices, 'serial')
        ElementTree.SubElement(serial_element, 'target', port='0')
        console_element = ElementTree.SubElement(devices, 'console')
        ElementTree.SubElement(
            console_element, 'target', type='serial', port='0')
        graphics_element = ElementTree.SubElement(
            devices, 'graphics', type='vnc', port='-1', autoport='yes',
            listen='0.0.0.0')
        ElementTree.SubElement(
            graphics_element, 'listen', type='address', address='0.0.0.0')
        video_element = ElementTree.SubElement(root, 'video')
        ElementTree.SubElement(video_element, 'model', type='cirrus')

        # Add the qemu guest agent, only if the libvirt version is higher than
        # 1.0.6 which does not require source path

        channel = ElementTree.SubElement(devices, 'channel', type='unix')

        if libvirt.getVersion() < 1000006:
            ElementTree.SubElement(
                channel, 'source', mode='bind',
                path='/var/lib/libvirt/qemu/%s.agent' % self.name)
        else:
            ElementTree.SubElement(channel, 'source', mode='bind')

        ElementTree.SubElement(
            channel, 'target', type='virtio', name='org.qemu.guest_agent.0')

        for device_element in self.device_list:
            devices.append(device_element)

        return root

    def create(self, conn=None, uri=None):
        with LibvirtOpen(conn=conn, uri=uri) as conn:
            domain = conn.defineXML(self.get_xml())
            domain.create()

        log.info('Domain "%s" is successfully created' % self.name)

    def destroy(self):
        if os.access(self.disk_file, 0):
            log.info('Deleting the disk file %s ... ' % self.disk_file)
            os.remove(self.disk_file)
        super(Domain, self).remove()
