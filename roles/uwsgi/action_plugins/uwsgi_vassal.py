# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from io import StringIO
from collections.abc import Mapping

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._task.args.get('name')
        env = self._task.args.get('env')
        pythonpath = self._task.args.get('pythonpath')

        if not name:
            raise AnsibleActionFail("'name' required for uwsgi_vassal")

        # Build the config file.
        content = StringIO()
        content.write('[uwsgi]\n\n')

        for key, value in self._task.args.items():
            if key == 'env':
                if not isinstance(value, Mapping):
                    raise AnsibleActionFail("'env' expected to be a dictionary.")
                for envkey, envval in value.items():
                    content.write('env = {}={}\n'.format(envkey, envval))
            elif key == 'pythonpath':
                if not isinstance(value, list):
                    value = [value]
                for path in value:
                    content.write('pythonpath = ' + path + '\n')
            else:
                content.write('{} = {}\n'.format(key.replace('_', '-') , str(value)))

        content.write('socket = /var/run/uwsgi/' + name + '.socket\n')

        # Copy the file over.
        new_task = self._task.copy()

        new_task.args = {
            'dest': '/etc/uwsgi-emperor/vassals/' + name + '.ini',
            'content': content.getvalue()
        }

        for arg in ('owner', 'group'):
            if arg in self._task.args:
                new_task.args[arg] = self._task.args[arg]

        copy_action = self._shared_loader_obj.action_loader.get('ansible.builtin.copy',
                                                                task=new_task,
                                                                connection=self._connection,
                                                                play_context=self._play_context,
                                                                loader=self._loader,
                                                                templar=self._templar,
                                                                shared_loader_obj=self._shared_loader_obj)
        result.update(copy_action.run(task_vars=task_vars))

        return result
