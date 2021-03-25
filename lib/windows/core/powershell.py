"""
:mod:`powershell` -- The test script template
===========================================

.. module:: virt.lib.windows.core.powershell
"""


import re
import json

from virt.lib.core import exception
from virt.lib.core import exe


class BaseHandler(object):
    """Base PowerShell Handler"""
    def __init__(self, command_format=None):
        self._command_format = (
            command_format or 'powershell "& {%s}"')

    @classmethod
    def get_powershell_version(cls):
        """Return the major version only"""
        return exe.block_run(
            'powershell ($PSVersionTable).PSVersion.ToString()')

    def exec_command(self, command):
        """Run powershell command as a raw command"""

        output = exe.block_run(
            self._command_format % command,
            universal_newlines=True, shell=True)

        if 'FullyQualifiedErrorId : ' in output:
            raise exception.ExeExitcodeException(
                command=self._command_format % command,
                exitcode=None, output=output)

        return output

    def parse_output(self, output):
        """Return the output"""
        return output


class JSONHandler(BaseHandler):
    def __init__(self):
        super(JSONHandler, self).__init__()

    def exec_command(self, command, select_clause=None, max_depth=2, **kwargs):
        param_list = []
        for param, value in kwargs.items():
            if value is True:
                param_list.append('-{}:$true'.format(param))
            elif value is False:
                param_list.append('-{}:$false'.format(param))
            elif value is None:
                continue
            else:
                if re.match('\w+$', str(value)):
                    param_list.append('-{} {}'.format(param, value))
                else:
                    param_list.append('-{} \'{}\''.format(param, value))

        params = ' '.join(param_list)
        select = '' if select_clause is None else ' | select %s' % select_clause

        output = super(JSONHandler, self).exec_command(
            command + ' ' + params + select +
            ' | convertto-json -depth %s -compress' % max_depth)

        return self.parse_output(output) if output else None

    def parse_output(self, output):
        try:
            json_obj = json.loads(output)
        except ValueError:
            raise exception.ValueException('No JSON object could be decoded')

        if isinstance(json_obj, (dict,)):
            return [type('ps_json', (object,), json_obj)]

        elif isinstance(json_obj, (list,)):
            ret_list = []
            for instance in json_obj:
                ret_list.append(type('ps_json', (object,), instance))
            return ret_list

        raise exception.ValueException(
            'json_obj is not list or dict but %s' % type(json_obj))


def exec_powershell(command, **kwargs):
    json_handler = JSONHandler()
    return json_handler.exec_command(command, **kwargs)
