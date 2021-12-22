# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from textwrap import dedent

from ansible.errors import AnsibleFilterTypeError

def create_nginx_location_entry(location):
    """ Create an entry for a nginx site configuration serving the
        uwsgi vassal given in the string.
    """
    if not isinstance(location, str):
        raise AnsibleFilterTypeError("munin_location_nginx requires string instead of {}.".format(str(vassal)))

    return dedent(f"""\
        location {location}/static {{
            alias /etc/munin/static/;
            expires modified +1w;
        }}

        location {location}/ {{
            alias /var/cache/munin/www/;
            expires modified +310s;
        }}
    """)


class FilterModule(object):
    ''' Ansible core jinja2 filters '''

    def filters(self):
        return {
            'munin_location_nginx': create_nginx_location_entry
        }
