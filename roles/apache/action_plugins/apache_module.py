# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._task.args.get('name', None)
        state = self._task.args.get('state', 'present')

        if name is None:
            raise AnsibleActionFail("Missing required parameter 'name'")

        if state not in ('present', 'absent'):
            raise AnsibleActionFail("'state' must be one of: present, absent")

        # Create or delete the link into the 'modules-enabled' directory.
        module_args = {
            'argv': ['a2dismod' if state == 'absent' else 'a2enmod', name]
        }

        result.update(self._execute_module('ansible.builtin.command',
                                           module_args=module_args,
                                           task_vars=task_vars, tmp=tmp))
        return result
