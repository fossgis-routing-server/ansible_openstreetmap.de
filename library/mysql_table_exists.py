#! /usr/bin/env python3

# Copyright: (c) 2020, Michael Reichert <michael.reichert@fossgis.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: mysql_table_exists

short_description: Check whether a table exists in a MySQL database

version_added: "2.9"

description:
    - "This module checks whether a table exists in a MySQL database. Login happens as user root via Unix socket."

options:
    db:
        description:
            - Database name
        required: true
    name:
        description:
            - Table name
        required: true
    login_unix_socket:
        description:
            - The path to a Unix domain socket for local connections.
        default: /var/run/mysqld/mysqld.sock

requirements:
    - PyMySQL

author:
    - Michael Reichert (@Nakaner)
'''

EXAMPLES = '''
- name: Check that a table wp_post is present in a database wpblog
  mysql_table_exists:
    db: wpblog
    table: wp_post
'''

RETURN = '''
table_exists:
    description: Whether the table exists
    type: bool
    returned: always
'''

try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False
import sys
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native


def check_args(args):
    if '"' in args['table']:
        raise AnsibleError('Invalid character \" in table name.')


def check_requirements(module):
    if not HAS_PYMYSQL:
        module.fail_json(msg='PyMySQL is required')
    if sys.version_info.major != 3:
        module.fail_json(msg='This module does not support Python 2.')
    if '`' in module.params['name']:
        module.fail_json(msg='Table name contains a ` character. This is not supported for security reasons.')


def has_table(module, result):
    found = False
    try:
        conn = pymysql.Connect(host='localhost', user='root', unix_socket=module.params['login_unix_socket'], database=module.params['db'])
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM `{}` LIMIT 1'.format(module.params['name']))
            row = cursor.fetchone()
            found = (row and len(row) == 1 and int(row[0]) == 1)
    except pymysql.err.ProgrammingError as err:
        # raised if the table does not exist
        pass
    except Exception as err:
        module.fail_json(
            msg='Failed to check whether the table exists.',
            traceback=to_native(traceback.format_exc()),
            exception=to_native(err),
            **result
        )
    finally:
        conn.close()
    return found


def run_module():
    module_args = dict(
        db=dict(type='str', required=True),
        name=dict(type='str', required=True),
        login_unix_socket=dict(type='str', default='/var/run/mysqld/mysqld.sock')
    )
    result = dict(
        changed=False,
        table_exists=False
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    check_requirements(module)
    result['table_exists'] = has_table(module, result)
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
