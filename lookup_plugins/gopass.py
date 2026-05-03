#!/usr/bin/env python3¬
# -*- coding: utf-8 -*

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import subprocess

DOCUMENTATION = """
    lookup: gopass
    author: Jaan Janesmae <git@janesmae.com>
    short_description: read the value of gopass secrets
    description:
        - Allows you to query the values of gopass secrets available for the current user.
    options:
      _terms:
        description: path of secret to read
        required: True
"""

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

def cleanPwOnly(s):
    """
    In case only one line is returned, clean the trailing newline
    Assume only the password is needed where the newline is not part of it
    """
    if s.count('\n') == 1:
        return s.strip()
    return s

class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        res = []

        # Extract the 'check' parameter, defaulting to False
        check_mode = kwargs.get('check', False)

        display.debug("gopass lookup secret: %s" % terms[0])
        result = subprocess.run(["gopass", "show", "%s" % (terms[0])], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        display.vvvv(u"gopass lookup secret at %s" % result)

        if check_mode:
            res.append(result.returncode == 0)
        else:
            try:
                if result.returncode == 0:
                    res.append(cleanPwOnly(result.stdout.decode("utf-8")))
                else:
                    raise AnsibleParserError()
            except AnsibleParserError:
                display.v("could not locate secret in lookup: %s" % terms[0])
                if 'default' in kwargs:
                    res.append(kwargs.get('default'))
                else:
                    raise AnsibleError("could not locate secret in lookup: %s" % terms[0])

        return res
