pycons3rtapi
===========

Python API for CONS3RT

Features
========

- Python bindings for CONS3RT API calls

Installation
============

Install from pip
----------------

If you have Python 2.7 installed with pip, you can run: ::

    pip install pycons3rtapi

Also you can install specific versions: ::

    pip install pycons3rtapi==0.0.2

Install from source
-------------------

::

    git clone https://github.com/cons3rt/pycons3rtapi
    cd pycons3rtapi
    python setup.py install

Install with CONS3RT assets
---------------------------

Search for community **pycons3rtapi** software assets in HmC or cons3rt.com to use.

To create your own pycons3rtapi assets, from the pycons3rtapi repo root directory, run from a Bash shell: ::

    ./scripts/make-assets.sh

This will create your own Linux and Windows pycons3rt assets for import: ::

    ./build/asset-pycons3rtapi-linux.zip
    ./build/asset-pycons3rtapi-windows.zip

Configuration
=============

Run the following command to configure pycons3rtapi: ::

    cons3rt config

Follow the instructions to create your CONS3RT API configuration.  This creates a
configuration file at **~/.cons3rt/config.json**.

Alternatively, you can stage your own config file to **~/.cons3rt/config.json**, or
use one of the samples in the **sample-configs** directory.

ReST API Tokens
~~~~~~~~~~~~~~~

Note: See the `this article <https://kb.cons3rt.com/kb/accounts/api-tokens>`_ for info
on generating an API token for one or more of your projects.

Example Usage
=============

In your python code:

::

    from pycons3rtapi.cons3rtapi import Cons3rtApi, Cons3rtApiError

    c5t = Cons3rtApi()

    # list scenarios
    scenarios = c5t.list_scenarios()

    # retrieve active deployment runs
    active_drs = c5t.list_deployment_runs_in_virtualization_realm(
        vr_id=10,
        search_type='SEARCH_ACTIVE'
    )

    # retrieve deployment run details
    active_dr_details = c5t.retrieve_deployment_run_details(dr_id='12345')

    # For some calls you can store a JSON file on the local file system and call
    # with the path to the JSON file

    # launch a deployment
    dr_id = c5t.launch_deployment_run_from_json(
        deployment_id='12345',
        json_file='/path/to/json/file.json'
    )


Here is a sample file.json for launch_deployment_run_from_json, replace
the virtualizationRealmId with yours: ::

    {
      "deploymentRunName": "ReST Test",
      "endState": "TESTS_EXECUTED_RESOURCES_RESERVED",
      "virtualizationRealmId": "12345",
      "username": "myuser",
      "password": "mypassword",
      "retainOnError": "true"
    }


CONS3RT CLI
===========

The "cons3rt" command line interface (CLI) gives you a convenience way to make
ReST API calls by typing simple commands.  If you have followed the instructions
this far you are already set up to run CLI commands.  If not, see the installation
section.

Run cons3rt CLI command as follows: ::

    cons3rt <command> <options>

Commands and various options are described below:

config
------

Configures pycons3rtapi and the CLI with your CONS3RT site connection information
and API key.

No options required.

cloudspace
----------

Perform actions on your CONS3RT cloudspaces.  You will need to get cloudspace IDs.

Options:

* --id = Specify a single cloudspace ID
* --ids = Specify a list of cloudspace IDs (e.g --ids=288,432,648)
* --release_active_runs = Releases all active runs in the cloudspace ID(s)
* --delete_inactive_runs = Deletes all inactive runs from the cloudspace ID(s)

Examples: ::

    cons3rt cloudspace --release_active_runs --delete_inactive_runs --ids=288,432,648


Asset Documentation
===================

Asset Prerequisites
-------------------

1. Git
1. Python 2.7.x
1. pip
1. [pycons3rt](https://github.com/cons3rt/pycons3rt) python package installed
1. Internet connectivity

Asset Exit Codes
----------------

Linux
~~~~~

- 0 - Success
- Non-zero - See log file in /var/log/cons3rt for more details

Windows
~~~~~~~

- 0 - Success
- Non-zero - See log file in C:\cons3rt\log for more details
