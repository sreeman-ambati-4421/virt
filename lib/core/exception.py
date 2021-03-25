"""
:mod:`exception` -- The test script template
===========================================

.. module:: controller.lib.linux.<DIR>.exception
"""

__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
class VirtError(Exception):
    """A base exception class for all virt errors"""
    pass


class ConfigException(VirtError):
    pass


class ValueException(VirtError):
    pass


class AlreadyExist(VirtError):
    pass


class ExeException(VirtError):
    pass


class ExeExitcodeException(ExeException):
    def __init__(self, command, exitcode, output=None):
        self.command = command
        self.exitcode = exitcode
        self.output = output

    def __str__(self):
        return 'command %s returned non-zero exit status %s. Output: %s' % (
            self.command, self.exitcode, self.output)


class LogHandlerException(VirtError):
    pass


class RemoteLoggingException(VirtError):
    pass


class VirtualMachineException(VirtError):
    pass


class NotFoundException(VirtError):
    pass
