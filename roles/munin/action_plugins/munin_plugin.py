# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from pathlib import Path
from io import StringIO


from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._task.args.get('name', None)
        src = self._task.args.get('src', None)
        config = self._task.args.get('config', None)
        state = self._task.args.get('state', 'present')

        if name is None:
            raise AnsibleActionFail("Missing required parameter 'name'")

        if src is None:
            src = name

        if not Path(src).is_absolute():
            src = '/usr/share/munin/plugins/' + src

        if config:
            outdata = StringIO()

            outdata.write(f'[{name}]\n')

            for key in ('user', 'group', 'host_name', 'timeout', 'command', 'disable_autoconf'):
                if key in config:
                    outdata.write(f'{key} {config[key]}\n')

            if 'env' in config:
                for k, v in config['env'].items():
                    outdata.write(f'env.{k} {v}\n')

            new_task = self._task.copy()
            new_task.args = {'dest': f'/etc/munin/plugin-conf.d/{name}',
                             'content': StringIO().getvalue()}

            copy_action = self._shared_loader_obj.action_loader.get('ansible.builtin.copy',
                                                                    task=new_task,
                                                                    connection=self._connection,
                                                                    play_context=self._play_context,
                                                                    loader=self._loader,
                                                                    templar=self._templar,
                                                                    shared_loader_obj=self._shared_loader_obj)
            result.update(copy_action.run(task_vars=task_vars))

            if result.get('failed', False):
                return result

        if state == 'present':
            module_args = {
                'src': src,
                'dest': '/etc/munin/plugins/' + name,
                'state': 'link'
            }
        else:
            module_args = {
                'dest': '/etc/nginx/sites-enabled/' + site,
                'state': 'absent'
            }

        result.update(self._execute_module('ansible.builtin.file',
                                           module_args=module_args,
                                           task_vars=task_vars, tmp=tmp))

        return result
