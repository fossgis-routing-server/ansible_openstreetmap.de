from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

from io import StringIO
from collections.abc import Iterable

class ActionModule(ActionBase):

    def _get_typed(self, name, typ):
        out = self._task.args.get(name, None)

        if out is not None and not isinstance(out, typ):
            raise AnsibleActionFail(f"Parameter {name} must be a {typ!s}")

        return out


    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._task.args.get('name', None)
        if not name:
            raise AnsibleActionFail("Missing required parameter 'name'")

        output = StringIO()
        output.write(f"[{name}]\nenabled = yes\n")

        for param in ('filter', 'backend', 'journalmatch', 'logpath', 'protocol'):
            value = self._get_typed(param, str)
            if value is not None:
                output.write(f"{param} = {value}\n")

        ports = self._get_typed('ports', Iterable)
        if ports is not None:
            output.write(f"ports = {ports!s}\n")

        for param in ('bantime', 'findtime', 'maxretry'):
            value = self._get_typed(param, (str, int))
            if value is not None:
                output.write(f"{param} = {value}\n")

        new_task = self._task.copy()
        new_task.args = {'dest': f'/etc/fail2ban/jail.d/50-{name}.conf',
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
