# Set up Ansible

Although Ansible is part of the package repositories of Debian and Ubuntu, you very likely have to install it
from Pip because we make use of the new PostgreSQL module to set up and modify databases. Unfortunately, this
module was added with Ansible 2.9.

In order to keep your system-wide Python module installation clean, use a virtual environment. Go to the
directory where you cloned this repository and run:

```sh
virtualenv --python python3 --system-site-packages _venv
source _venv/bin/activate
pip install ansible
```

Sourcing `_venv/bin/activate` will change your path and let `python` point to the binary specified with
`--python`. The same applies to `pip`. Packages installed with Pip will be stored at `_venv/`, not
`/usr/lib/` or in your home directory.

`--system-site-packages` makes use of the packages installed system-wide to satisfy dependencies. This saves
disk space.

If installing or running Ansible fails with strange exceptions, the dependencies are too old (i.e. breaking
changes since Debian/Ubuntu has packaged them). Delete your virtual environment and recreate it without
`--system-site-packages`.


# Deploying a new host

First add the host to the inventory (`hosts.yml`).

Ansible uses python (preferrably Python 3), which is not installed by default on the Hetzner images of Debian.
Hetzner Cloud images of Debian 10 contain Python3 and the APT module of Python3.
If it is a dedicated Hetzner server, install the `python3` and `python3-apt` package:

```sh
ssh root@$SERVER_HOSTNAME apt install python3 python3-apt
```

Perform the initial base installation with:

```sh
ansible-playbook site.yml -l $SERVER_HOSTNAME --tags base,accounts
```
