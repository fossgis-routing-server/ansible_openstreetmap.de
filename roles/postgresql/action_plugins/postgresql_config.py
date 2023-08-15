# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from io import StringIO
from collections.abc import Mapping

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

import jinja2

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        jinjaenv = jinja2.Environment()

        try:
            value = int(task_vars.get('postgresql__version'))
            pgver = task_vars.get('postgresql__version')
        except ValueError:
            pgvertemplate = jinjaenv.from_string(task_vars.get('postgresql__version'))
            pgver = pgvertemplate.render(
                    ansible_distribution_major_version =
                            task_vars.get('ansible_distribution_major_version'))

        name = self._task.args.get('name')
        config = self._task.args.get('config')

        if not name:
            raise AnsibleActionFail("'name' required for postgresql_config")
        if not isinstance(config, Mapping):
            raise AnsibleActionFail("'config' must be present and a dictionary of settings")

        content = StringIO()

        for k, v in config.items():
            if "'" in str(v):
                raise AnsibleActionFail("Single quotes not allowed in configuration values")
            content.write(f"{k} = '{v}'\n")

        new_task = self._task.copy()
        new_task.args = {
            'dest': f'/etc/postgresql/{pgver}/main/conf.d/{name}.conf',
            'content': content.getvalue()
        }

        action = self._shared_loader_obj.action_loader.get(
                     'ansible.builtin.copy',
                     task=new_task,
                     connection=self._connection,
                     play_context=self._play_context,
                     loader=self._loader,
                     templar=self._templar,
                     shared_loader_obj=self._shared_loader_obj)

        result.update(action.run(task_vars=task_vars))

        return result
