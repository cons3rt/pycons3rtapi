#!/usr/bin/env python
"""
Sets up the config.json file
"""

import os
import json
import logging
import shutil

from pycons3rt.logify import Logify
from pycons3rt.bash import mkdir_p


# Set up logger name for this module
mod_logger = Logify.get_name() + '.pycons3rtapi.cons3rtapi'

# List of site URLs
site_urls = {
    'hmc': 'https://www.milcloud.hanscom.hpc.mil/rest/api/',
    'cons3rt.com': 'https://www.cons3rt.com/rest/api/'
}

# The default site selection
default_api_url = site_urls['hmc']

# List of sites that require certificate-based auth
cert_auth_sites = [
    site_urls['hmc']
]

# String representation of the list of sites
site_url_list_str = ', '.join(site_urls.keys())

# cons3rtapi config directory
cons3rtapi_config_dir = os.path.join(os.path.expanduser('~'), '.cons3rt')

# cons3rtapi config file
cons3rtapi_config_file = os.path.join(cons3rtapi_config_dir, 'config.json')


class Cons3rtConfigError(Exception):
    """This class is an Exception type for handling errors configuring pycons3rtapi
    """
    pass


def write_config(config_data):
    """Outputs the cons3rt config to the cons3rt config dir

    :param config_data: (dict)
    :return: None
    """
    if not os.path.isdir(cons3rtapi_config_dir):
        os.makedirs(cons3rtapi_config_dir)
        print('Created your cons3rt config directory: {d}'.format(d=cons3rtapi_config_dir))

    json.dump(config_data, open(cons3rtapi_config_file, 'w'), sort_keys=True, indent=2, separators=(',', ': '))


def manual_config():
    """Manually configures your CONS3RT API

    :return: None
    """
    print('Welcome to CONS3RT!\nLet\'s set up your CONS3RT API...')

    cons3rt_config = {}

    # Get the API URL
    site_selection_input = raw_input('Enter the CONS3RT site ({v}) (default: hmc): '.format(v=site_url_list_str))

    if site_selection_input:
        site_selection = site_selection_input.strip()

        if site_selection not in site_urls.keys():
            print('ERROR: Invalid site selection [{s}], valid sites are: {v}'.format(
                s=site_selection, v=site_url_list_str))
            return 1

        cons3rt_config['api_url'] = site_urls[site_selection]
    else:
        cons3rt_config['api_url'] = default_api_url

    # Get cert or username
    if cons3rt_config['api_url'] in cert_auth_sites:
        cert_path_input = raw_input('Enter full path to your client certificate file (pem format): ')

        if not cert_path_input:
            print('ERROR: Client certificate required in PEM format to access API: [{u}]'.format(
                u=cons3rt_config['api_url']))
            return 1

        cons3rt_config['cert'] = cert_path_input.strip()

        if not os.path.isfile(cons3rt_config['cert']):
            print('ERROR: Your client certificate was not found: {c}'.format(c=cons3rt_config['cert']))
            return 1
    else:
        username_input = raw_input('CONS3RT username: ')

        if not username_input:
            print('ERROR: CONS3RT username is required.  You can find username on your account page.')
            return 1

        cons3rt_config['name'] = username_input.strip()

    # Get the Project
    project_input = raw_input('Enter your CONS3RT project name: ')

    if not project_input:
        print('ERROR: CONS3RT project name is required.  You can find this on your "My Project" page.')
        return 1

    project_name = project_input.strip()
    cons3rt_config['projects'] = [
        {
            'name': project_name
        }
    ]

    # Get the API key
    print('++++++++++++++++++++++++')
    print('You can generate a ReST API key for your project from your account/security page.')
    print('Note: The ReST API key must be associated to your project: [{p}]'.format(p=project_name))
    print('++++++++++++++++++++++++')
    rest_key_input = raw_input('Enter your project ReST API key: ')

    if not rest_key_input:
        print('ERROR: ReST API key is required.  You can find this on your account/security page.')
        return 1

    cons3rt_config['projects'][0]['rest_key'] = rest_key_input.strip()
    write_config(config_data=cons3rt_config)
    print('Congrats! Your CONS3RT API configuration is complete!')
    return 0


def asset_config(config_file_path, cert_file_path=None):
    """Configure pycons3rtapi using a config file and optional cert from the
    ASSET_DIR/media directory

    :param: cert_file_path (str) name of the certificate pem file in the media directory
    :param: config_file_path (str) name of the config file
    :return: None
    """
    log = logging.getLogger(mod_logger + '.config_pycons3rtapi')

    # Create the pycons3rtapi directory
    log.info('Creating directory: {d}'.format(d=cons3rtapi_config_dir))
    mkdir_p(cons3rtapi_config_dir)

    # Ensure the config file exists
    if not os.path.isfile(config_file_path):
        raise Cons3rtConfigError('Config file not found: {f}'.format(f=config_file_path))

    # Remove existing config file if it exists
    config_file_dest = os.path.join(cons3rtapi_config_dir, 'config.json')
    if os.path.isfile(config_file_dest):
        log.info('Removing existing config file: {f}'.format(f=config_file_dest))
        os.remove(config_file_dest)

    # Copy files to the pycons3rtapi dir
    log.info('Copying config file to directory: {d}'.format(d=cons3rtapi_config_dir))
    shutil.copy2(config_file_path, config_file_dest)

    # Stage the cert if provided
    if cert_file_path:
        log.info('Attempting to stage certificate file: {f}'.format(f=cert_file_path))

        # Ensure the cert file exists
        if not os.path.isfile(cert_file_path):
            raise Cons3rtConfigError('Certificate file not found: {f}'.format(f=cert_file_path))

        # Copy cert file to the pycons3rtapi dir
        log.info('Copying certificate file to directory: {d}'.format(d=cons3rtapi_config_dir))
        shutil.copy2(cert_file_path, cons3rtapi_config_dir)
    else:
        log.info('No cert_file_path arg provided, no cert file will be copied.')
