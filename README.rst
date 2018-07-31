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

    pip install pycons3rtapi==0.0.1

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

    ./build/asset-pycons3rt-linux.zip
    ./build/asset-pycons3rt-windows.zip

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

    cons3rt_api = Cons3rtApi(url='https://www.milcloud.hanscom.hpc.mil/rest/api/')

    # list scenarios
    scenarios = cons3rt_api.list_scenarios()

    # retrieve active deployment runs
    active_drs = cons3rt_api.list_deployment_runs_in_virtualization_realm(
        vr_id=10,
        search_type='SEARCH_ACTIVE'
    )

    # retrieve deployment run details
    active_dr_details = cons3rt_api.retrieve_deployment_run_details(dr_id='12345')

    # For some calls you can store a JSON file on the local file system and call
    # with the path to the JSON file

    # launch a deployment
    dr_id = cons3rt_api.launch_deployment_run_from_json(
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
