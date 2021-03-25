"""
:mod:`logging` -- logging library
=================================

.. module:: virt.lib.core.log_handler
This module provides some logging related functions that are necessary when
libraries are called directly from Python interpreter (i.e. standalone script)

Technically,

>>> import logging
>>> logging.getLogger()

is identical to

>>> from virt.lib.core import log_handler
>>> log_handler.get_logger()

So you do not need to use log_handler all the time. It's up to you really.

Though one reason why you need to use log_hander instead of logging is if you
logging.getLogger() only, no one will set up the logging handler therefore no
output will be displayed.

Running a test script using STAT should not be a problem since STAT calls
logging.basicConfig() and set up the logging handler.

The default logging level is DEBUG, The way to change the logging level is

>>> log_handler.setlevel(20)

And this module has some more useful functions that can parse head/tail of a
text file without storing entire file content on the memory.

"""

import logging
import platform
import os

from virt.lib.core import exception


__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
DEFAULT_FORMAT = '|%(levelname)-8s|%(message)s'
BLOCK_SIZE = 1024  # Block size to parse data at once


def get_logger(name=None, loglevel=None):
    """
    Return a logger as logging.getLogger(), but additionally run basicConfig
    only if Python interpreter is not IronPython - namely not ran by STAT.

    Args:
        name (str): Name of the logger
        loglevel (int): log level for the logger.

    """
    if '.NET' not in platform.python_compiler():
        logging.basicConfig(format=DEFAULT_FORMAT, level=logging.INFO)

    ret_logger = logging.getLogger(name=name)
    if loglevel:
        ret_logger.setLevel(loglevel)

    return ret_logger


def setlevel(level):
    logging.root.setLevel(level)


def get_head(filename, line_num):
    """
    Return a list of lines as many as line_num without storing the entire file
    content to the memory - this is for when handling a large size file.

    Args:
        filename (str): filename with an absolute path
        line_num (int): A number of lines that should be returned. If the
           entire file content has a less number of lines, return whatever
           available.

    Return:
        list: A list of lines
    """

    if not os.path.exists(filename) or not os.path.isfile(filename):
        raise exception.LogHandlerException(
            'file %s does not exist or not a file' % filename
        )

    output = ''

    with open(filename, 'r') as fileobj:
        fileobj.seek(0, os.SEEK_END)
        filesize = fileobj.tell()

        fileobj.seek(0)

        while fileobj.tell() < filesize:
            output += fileobj.read(BLOCK_SIZE)

            if output.count('\n') >= line_num:
                return output.splitlines()[:line_num]

            # File content is shorter than 1024 and no more lines are available.
            # Return as it is.
            if len(output) < BLOCK_SIZE:
                return output.splitlines()

        # Cannot find given lines. Return whatever parsed
        return output.splitlines()


def get_tail(filename, line_num):
    """
    Return a list of lines as many as line num without storing the entire file
    ceontent to the memory. This is for when handling a large size file.

    Args:
        filename (str): filename with an absolute path
        line_num (int): A number of lines that should be returned. If the
           entire file content has a less number of lines, return whatever
           available.

    Return:
        list: A list of lines
    """

    if not os.path.exists(filename) or not os.path.isfile(filename):
        raise exception.LogHandlerException(
            'file %s does not exist or not a file' % filename
        )

    output = ''

    with open(filename, 'r') as fileobj:
        fileobj.seek(0, os.SEEK_END)
        block_multiply = 1

        # File content is shorter than 1024 and no more lines are available.
        # Return as it is.
        if fileobj.tell() < BLOCK_SIZE:
            fileobj.seek(0)
            output = fileobj.read()
            return output.splitlines()[-line_num:]

        while fileobj.tell() > 0:
            fileobj.seek(-BLOCK_SIZE * block_multiply, os.SEEK_END)
            output += fileobj.read(BLOCK_SIZE)

            if output.count('\n') >= line_num:
                return output.splitlines()[-line_num:]

            block_multiply += 1

        # Cannot find given lines. Return whatever parsed
        return output.splitlines()
