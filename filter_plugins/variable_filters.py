from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.errors import AnsibleError, AnsibleFilterError, AnsibleFilterTypeError
from collections.abc import Mapping, Iterable

def var_merge_lists(obj, suffix=None):
    """ Given a dictionary, find all keys with the given suffix and
        merge their respective values together. The values must be lists.
        The lists are concatenated.
    """
    if not isinstance(obj, Mapping):
        raise AnsibleFilterError(f"obj must be a dict, not a '{type(obj)}'")

    results = []

    if suffix:
        for k, v in obj.items():
            if k.endswith(suffix):
                if isinstance(v, list):
                    results.extend(v)
                else:
                    raise AnsibleFilterTypeError(f"Entry '{k} ' does not contain a list")
    else:
        raise AnsibleFilterError("Don't know what to merge")

    return results


def flatten_dict(obj, depth=1):
    """ Convert a potentially nested dictionary into a list.

        The list entries are lists of the form [key1, key2, ..., value].

        The input dictionary is to be nested at least up to the given depth.
    """
    if depth == 0:
        return [[obj]]

    if not isinstance(obj, Mapping):
        raise AnsibleFilterError(f"obj must be a dict, not a '{type(obj)}'")

    results = []

    for k, v in obj.items():
        for items in flatten_dict(v, depth - 1):
            results.append([k] + items)

    return results


def need_list(obj, field_name):
    """ Ensures that the input is a simple list. Fails otherwise with an error.
    """
    if not isinstance(obj, list):
        raise AnsibleFilterError(f"Field '{field_name}' must be a list")

    return obj


def firstof_dict(obj, *args, default=None):
    """ Return the value for the first key in the list that is found.
        If not of the keys exists in the list, return the default value.
    """
    if not isinstance(obj, Mapping):
        raise AnsibleFilterError(f"obj must be a dict, not a '{type(obj)}'")

    for key in args:
        if key in obj:
            return obj[key]

    return default


def format_join(obj, pattern, delimiter):
    """ Formats the elements of a list with 'pattern' before joining them
        with the delimiter.
    """
    if not isinstance(obj, Iterable):
        raise AnsibleFilterError(f"obj must be a list, not a '{type(obj)}'")

    return delimiter.join(pattern.format(item) for item in obj)


class FilterModule(object):
    """ Filters for merging variables from different roles or hosts.
    """

    def filters(self):
        return {
          'var_merge_lists': var_merge_lists,
          'need_list': need_list,
          'flatten_dict': flatten_dict,
          'firstof_dict': firstof_dict,
          'format_join': format_join
        }
