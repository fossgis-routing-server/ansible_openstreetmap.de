# SPDX-License-Identifier: MIT

"""
module: system_account

short_description: Create a system account and group

description:
    - This module creates a new user account with system flag for the given
      name.
    - In addition it creates a new group with the same name as the system
      user and makes this group the primary group of the user.
    - The shell for the user is '/bin/false' unless explicitly set otherwise.
    - The module passes the following options on to user creation:
      state, shell, comment, create_home, home, groups
"""

#Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._task.args.get('name')
        state = self._task.args.get('state', 'present')
        shell = self._task.args.get('shell', '/bin/false')

        # First, create the group.
        module_args = {
            'name': name,
            'system': True,
            'state': state
        }

        result.update(self._execute_module('ansible.builtin.group',
                                           module_args=module_args,
                                           task_vars=task_vars, tmp=tmp))

        if result.get('failed', False):
            return result

        # Next proceed to create the user.
        module_args = {
            'name': name,
            'group': name,
            'state': state,
            'system': True,
            'shell' : shell
        }
        for param in ('comment', 'create_home', 'home', 'groups'):
            if param in self._task.args:
                module_args[param] = self._task.args[param]

        result.update(self._execute_module('ansible.builtin.user',
                                           module_args=module_args,
                                           task_vars=task_vars, tmp=tmp))

        return result
