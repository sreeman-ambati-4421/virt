"""
:mod:`exe` -- Shell command execution tool
==========================================

.. module:: virt.lib.core.exe
"""

import sys
import subprocess
import time
import atexit

from threading import Thread
from Queue import Queue, Empty

from . import exception
from . import log_handler


__version__ = "1.0.0"  # PEP 8. Also check PEP 386 for the format.
ON_POSIX = 'posix' in sys.builtin_module_names
MAX_PROCS = 1024  # Maximum processes to be tracked
log = log_handler.get_logger(__name__)


class ProcessHandler(object):
    """
    subprocess.Popen wrapper. Few guidelines:

    * Avoid 'shell=True' option as much as possible. It spawns processes
      as children and it's difficult to maintain them, especially when
      you need to terminate all processes. Note that kill() or other
      functions will likely kill only parents, not the actual child
      process.
      Another major problem is a security issue; Official Python guide
      strongly recommends not using the shell option.
    * buffer overflow might NOT happen with this wrapper since it will
      keep flushing the buffer internally using multithread, but it's
      good to be aware about the buffer.
    * At exit of Python, this module will try to kill all spawned
      processes automatically, but this will not work when "shell=True"
      is used.

    Args:
        max_line (int): Maximum number of lines that queue will store. When
           the process gets more lines, the old lines will be removed to add
           new lines. Default=None which means no limit, but this value might
           need to be updated when memory limitation issue raises.

    Returns:
        ProcessHandler: An object to interact with shell process

    """
    procs = Queue(MAX_PROCS)

    def __init__(self, max_line=None):

        self._proc = None
        self._command = None
        self._thread = None
        self._output_queue = Queue() if max_line is None else Queue(max_line)

    @property
    def proc(self):
        return self._proc

    @property
    def command(self):
        return self._command

    def _override_kwargs(self, kwargs):
        """
        Override some kwargs.

        """

        override_values = {
            'stdout': kwargs.get('stdout', subprocess.PIPE),
            'stderr': kwargs.get('stderr', subprocess.STDOUT),
            'bufsize': 1,
            'close_fds': ON_POSIX,
        }

        kwargs.update(override_values)

        return kwargs

    def _enqueue_output(self):
        # Read until hitting an empty string
        for line in iter(self.proc.stdout.readline, b''):
            if self._output_queue.full():
                # Remove the old line, since the queue is full
                self._output_queue.get_nowait()
            self._output_queue.put_nowait(line)

        self.proc.stdout.close()

    def _read_buffer(self):
        self._thread = Thread(target=self._enqueue_output)
        self._thread.daemon = True  # Do not hang when the program exits
        self._thread.start()

    def _append_proc_handler(self):
        """
        Append the self.proc to ProcessHandler.procs. Limit the maximum length
        to MAX_PROCS so it doesn't track more than that. FIFO.

        :return:
        """

        if not ProcessHandler.procs.full():
            ProcessHandler.procs.put(self)
            return

        log.debug(
            'Process queue is reached to maximum size %s. Removing the first '
            'terminated process ... ' % MAX_PROCS
        )

        new_queue = Queue(MAX_PROCS)

        # Not ideal perform get/put many times, but for thread safety,
        # and considering a number of loop, should be okay

        while not ProcessHandler.procs.empty():
            proc_handler = ProcessHandler.procs.get()
            if proc_handler.proc.poll() is not None:  # Terminated
                log.debug(
                    'Removing the pid %s (command: %s, exitcode: %s)'
                    % (proc_handler.proc.pid, proc_handler.command,
                       proc_handler.proc.returncode)
                )

                continue  # Not adding back to the queue; namely remove

            new_queue.put(proc_handler)

        # Update the queue pointer
        ProcessHandler.procs = new_queue

        if ProcessHandler.procs.full():
            raise exception.ExeException(
                'Reached maximum queue. Cannot run anymore processes.'
            )

        ProcessHandler.procs.put(self)

        return True

    def run(self, command, **kwargs):
        """
        Non-blocking shell command execution.

        stderr, bufsize and close_fds kwargs will be
        ignored and overriden.

        Note that developers should clean up all the resources
        manually including process objects and pipes no matter how the
        process is terminated.

        Start automatically thread-safe queue to keep reading buffer
        for avoiding any buffer overflow.

        You have to make sure any blocking process is terminated before
        Python exits - otherwise the process will be still running. This
        module will try to clean up, but not guaranteed.

        Args:
            command (str): Shell comamnd that should be executed
            kwargs: keyword arguments that are passed to subprocess.Popen

        """

        # Try to add self to procs before executing shell command
        self._append_proc_handler()

        log.debug('Run command: %s' % command)
        kwargs = self._override_kwargs(kwargs)

        self._command = command

        command = command if (
            isinstance(command, (list, tuple)) or
            ('shell' in kwargs and kwargs['shell'])) else command.split()

        self._proc = subprocess.Popen(command, **kwargs)
        if kwargs.get('stdout') == subprocess.PIPE:
            self._read_buffer()

    def kill(self):
        """
        Stop running the process and clean up. Proxy to os.kill(). If return
        value is None, the process should be handled separately to clean up.

        Returns:
            int: exitcode
            None: When the process is still running
        """

        self.proc.kill()
        return self.proc.poll()

    def poll(self):
        """
        Proxy to subprocess.Popen.poll()

        Returns:
            int: exitcode
            None: When the process is still running

        """

        return self.proc.poll()

    def get_output(self):
        ret_list = []

        while 1:
            try:
                output = self._output_queue.get_nowait()
            except Empty:
                return ''.join(ret_list)
            else:
                ret_list.append(output)


