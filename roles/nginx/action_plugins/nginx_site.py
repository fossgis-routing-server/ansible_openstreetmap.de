# SPDX-License-Identifier: MIT
# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        site = self._task.args.get('site', None)
        state = self._task.args.get('state', 'present')
        src = self._task.args.get('src')

        if site is None:
            raise AnsibleActionFail("Missing required parameter 'site'")

        if src is None:
            raise AnsibleActionFail("Missing required parameter 'src'")

        if state not in ('present', 'absent'):
            raise AnsibleActionFail("'state' must be one of: present, absent")

        # Create the site configuration file from the given template.
        if state == 'present':
            new_task = self._task.copy()

            new_task.args = {
                'dest': f'/etc/nginx/sites-available/{site}',
                'owner': 'www-data',
                'group': 'www-data',
                'mode': '0644',
                'src': 'roles/nginx/templates/nginx_site_macros.jinja'
            }

            new_task_vars = task_vars.copy()
            new_task_vars['nginx_site_body'] = src

            template_action = self._shared_loader_obj.action_loader.get(
                'ansible.builtin.template',
                task=new_task,
                connection=self._connection,
                play_context=self._play_context,
                loader=self._loader,
                templar=self._templar,
                shared_loader_obj=self._shared_loader_obj
            )
            result.update(template_action.run(task_vars=new_task_vars))

            if result.get('failed', False):
                return result

        # Create or delete the link into the 'sites-enabled' directory.
        if state == 'present':
            module_args = {
                'src': f'../sites-available/{site}',
                'dest': f'/etc/nginx/sites-enabled/{site}',
                'state': 'link',
                'owner': 'www-data',
                'group': 'www-data'
            }
        else:
            module_args = {
                'dest': f'/etc/nginx/sites-enabled/{site}',
                'state': 'absent'
            }

        next_result = self._execute_module(
            'ansible.builtin.file',
            module_args=module_args,
            task_vars=task_vars, tmp=tmp
        )
        if result.get('changed', False):
            next_result['changed'] = True

        return next_result
