from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

from io import StringIO
from collections.abc import Iterable

class ActionModule(ActionBase):

    def _get_typed(self, name, typ, required=False):
        out = self._task.args.get(name, None)

        if required and not out:
            raise AnsibleActionFail(f"Missing required parameter '{name}'")

        if out is not None and not isinstance(out, typ):
            raise AnsibleActionFail(f"Parameter {name} must be a {typ!s}")


        return out


    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._get_typed('name', str, required=True)
        description = self._get_typed('description', str, required=True)

        output = StringIO()
        output.write(f"# Filter '{name}' automatically installed by Ansible. Do not edit.\n")
        output.write(f"\n[Description]\n\n{description}")

        new_task = self._task.copy()
        new_task.args = {'dest': f'/etc/fail2ban/filter.d/{name}.conf',
                         'content': output.getvalue()}

        copy_action = self._shared_loader_obj.action_loader.get('ansible.builtin.copy',
                                                                task=new_task,
                                                                connection=self._connection,
                                                                play_context=self._play_context,
                                                                loader=self._loader,
                                                                templar=self._templar,
                                                                shared_loader_obj=self._shared_loader_obj)

        result.update(copy_action.run(task_vars=task_vars))

        return result

