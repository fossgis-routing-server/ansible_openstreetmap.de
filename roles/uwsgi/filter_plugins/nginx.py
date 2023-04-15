# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from textwrap import dedent

from ansible.errors import AnsibleFilterTypeError

def create_nginx_location_entry(vassal, location='/'):
    """ Create an entry for a nginx site configuration serving the
        uwsgi vassal given in the string.
    """
    if not isinstance(vassal, str):
        raise AnsibleFilterTypeError("uwsgi_location_nginx requires string instead of {}.".format(str(vassal)))

    return dedent(f"""\
        location {location} {{
            include /etc/nginx/uwsgi_params;
            uwsgi_pass unix:/var/run/uwsgi/{vassal}.socket;
        }}
    """)


class FilterModule(object):
    ''' Ansible core jinja2 filters '''

    def filters(self):
        return {
            'uwsgi_location_nginx': create_nginx_location_entry
        }