def block_run(command, **kwargs):
    """
    Simple wrapper of check_output.

    Re-raise exceptions and include the output in the case that errors can
    be debugged even if exceptions are not caught.

    Args:
        command (str): Shell command that should be executed
        kwargs: keyword arguments that are passed to subprocess.check_output

    Returns:
        string: Output of the command execution

    """

    kwargs['stderr'] = kwargs['stderr'] \
        if 'stderr' in kwargs else subprocess.STDOUT

    if not kwargs.get('shell', False):
        if isinstance(command, (str, unicode)):
            # shell is False, but the command is string. technically, this is a
            # wrong value, but just split and use it
            command = command.split()
        log.debug('Run command: %s' % subprocess.list2cmdline(command))
    else:
        # shell is True. Should pass the command as it is
        log.debug('Run command: %s' % command)

    try:
        if sys.version_info >= (2, 7):
            output = subprocess.check_output(command, **kwargs)
        else:
            proc = run(command, **kwargs)

            while proc.poll() is None or proc._thread.is_alive():
                time.sleep(0.1)

            output = proc.get_output()

            if proc.poll() != 0:
                raise exception.ExeExitcodeException(
                    command=command,
                    exitcode=proc.poll(),
                    output=output
                )

    except subprocess.CalledProcessError as err:
        raise exception.ExeExitcodeException(
            command=err.cmd,
            exitcode=err.returncode,
            output=err.output
        )
    else:
        log.debug('Output: %s' % output)
        return output


def run(command, max_line=None, **kwargs):
    """
    Proxy to ProcessHandler.run()

    Args:
        command (str): Shell comamnd that should be executed
        max_lines (int): Maximum number of lines that queue will store. When
           the process gets more lines, the old lines will be removed to add
           new lines. Default=None which means no limit, but this value might
           need to be updated when memory limitation issue raises.
        kwargs: keyword arguments that are passed to subprocess.Popen
    Return:
       ProcessHandler: ProcessHandler that you can interact with the process,
          such as start, stop, get_output, etc.

    """

    ph = ProcessHandler(max_line=max_line)
    ph.run(command=command, **kwargs)
    return ph


@atexit.register
def _terminate():
    """
    Try to clean up the resources at exit. Note that if you use the option
    "shell=True" for subprocess, this will likely only kill parents.

    This should not be called by any other modules but atexit.

    """

    while not ProcessHandler.procs.empty():
        proc_handler = ProcessHandler.procs.get()
        if proc_handler.proc is not None and proc_handler.proc.poll() is None:
            proc_handler.proc.kill()
            proc_handler.proc.poll()
