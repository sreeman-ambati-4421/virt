# Disable libvirt logging

import libvirt


def libvirt_callback(ignore, err):
    return None


libvirt.registerErrorHandler(f=libvirt_callback, ctx=None)
