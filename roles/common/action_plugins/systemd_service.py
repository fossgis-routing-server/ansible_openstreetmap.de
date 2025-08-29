# SPDX-License-Identifier: MIT
"""
module: systemd_service

short_description: Create and activate a systemd service file

description:
    - Creates or updates a systemd service files with the given content.
    - Optionally it also creates a timer and/or path unit that activates
      the given service unit.
    - The unit is immediately enabled/started according to the enabled
      and state parameters. When a timer is selected, then
      that is enabled/started insted of the main service unit.
    - Next to the options below, the module also accepts the following
      parameters from the systemd module:
      enabled, force, masked, no_block, scope, state

options:
    name:
        description:
            - Name of the service unit without the .service suffix. The same
              name will be used for the optional timer and path units.
        required: true
    service:
        description:
            - Content of the service description file in form of a YAML
              dictionary. The Unit.Description is mandatory and will be
              reused for the timer and path units.
    timer:
        description:
            - When defined, create an additional timer unit that triggers the
              main service unit. Must contain the content of the [Timer]
              section in form of a YAML dictionary.
    path:
        description:
            - When defined, create an additional path unit that triggers the
              main service unit. Must contain the content of the [Path]
              section in form of a YAML dictionary.
    socket:
        description:
            - When defined, create an additional socket unit that triggers the
              main service unit. Must contain the content of the [Socket]
              section in form of a YAML dictionary.
"""

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import configparser
from io import StringIO

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

class ActionModule(ActionBase):

    def _copy_configfile(self, dest, content, task_vars):
        config = configparser.ConfigParser()
        config.optionxform = lambda option: option
        config.read_dict(content)

        cfg_content = StringIO()
        config.write(cfg_content, space_around_delimiters=False)

        new_task = self._task.copy()
        new_task.args = {'dest': dest, 'content': cfg_content.getvalue()}

        copy_action = self._shared_loader_obj.action_loader.get('ansible.builtin.copy',
                                                                task=new_task,
                                                                connection=self._connection,
                                                                play_context=self._play_context,
                                                                loader=self._loader,
                                                                templar=self._templar,
                                                                shared_loader_obj=self._shared_loader_obj)
        return copy_action.run(task_vars=task_vars)


    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._task.args.get('name', None)
        content = self._task.args.get('service', None)
        timer = self._task.args.get('timer', None)
        path = self._task.args.get('path', None)
        socket = self._task.args.get('socket', None)
        scope = self._task.args.get('scope', 'system')

        if not name:
            raise AnsibleActionFail("Missing required parameter 'name'")

        if not content:
            raise AnsibleActionFail("Missing required parameter 'service'")

        if scope not in ('system', 'user', 'global'):
            raise AnsibleActionFail("'scope' must be one of: system, user, global")


        if scope == 'system':
            destdir = 'system'
        else:
            destdir = 'user'

        # Create the service unit file content.
        result.update(self._copy_configfile('/etc/systemd/{}/{}.service'.format(destdir, name),
                                            content, task_vars))

        if result.get('failed', False):
            return result

        changed = result.get('changed', False)

        # Create a timer if necessary
        if timer:
            cfg_content= {
                'Unit': {'Description': content['Unit']['Description'] + ' (timer)'},
                'Timer': timer,
                'Install' : {'WantedBy': 'timers.target'}
            }
            result.update(self._copy_configfile(
               '/etc/systemd/{}/{}.timer'.format(destdir, name),
               cfg_content, task_vars))

            changed = changed or result.get('changed', False)

            if result.get('failed', False):
                return result

        # Create a path service if necessary
        if path:
            cfg_content= {
                'Unit': {'Description': content['Unit']['Description'] + ' (path)',
                         'PartOf': content['Unit']['Description'] + '.service'},
                'Path': path,
                'Install' : {'WantedBy': 'multi-user.target'}
            }
            result.update(self._copy_configfile(
               '/etc/systemd/{}/{}.path'.format(destdir, name),
               cfg_content, task_vars))

            changed = changed or result.get('changed', False)

            if result.get('failed', False):
                return result

        # Create a socket service if necessary
        if socket:
            cfg_content = {
                'Unit': {'Description': content['Unit']['Description'] + ' (socket)'},
                'Socket': socket,
                'Install' : {'WantedBy': 'multi-user.target'}

            }
            result.update(self._copy_configfile(
               '/etc/systemd/{}/{}.socket'.format(destdir, name),
               cfg_content, task_vars))

            changed = changed or result.get('changed', False)

            if result.get('failed', False):
                return result

        # Enable the service
        module_args = {
            'name' : '.'.join((name, 'timer' if timer else 'service')),
            'daemon_reload': True
        }
        for param in ('enabled', 'force', 'masked', 'no_block',
                      'scope', 'state'):
            if param in self._task.args:
                module_args[param] = self._task.args[param]

        result.update(self._execute_module('ansible.builtin.systemd',
                                           module_args=module_args,
                                           task_vars=task_vars, tmp=tmp))

        return result
