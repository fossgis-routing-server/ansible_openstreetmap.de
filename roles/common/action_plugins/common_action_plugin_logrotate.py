# This script is from
# https://gist.github.com/lonvia/0c24ec09bcd897ae85cdce2750f47c0a
#
# Installation of logrotate configuration

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from collections.abc import Mapping, Iterable
from io import StringIO

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail


def normalized_content(content):
    if isinstance(content, Mapping):
        content = [content]
    elif not isinstance(content, Iterable):
        raise AnsibleActionFail("Parameter 'content' must be a list.")

    for entry in content:
        if 'dest' not in entry:
            raise AnsibleActionFail("Missing 'dest' in 'content' list entry.")

        if 'settings' not in entry:
            settings = []
        elif isinstance(entry['settings'], str):
            settings = [entry['settings']]
        elif isinstance(entry['settings'], Iterable):
            settings = entry['settings']
        else:
            raise AnsibleActionFail("Parameter 'settings' in content list must be a list.")

        yield (entry['dest'], settings)


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._task.args.get('name', None)
        content = self._task.args.get('content', None)

        if not name:
            raise AnsibleActionFail("Missing required parameter 'name'")

        if not content:
            raise AnsibleActionFail("Missing required parameter 'content'")

        output = StringIO()
        for dest, settings in normalized_content(content):
            output.write(f"{dest} {{\n")
            for line in settings:
                output.write(f'  {line}\n')
            output.write("}\n\n")

        new_task = self._task.copy()
        new_task.args = {'dest': f'/etc/logrotate.d/{name}', 'content': output.getvalue()}

        copy_action = self._shared_loader_obj.action_loader.get('ansible.builtin.copy',
                                                                task=new_task,
                                                                connection=self._connection,
                                                                play_context=self._play_context,
                                                                loader=self._loader,
                                                                templar=self._templar,
                                                                shared_loader_obj=self._shared_loader_obj)

        result.update(copy_action.run(task_vars=task_vars))

        return result