#!/usr/bin/env python

import json
import logging
import os
import sys

from pycons3rt.logify import Logify

from cons3rtclient import Cons3rtClient
from pycons3rtlibs import RestUser, Cons3rtClientError, Cons3rtApiError
from cons3rtconfig import cons3rtapi_config_file


# Set up logger name for this module
mod_logger = Logify.get_name() + '.pycons3rtapi.cons3rtapi'


class Cons3rtApi:

    def __init__(self, url=None, base_dir=None, user=None, config_file=cons3rtapi_config_file, project=None):
        self.cls_logger = mod_logger + '.Cons3rtApi'
        self.user = user
        self.url_base = url
        self.base_dir = base_dir
        self.project = project
        self.retries = ''
        self.timeout = ''
        self.queries = ''
        self.virtrealm = ''
        self.config_file = config_file
        self.config_data = {}
        self.user_list = []
        if self.user is None:
            self.load_config()
        self.cons3rt_client = Cons3rtClient(base=self.url_base, user=self.user)

    def load_config(self):
        """Loads the default config file

        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.load_config')
        log.info('Loading pycons3rtapi configuration...')

        # Ensure the file_path file exists
        if not os.path.isfile(self.config_file):
            msg = 'Cons3rtApi config file is required but not found: {f}'.format(f=self.config_file)
            raise Cons3rtApiError(msg)

        # Load the config file
        try:
            with open(self.config_file, 'r') as f:
                self.config_data = json.load(f)
        except(OSError, IOError):
            _, ex, trace = sys.exc_info()
            msg = 'Unable to read the Cons3rtApi config file: {f}\n{e}'.format(f=self.config_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        else:
            log.debug('Loading config data from file: {f}'.format(f=self.config_file))

        # Attempt to load the URL
        try:
            self.url_base = self.config_data['api_url']
        except KeyError:
            raise Cons3rtApiError('api_url is required but not defined in the config file')
        log.info('Using CONS3RT API URL: {u}'.format(u=self.url_base))

        # Attempt to find a username in the config data
        try:
            username = self.config_data['name']
        except KeyError:
            username = None

        # Attempt to find a cert_file_path in the config data
        try:
            cert_file_path = self.config_data['cert']
        except KeyError:
            cert_file_path = None
        else:
            # Ensure the cert_file_path points to an actual file
            if not os.path.isfile(cert_file_path):
                raise Cons3rtApiError('config.json provided a cert, but the cert file was not found: {f}'.format(
                    f=cert_file_path))
            log.info('Found certificate file: {f}'.format(f=cert_file_path))

        # Ensure that either a username or cert_file_path was found
        if username is None and cert_file_path is None:
            raise Cons3rtApiError('The pycons3rtapi config.json file must contain values for either name or cert')

        # Ensure at least one token is found
        try:
            project_token_list = self.config_data['projects']
        except KeyError:
            _, ex, trace = sys.exc_info()
            msg = 'Element [projects] is required but not found in the config data, at least 1 project token must ' \
                  'be configured\n{e}'.format(e=str(ex))
            raise Cons3rtApiError, msg, trace

        # Attempt to create a ReST user for each project in the list
        for project in project_token_list:
            try:
                token = project['rest_key']
                project_name = project['name']
            except KeyError:
                log.warn('Found an invalid project token, skipping: {p}'.format(p=str(project)))
                continue

            # Create a ReST User for the project/token pair
            log.debug('Found rest token for project {p}: {t}'.format(p=project, t=token))

            # Create a cert-based auth or username-based auth user depending on the config
            if cert_file_path:
                self.user_list.append(RestUser(token=token, project=project_name, cert_file_path=cert_file_path))
            elif username:
                self.user_list.append(RestUser(token=token, project=project_name, username=username))

        # Ensure that at least one valid project/token was found
        if len(self.user_list) < 1:
            raise Cons3rtApiError('A ReST API token was not found in config file: {f}'.format(f=self.config_file))

        log.info('Found {n} project/token pairs'.format(n=str(len(self.user_list))))

        # Select the first user to use as the default
        self.user = self.user_list[0]
        if self.project is not None:
            self.set_project_token(project_name=self.project)
        log.info('Set project to [{p}] and ReST API token: {t}'.format(p=self.user.project_name, t=self.user.token))

    def set_project_token(self, project_name):
        """Sets the project name and token to the specified project name.  This project name
        must already exist in config data

        :param project_name: (str) name of the project
        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.set_project_token')

        # Ensure the project_name is a string
        if not isinstance(project_name, basestring):
            raise Cons3rtApiError('The arg project_name must be a string, found: {t}'.format(
                t=project_name.__class__.__name__))

        # Loop through the projects until the project matches
        found = False
        log.info('Attempting to set the project token pair for project: {p}'.format(p=project_name))
        for rest_user in self.user_list:
            log.debug('Checking if rest user matches project [{p}]: {u}'.format(p=project_name, u=str(rest_user)))
            if rest_user.project_name == project_name:
                log.info('Found matching rest user: {u}'.format(u=str(rest_user)))
                self.user = rest_user
                found = True
                break
        if found:
            log.info('Set project to [{p}] and ReST API token: {t}'.format(p=self.user.project_name, t=self.user.token))
        else:
            log.warn('Matching ReST User not found for project: {p}'.format(p=project_name))

    def get_asset_type(self, asset_type):
        """Translates the user-provided asset type to an actual ReST target

        :param asset_type: (str) provided asset type
        :return: (str) asset type ReSt target
        """
        log = logging.getLogger(self.cls_logger + '.get_asset_type')

        # Determine the target based on asset_type
        target = ''
        if 'scenario' in asset_type.lower():
            target = 'scenarios'
        elif 'deployment' in asset_type.lower():
            target = 'deployments'
        elif 'software' in asset_type.lower():
            target = 'software'
        elif 'system' in asset_type.lower():
            target = 'systems'
        elif 'test' in asset_type.lower():
            target = 'testassets'
        else:
            log.warn('Unable to determine the target from provided asset_type: {t}'.format(t=asset_type))
        return target

    def register_cloud_from_json(self, json_file):
        """Attempts to register a Cloud using the provided JSON
        file as the payload

        :param json_file: (str) path to the JSON file
        :return: (int) Cloud ID
        :raises Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.register_cloud_from_json')

        # Ensure the json_file arg is a string
        if not isinstance(json_file, basestring):
            msg = 'The json_file arg must be a string'
            raise ValueError(msg)

        # Ensure the JSON file exists
        if not os.path.isfile(json_file):
            msg = 'JSON file not found: {f}'.format(f=json_file)
            raise OSError(msg)

        # Attempt to register the Cloud
        try:
            cloud_id = self.cons3rt_client.register_cloud(cloud_file=json_file)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to register a Cloud using JSON file: {f}\n{e}'.format(
                n=ex.__class__.__name__, f=json_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully registered Cloud ID: {c}'.format(c=str(cloud_id)))
        return cloud_id

    def create_team_from_json(self, json_file):
        """Attempts to create a Team using the provided JSON
        file as the payload

        :param json_file: (str) path to the JSON file
        :return: (int) Team ID
        :raises Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.create_team_from_json')

        # Ensure the json_file arg is a string
        if not isinstance(json_file, basestring):
            msg = 'The json_file arg must be a string'
            raise ValueError(msg)

        # Ensure the JSON file exists
        if not os.path.isfile(json_file):
            msg = 'JSON file not found: {f}'.format(f=json_file)
            raise OSError(msg)

        # Attempt to create the team
        try:
            team_id = self.cons3rt_client.create_team(team_file=json_file)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to create a Team using JSON file: {f}\n{e}'.format(
                n=ex.__class__.__name__, f=json_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully created Team ID: {c}'.format(c=str(team_id)))
        return team_id

    def register_virtualization_realm_to_cloud_from_json(self, cloud_id, json_file):
        """Attempts to register a virtualization realm using
        the provided JSON file as the payload

        :param cloud_id: (int) Cloud ID to register the VR under
        :param json_file: (str) path to JSON file
        :return: (int) Virtualization Realm ID
        :raises Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.register_virtualization_realm_to_cloud_from_json')

        # Ensure the json_file arg is a string
        if not isinstance(json_file, basestring):
            msg = 'The json_file arg must be a string'
            raise Cons3rtApiError(msg)

        # Ensure the cloud_id is an int
        if not isinstance(cloud_id, int):
            try:
                cloud_id = int(cloud_id)
            except ValueError:
                msg = 'The cloud_id arg must be an int'
                raise Cons3rtApiError(msg)

        # Ensure the JSON file exists
        if not os.path.isfile(json_file):
            msg = 'JSON file not found: {f}'.format(f=json_file)
            raise OSError(msg)

        # Attempt to register the virtualization realm to the Cloud ID
        try:
            vr_id = self.cons3rt_client.register_virtualization_realm(
                cloud_id=cloud_id,
                virtualization_realm_file=json_file)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to register virtualization realm to Cloud ID {c} from file: {f}\n{e}'.format(
                n=ex.__class__.__name__, c=cloud_id, f=json_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Registered new Virtualization Realm ID {v} to Cloud ID: {c}'.format(v=str(vr_id), c=str(cloud_id)))
        return vr_id

    def allocate_virtualization_realm_to_cloud_from_json(self, cloud_id, json_file):
        """Attempts to allocate a virtualization realm using
        the provided JSON file as the payload

        :param cloud_id: (int) Cloud ID to allocate the VR under
        :param json_file: (str) path to JSON file
        :return: (int) Virtualization Realm ID
        :raises Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.allocate_virtualization_realm_to_cloud_from_json')

        # Ensure the json_file arg is a string
        if not isinstance(json_file, basestring):
            msg = 'The json_file arg must be a string'
            raise Cons3rtApiError(msg)

        # Ensure the cloud_id is an int
        if not isinstance(cloud_id, int):
            try:
                cloud_id = int(cloud_id)
            except ValueError:
                msg = 'The cloud_id arg must be an int'
                raise Cons3rtApiError(msg)

        # Ensure the JSON file exists
        if not os.path.isfile(json_file):
            msg = 'JSON file not found: {f}'.format(f=json_file)
            raise OSError(msg)

        # Attempt to register the virtualization realm to the Cloud ID
        try:
            vr_id = self.cons3rt_client.allocate_virtualization_realm(
                cloud_id=cloud_id,
                allocate_virtualization_realm_file=json_file)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to allocate virtualization realm to Cloud ID {c} from file: {f}'.format(
                n=ex.__class__.__name__, c=cloud_id, f=json_file)
            raise Cons3rtApiError, msg, trace
        log.info('Allocated new Virtualization Realm ID {v} to Cloud ID: {c}'.format(v=str(vr_id), c=str(cloud_id)))
        return vr_id

    def list_projects(self):
        """Query CONS3RT to return a list of projects for the current user

        :return: (list) of Project info
        """
        log = logging.getLogger(self.cls_logger + '.list_projects')
        log.debug('Attempting to list projects for user: {u}'.format(u=self.user.username))
        try:
            projects = self.cons3rt_client.list_projects()
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a list of projects\n{e}'.format(e=str(ex))
            raise Cons3rtApiError, msg, trace
        return projects

    def list_expanded_projects(self):
        """Query CONS3RT to return a list of projects the current user is not a member of

        :return: (list) of Project info
        """
        log = logging.getLogger(self.cls_logger + '.list_expanded_projects')
        log.debug('Attempting to list non-member projects for user: {u}'.format(u=self.user.username))
        try:
            projects = self.cons3rt_client.list_expanded_projects()
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a list of projects\n{e}'.format(e=str(ex))
            raise Cons3rtApiError, msg, trace
        return projects

    def list_all_projects(self):
        """Query CONS3RT to return a list of all projects on the site

        :return: (list) of Project info
        """
        log = logging.getLogger(self.cls_logger + '.list_all_projects')
        log.debug('Attempting to list all projects...')
        try:
            member_projects = self.cons3rt_client.list_projects()
            non_member_projects = self.cons3rt_client.list_expanded_projects()
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a list of projects\n{e}'.format(e=str(ex))
            raise Cons3rtApiError, msg, trace
        return member_projects + non_member_projects

    def get_project_details(self, project_id):
        """Returns details for the specified project ID

        :param (int) project_id: ID of the project to query
        :return: (dict) details for the project ID
        """
        log = logging.getLogger(self.cls_logger + '.get_project_details')

        # Ensure the vr_id is an int
        if not isinstance(project_id, int):
            try:
                project_id = int(project_id)
            except ValueError:
                msg = 'project_id arg must be an Integer, found: {t}'.format(t=project_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        log.debug('Attempting query project ID {i}'.format(i=str(project_id)))
        try:
            project_details = self.cons3rt_client.get_project_details(project_id=project_id)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for details on project: {i}\n{e}'.format(i=str(project_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        return project_details

    def get_project_id(self, project_name):
        """Given a project name, return a list of IDs with that name

        :param project_name: (str) name of the project
        :return: (list) of project IDs (int)
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.get_project_id')

        if not isinstance(project_name, basestring):
            raise Cons3rtApiError('Expected project_name arg to be a string, found: {t}'.format(
                t=project_name.__class__.__name__)
            )

        project_id_list = []

        # List all projects
        log.debug('Getting a list of all projects...')
        try:
            projects = self.list_all_projects()
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            msg = 'Cons3rtApiError: There was a problem listing all projects\n{e}'.format(e=str(ex))
            raise Cons3rtApiError, msg, trace

        # Look for project IDs with matching names
        log.debug('Looking for projects with name: {n}'.format(n=project_name))
        for project in projects:
            if project['name'] == project_name:
                project_id_list.append(project['id'])

        # Raise an error if the project was not found
        if len(project_id_list) < 1:
            raise Cons3rtApiError('Project not found: {f}'.format(f=project_name))

        # Return the list of IDs
        return project_id_list

    def list_projects_in_virtualization_realm(self, vr_id):
        """Queries CONS3RT for a list of projects in the virtualization realm

        :param vr_id: (int) virtualization realm ID
        :return: (list) of projects
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.list_projects_in_virtualization_realm')

        # Ensure the vr_id is an int
        if not isinstance(vr_id, int):
            try:
                vr_id = int(vr_id)
            except ValueError:
                msg = 'vr_id arg must be an Integer, found: {t}'.format(t=vr_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        log.debug('Attempting to list projects in virtualization realm ID: {i}'.format(i=str(vr_id)))
        try:
            projects = self.cons3rt_client.list_projects_in_virtualization_realm(vr_id=vr_id)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a list of projects in virtualization realm ID: {i}\n{e}'.format(
                i=str(vr_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        return projects

    def list_clouds(self):
        """Query CONS3RT to return a list of the currently configured Clouds

        :return: (list) of Cloud Info
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.list_clouds')
        log.info('Attempting to list clouds...')
        try:
            clouds = self.cons3rt_client.list_clouds()
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a list of Clouds\n{e}'.format(e=str(ex))
            raise Cons3rtApiError, msg, trace
        return clouds

    def list_teams(self):
        """Query CONS3RT to return a list of Teams

        :return: (list) of Team Info
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.list_teams')
        log.info('Attempting to list teams...')
        try:
            teams = self.cons3rt_client.list_teams()
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a list of Teams\n{e}'.format(e=str(ex))
            raise Cons3rtApiError, msg, trace
        return teams

    def get_team_details(self, team_id):
        """Returns details for the specified team ID

        :param (int) team_id: ID of the team to query
        :return: (dict) details for the team ID
        """
        log = logging.getLogger(self.cls_logger + '.get_team_details')

        # Ensure the vr_id is an int
        if not isinstance(team_id, int):
            try:
                team_id = int(team_id)
            except ValueError:
                msg = 'team_id arg must be an Integer, found: {t}'.format(t=team_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        log.debug('Attempting query team ID {i}'.format(i=str(team_id)))
        try:
            team_details = self.cons3rt_client.get_team_details(team_id=team_id)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for details on team: {i}\n{e}'.format(i=str(team_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        return team_details

    def list_scenarios(self):
        """Query CONS3RT to return a list of Scenarios

        :return: (list) of Scenario Info
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.list_scenarios')
        log.info('Attempting to get a list of scenarios...')
        try:
            scenarios = self.cons3rt_client.list_scenarios()
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a list of scenarios\n{e}'.format(e=str(ex))
            raise Cons3rtApiError, msg, trace
        return scenarios

    def list_deployments(self):
        """Query CONS3RT to return a list of Deployments

        :return: (list) of Deployments Info
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.list_deployments')
        log.info('Attempting to get a list of deployments...')
        try:
            deployments = self.cons3rt_client.list_deployments()
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a list of deployments\n{e}'.format(e=str(ex))
            raise Cons3rtApiError, msg, trace
        return deployments

    def list_deployment_runs_in_virtualization_realm(self, vr_id, search_type='SEARCH_ALL'):
        """Query CONS3RT to return a list of deployment runs in a virtualization realm

        :param: vr_id: (int) virtualization realm ID
        :param: search_type (str) the run status to filter the search on
        :return: (list) of deployment runs
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.list_deployment_runs_in_virtualization_realm')

        # Ensure the vr_id is an int
        if not isinstance(vr_id, int):
            try:
                vr_id = int(vr_id)
            except ValueError:
                msg = 'vr_id arg must be an Integer, found: {t}'.format(t=vr_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        # Ensure status is valid
        if not isinstance(search_type, basestring):
            raise Cons3rtApiError('Arg search_type must be a string, found type: {t}'.format(
                t=search_type.__class__.__name__))

        valid_search_type = ['SEARCH_ACTIVE', 'SEARCH_ALL', 'SEARCH_AVAILABLE', 'SEARCH_COMPOSING',
                             'SEARCH_DECOMPOSING', 'SEARCH_INACTIVE', 'SEARCH_PROCESSING', 'SEARCH_SCHEDULED',
                             'SEARCH_TESTING', 'SEARCH_SCHEDULED_AND_ACTIVE']

        search_type = search_type.upper()
        if search_type not in valid_search_type:
            raise Cons3rtApiError('Arg status provided is not valid, must be one of: {s}'.format(
                s=', '.join(search_type)))

        # Attempt to get a list of deployment runs
        log.info('Attempting to get a list of deployment runs with search_type {s} in '
                 'virtualization realm ID: {i}'.format(i=str(vr_id), s=search_type))
        try:
            drs = self.cons3rt_client.list_deployment_runs_in_virtualization_realm(vr_id=vr_id, search_type=search_type)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT VR ID {i} for a list of deployment runs\n{e}'.format(
                i=str(vr_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Found {n} runs in VR ID: {i}'.format(i=str(vr_id), n=str(len(drs))))
        return drs

    def retrieve_deployment_run_details(self, dr_id):
        """Query CONS3RT to return details of a deployment run

        :param: (int) deployment run ID
        :return: (dict) of deployment run detailed info
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.retrieve_deployment_run_details')

        # Ensure the dr_id is an int
        if not isinstance(dr_id, int):
            try:
                dr_id = int(dr_id)
            except ValueError:
                msg = 'dr_id arg must be an Integer, found: {t}'.format(t=dr_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        # Query for DR details
        log.info('Attempting to retrieve details for deployment run ID: {i}'.format(i=str(dr_id)))
        try:
            dr_details = self.cons3rt_client.retrieve_deployment_run_details(dr_id=dr_id)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a details of deployment run ID: {i}\n{e}'.format(
                i=str(dr_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        return dr_details

    def list_virtualization_realms_for_cloud(self, cloud_id):
        """Query CONS3RT to return a list of VRs for a specified Cloud ID

        :param cloud_id: (int) Cloud ID
        :return: (list) of Virtualization Realm data
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.list_virtualization_realms_for_cloud')
        log.info('Attempting to list virtualization realms for cloud ID: {i}'.format(i=cloud_id))
        try:
            vrs = self.cons3rt_client.list_virtualization_realms_for_cloud(cloud_id=cloud_id)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for a list of Virtualization Realms for Cloud ID: {c}\n{e}'.format(
                c=cloud_id, e=str(ex))
            raise Cons3rtApiError, msg, trace
        return vrs

    def add_cloud_admin(self, cloud_id, username=None):
        """Adds a users as a Cloud Admin

        :param username: (str) Username
        :param cloud_id: (int) Cloud ID
        :return: None
        :raises: Cons3rtApiError, ValueError
        """
        log = logging.getLogger(self.cls_logger + '.add_cloud_admin')
        if username is None:
            username = self.user.username
        # Ensure the cloud_id is an int
        if not isinstance(cloud_id, int):
            try:
                cloud_id = int(cloud_id)
            except ValueError:
                msg = 'The cloud_id arg must be an int'
                raise Cons3rtApiError(msg)
        try:
            self.cons3rt_client.add_cloud_admin(cloud_id=cloud_id, username=self.user.username)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to add Cloud Admin {u} to Cloud: {c}\n{e}'.format(u=username, c=cloud_id, e=str(ex))
            raise Cons3rtApiError, msg, trace
        else:
            log.info('Added Cloud Admin {u} to Cloud: {c}'.format(u=username, c=cloud_id))

    def delete_asset(self, asset_type, asset_id):
        """Deletes the asset based on a provided asset type

        :param asset_type: (str) asset type
        :param asset_id: (int) asset ID
        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.delete_asset')

        # Ensure the asset_id is an int
        if not isinstance(asset_id, int):
            try:
                asset_id = int(asset_id)
            except ValueError:
                msg = 'asset_id arg must be an Integer, found: {t}'.format(t=asset_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        #  Ensure the asset_zip_file arg is a string
        if not isinstance(asset_type, basestring):
            msg = 'The asset_type arg must be a string, found {t}'.format(t=asset_type.__class__.__name__)
            raise Cons3rtApiError(msg)

        # Determine the target based on asset_type
        target = self.get_asset_type(asset_type=asset_type)
        if target == '':
            raise Cons3rtApiError('Unable to determine the target from provided asset_type: {t}'.format(t=asset_type))

        # Ensure the target is valid
        valid_targets = ['scenarios', 'deployments', 'systems', 'software', 'clouds', 'teams', 'projects']
        if target not in valid_targets:
            msg = 'Provided asset_type does not match a valid asset type that can be deleted.  Valid asset types ' \
                  'are: {t}'.format(t=','.join(valid_targets))
            raise Cons3rtApiError(msg)

        # Attempt to delete the target
        try:
            self.cons3rt_client.delete_asset(asset_id=asset_id, asset_type=target)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to delete {t} with asset ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, i=str(asset_id), t=target, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully deleted {t} asset ID: {i}'.format(i=str(asset_id), t=target))

    def update_asset_content(self, asset_id, asset_zip_file):
        """Updates the asset content for the provided asset_id using the asset_zip_file

        :param asset_id: (int) ID of the asset to update
        :param asset_zip_file: (str) path to the asset zip file
        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.update_asset_content')

        # Ensure the asset_id is an int
        if not isinstance(asset_id, int):
            try:
                asset_id = int(asset_id)
            except ValueError:
                msg = 'asset_id arg must be an Integer'
                raise ValueError(msg)

        #  Ensure the asset_zip_file arg is a string
        if not isinstance(asset_zip_file, basestring):
            msg = 'The json_file arg must be a string'
            raise ValueError(msg)

        # Ensure the asset_zip_file file exists
        if not os.path.isfile(asset_zip_file):
            msg = 'Asset zip file file not found: {f}'.format(f=asset_zip_file)
            raise OSError(msg)

        # Attempt to update the asset ID
        try:
            self.cons3rt_client.update_asset_content(asset_id=asset_id, asset_zip_file=asset_zip_file)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to update asset ID {i} using asset zip file: {f}\n{e}'.format(
                n=ex.__class__.__name__, i=str(asset_id), f=asset_zip_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully updated Asset ID: {i}'.format(i=str(asset_id)))

    def update_asset_state(self, asset_type, asset_id, state):
        """Updates the asset state

        :param asset_type: (str) asset type (scenario, deployment, system, etc)
        :param asset_id: (int) asset ID to update
        :param state: (str) desired state
        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.update_asset_state')

        # Ensure the asset_id is an int
        if not isinstance(asset_id, int):
            try:
                asset_id = int(asset_id)
            except ValueError:
                msg = 'asset_id arg must be an Integer'
                raise Cons3rtApiError(msg)

        #  Ensure the asset_zip_file arg is a string
        if not isinstance(asset_type, basestring):
            msg = 'The asset_type arg must be a string, found {t}'.format(t=asset_type.__class__.__name__)
            raise Cons3rtApiError(msg)

        #  Ensure the asset_zip_file arg is a string
        if not isinstance(state, basestring):
            msg = 'The state arg must be a string, found {t}'.format(t=state.__class__.__name__)
            raise Cons3rtApiError(msg)

        # Determine the target based on asset_type
        target = self.get_asset_type(asset_type=asset_type)
        if target == '':
            raise Cons3rtApiError('Unable to determine the target from provided asset_type: {t}'.format(t=asset_type))

        # Ensure state is valid
        valid_states = ['DEVELOPMENT', 'PUBLISHED', 'CERTIFIED', 'DEPRECATED', 'OFFLINE']
        state = state.upper().strip()
        if state not in valid_states:
            raise Cons3rtApiError('Provided state is not valid: {s}, must be one of: {v}'.format(
                s=state, v=valid_states))

        # Attempt to update the asset ID
        try:
            self.cons3rt_client.update_asset_state(asset_id=asset_id, state=state, asset_type=target)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to update the state for asset ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, i=str(asset_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully updated state for Asset ID {i} to: {s}'.format(i=str(asset_id), s=state))

    def update_asset_visibility(self, asset_type, asset_id, visibility):
        """Updates the asset visibilty

        :param asset_type: (str) asset type (scenario, deployment, system, etc)
        :param asset_id: (int) asset ID to update
        :param visibility: (str) desired asset visibilty
        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.update_asset_visibility')

        # Ensure the asset_id is an int
        if not isinstance(asset_id, int):
            try:
                asset_id = int(asset_id)
            except ValueError:
                msg = 'asset_id arg must be an Integer'
                raise Cons3rtApiError(msg)

        #  Ensure the asset_zip_file arg is a string
        if not isinstance(asset_type, basestring):
            msg = 'The asset_type arg must be a string, found {t}'.format(t=asset_type.__class__.__name__)
            raise Cons3rtApiError(msg)

        #  Ensure the asset_zip_file arg is a string
        if not isinstance(visibility, basestring):
            msg = 'The visibility arg must be a string, found {t}'.format(t=visibility.__class__.__name__)
            raise Cons3rtApiError(msg)

        # Determine the target based on asset_type
        target = self.get_asset_type(asset_type=asset_type)
        if target == '':
            raise Cons3rtApiError('Unable to determine the target from provided asset_type: {t}'.format(t=asset_type))

        # Valid values for visibility
        valid_visibility = ['OWNER', 'OWNING_PROJECT', 'TRUSTED_PROJECTS', 'COMMUNITY']

        # Ensure visibility is cvalid
        visibility = visibility.upper().strip()
        if visibility not in valid_visibility:
            raise Cons3rtApiError('Provided visibility is not valid: {s}, must be one of: {v}'.format(
                s=visibility, v=valid_visibility))

        # Attempt to update the asset ID
        try:
            self.cons3rt_client.update_asset_visibility(asset_id=asset_id, visibility=visibility, asset_type=target)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to update the visibility for asset ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, i=str(asset_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully updated visibility for Asset ID {i} to: {s}'.format(i=str(asset_id), s=visibility))

    def import_asset(self, asset_zip_file):
        """

        :param asset_zip_file:
        :return:
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.import_asset')

        #  Ensure the asset_zip_file arg is a string
        if not isinstance(asset_zip_file, basestring):
            msg = 'The json_file arg must be a string'
            raise ValueError(msg)

        # Ensure the asset_zip_file file exists
        if not os.path.isfile(asset_zip_file):
            msg = 'Asset zip file file not found: {f}'.format(f=asset_zip_file)
            raise OSError(msg)

        # Attempt to update the asset ID
        try:
            self.cons3rt_client.import_asset(asset_zip_file=asset_zip_file)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to import asset using asset zip file: {f}\n{e}'.format(
                n=ex.__class__.__name__, f=asset_zip_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully imported asset from file: {f}'.format(f=asset_zip_file))

    def enable_remote_access(self, virtualization_realm_id, size=None):
        """Enables Remote Access for a specific virtualization realm, and uses SMALL
        as the default size if none is provided.

        :param virtualization_realm_id: (int) ID of the virtualization
        :param size: (str) small, medium, or large
        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.enable_remote_access')

        # Ensure the virtualization_realm_id is an int
        if not isinstance(virtualization_realm_id, int):
            try:
                virtualization_realm_id = int(virtualization_realm_id)
            except ValueError:
                raise ValueError('virtualization_realm_id arg must be an Integer')

        # Use small as the default size
        if size is None:
            size = 'SMALL'

        # Ensure size is a string
        if not isinstance(size, basestring):
            raise ValueError('The size arg must be a string')

        # Acceptable sizes
        size_options = ['SMALL', 'MEDIUM', 'LARGE']
        size = size.upper()
        if size not in size_options:
            raise ValueError('The size arg must be set to SMALL, MEDIUM, or LARGE')

        # Attempt to enable remote access
        log.info('Attempting to enable remote access in virtualization realm ID {i} with size: {s}'.format(
            i=virtualization_realm_id, s=size))
        try:
            self.cons3rt_client.enable_remote_access(virtualization_realm_id=virtualization_realm_id, size=size)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem enabling remote access in virtualization realm ID: {i} with size: ' \
                  '{s}\n{e}'.format(n=ex.__class__.__name__, i=virtualization_realm_id, s=size, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully enabled remote access in virtualization realm: {i}, with size: {s}'.format(
            i=virtualization_realm_id, s=size))

    def retrieve_all_users(self):
        """Retrieve all users from the CONS3RT site

        :return: (list) containing all site users
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.query_all_users')
        log.info('Attempting to query CONS3RT to retrieve all users...')
        try:
            users = self.cons3rt_client.retrieve_all_users()
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem querying for all users\n{e}'.format(n=ex.__class__.__name__, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully enabled retrieved all site users')
        return users

    def create_user_from_json(self, json_file):
        """Creates a single CONS3RT user using data from a JSON file

        :param json_file: (str) path to JSON file
        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.create_user_from_json')
        log.info('Attempting to query CONS3RT to create a user from JSON file...')

        # Ensure the json_file arg is a string
        if not isinstance(json_file, basestring):
            msg = 'The json_file arg must be a string'
            raise ValueError(msg)

        # Ensure the JSON file exists
        if not os.path.isfile(json_file):
            msg = 'JSON file not found: {f}'.format(f=json_file)
            raise OSError(msg)

        # Attempt to create the team
        try:
            self.cons3rt_client.create_user(user_file=json_file)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to create a User using JSON file: {f}\n{e}'.format(
                n=ex.__class__.__name__, f=json_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully created User from file: {f}'.format(f=json_file))

    def add_user_to_project(self, username, project_id):
        """Add the username to the specified project ID

        :param username: (str) CONS3RT username to add to the project
        :param project_id: (int) ID of the project
        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.add_user_to_project')

        # Ensure the username arg is a string
        if not isinstance(username, basestring):
            msg = 'The username arg must be a string'
            raise Cons3rtApiError(msg)

        # Ensure the project_id is an int
        if not isinstance(project_id, int):
            try:
                project_id = int(project_id)
            except ValueError:
                msg = 'project_id arg must be an Integer, found: {t}'.format(t=project_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        # Attempt to add the user to the project
        try:
            self.cons3rt_client.add_user_to_project(username=username, project_id=project_id)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to add username {u} to project ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, u=username, i=str(project_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully added username {u} to project ID: {i}'.format(i=str(project_id), u=username))

    def create_scenario_from_json(self, json_file):
        """Creates a scenario using data from a JSON file

        :param json_file: (str) path to JSON file
        :return: (int) Scenario ID
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.create_scenario_from_json')
        log.info('Attempting to query CONS3RT to create a scenario from JSON file...')

        # Ensure the json_file arg is a string
        if not isinstance(json_file, basestring):
            msg = 'The json_file arg must be a string'
            raise ValueError(msg)

        # Ensure the JSON file exists
        if not os.path.isfile(json_file):
            msg = 'JSON file not found: {f}'.format(f=json_file)
            raise OSError(msg)

        # Attempt to create the team
        try:
            scenario_id = self.cons3rt_client.create_scenario(scenario_file=json_file)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to create a scenario using JSON file: {f}\n{e}'.format(
                n=ex.__class__.__name__, f=json_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully created scenario ID {i} from file: {f}'.format(i=scenario_id, f=json_file))
        return scenario_id

    def create_deployment_from_json(self, json_file):
        """Creates a deployment using data from a JSON file

        :param json_file: (str) path to JSON file
        :return: (int) Deployment ID
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.create_deployment_from_json')
        log.info('Attempting to query CONS3RT to create a deployment from JSON file...')

        # Ensure the json_file arg is a string
        if not isinstance(json_file, basestring):
            msg = 'The json_file arg must be a string, found: {t}'.format(t=json_file.__class__.__name__)
            raise Cons3rtApiError(msg)

        # Ensure the JSON file exists
        if not os.path.isfile(json_file):
            msg = 'JSON file not found: {f}'.format(f=json_file)
            raise Cons3rtApiError(msg)

        # Attempt to create the team
        try:
            deployment_id = self.cons3rt_client.create_deployment(deployment_file=json_file)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to create a deployment using JSON file: {f}\n{e}'.format(
                n=ex.__class__.__name__, f=json_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully created deployment ID {i} from file: {f}'.format(i=deployment_id, f=json_file))
        return deployment_id

    def release_deployment_run(self, dr_id):
        """Release a deployment run by ID

        :param: dr_id: (int) deployment run ID
        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.release_deployment_run')

        # Ensure the dr_id is an int
        if not isinstance(dr_id, int):
            try:
                dr_id = int(dr_id)
            except ValueError:
                msg = 'dr_id arg must be an Integer, found: {t}'.format(t=dr_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        # Attempt to release the DR
        log.debug('Attempting to release deployment run ID: {i}'.format(i=str(dr_id)))
        try:
            result = self.cons3rt_client.release_deployment_run(dr_id=dr_id)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to release deployment run ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, i=str(dr_id), e=str(ex))
            raise Cons3rtApiError, msg, trace

        if result:
            log.info('Successfully released deployment run ID: {i}'.format(i=str(dr_id)))
        else:
            raise Cons3rtApiError('Unable to release deployment run ID: {i}'.format(i=str(dr_id)))

    def launch_deployment_run_from_json(self, deployment_id, json_file):
        """Launches a deployment run using options provided in a JSON file

        :param deployment_id: (int) ID of the deployment to launch
        :param json_file: (str) path to JSON file containing data for deployment run options
        :return: (int) deployment run ID
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.launch_deployment_run_from_json')

        # Ensure the deployment_id is an int
        if not isinstance(deployment_id, int):
            try:
                deployment_id = int(deployment_id)
            except ValueError:
                raise Cons3rtApiError('deployment_id arg must be an Integer, found: {t}'.format(
                    t=deployment_id.__class__.__name__))

        # Ensure the json_file arg is a string
        if not isinstance(json_file, basestring):
            raise Cons3rtApiError('The json_file arg must be a string')

        # Ensure the JSON file exists
        if not os.path.isfile(json_file):
            raise Cons3rtApiError('JSON file not found: {f}'.format(f=json_file))

        # Read JSON
        try:
            with open(json_file, 'r') as f:
                json_content = f.read()
        except (OSError, IOError):
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to read contents of file: {f}\n{e}'.format(
                n=ex.__class__.__name__, f=json_file, e=str(ex))
            raise Cons3rtApiError, msg, trace

        # Attempt to run the deployment
        try:
            dr_id = self.cons3rt_client.run_deployment(deployment_id=deployment_id, json_content=json_content)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to launch deployment run: {f}\n{e}'.format(
                n=ex.__class__.__name__, f=json_file, e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully launched deployment run ID {i} from file: {f}'.format(i=dr_id, f=json_file))
        return dr_id

    def run_deployment(self, deployment_id, run_options):
        """Launches a deployment using provided data

        :param deployment_id: (int) ID of the deployment to launch
        :param run_options: (dict) data for deployment run options
        :return (int) deployment run ID
        :raises Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.launch_deployment_run')

        # Ensure the deployment_id is an int
        if not isinstance(deployment_id, int):
            try:
                deployment_id = int(deployment_id)
            except ValueError:
                raise Cons3rtApiError('deployment_id arg must be an Integer, found: {t}'.format(
                    t=deployment_id.__class__.__name__))

        # Ensure the run_options is a dict
        if not isinstance(run_options, dict):
            raise Cons3rtApiError('run_options arg must be a dict, found: {t}'.format(t=run_options.__class__.__name__))

        # Create JSON content
        try:
            json_content = json.dumps(run_options)
        except SyntaxError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem convertify data to JSON: {d}\n{e}'.format(
                n=ex.__class__.__name__, d=str(run_options), e=str(ex))
            raise Cons3rtApiError, msg, trace

        # Attempt to run the deployment
        try:
            dr_id = self.cons3rt_client.run_deployment(deployment_id=deployment_id, json_content=json_content)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to launch deployment run ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, i=str(deployment_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        log.info('Successfully launched deployment ID {d} as deployment run ID: {i}'.format(
            i=str(dr_id), d=str(deployment_id)))

    def delete_inactive_runs_in_virtualization_realm(self, vr_id):
        """Deletes all inactive runs in a virtualization realm

        :param vr_id: (int) virtualization realm ID
        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.delete_inactive_runs_in_virtualization_realm')

        # Ensure the vr_id is an int
        if not isinstance(vr_id, int):
            try:
                vr_id = int(vr_id)
            except ValueError:
                msg = 'vr_id arg must be an Integer, found: {t}'.format(t=vr_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        # List runs in the virtualization realm
        try:
            drs = self.list_deployment_runs_in_virtualization_realm(vr_id=vr_id, search_type='SEARCH_INACTIVE')
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            msg = 'Cons3rtApiError: There was a problem listing inactive deployment runs in VR ID: {i}\n{e}'.format(
                i=str(vr_id), e=str(ex))
            raise Cons3rtApiError, msg, trace

        # Delete each inactive run
        log.debug('Found inactive runs in VR ID {i}:\n{r}'.format(i=str(vr_id), r=str(drs)))
        log.info('Attempting to delete inactive runs from VR ID: {i}'.format(i=str(vr_id)))
        for dr in drs:
            try:
                dr_id = dr['id']
            except KeyError:
                log.warn('Unable to determine the run ID from run: {r}'.format(r=str(dr)))
                continue
            try:
                self.delete_inactive_run(dr_id=dr_id)
            except Cons3rtApiError:
                _, ex, trace = sys.exc_info()
                log.warn('Cons3rtApiError: Unable to delete run ID: {i}\n{e}'.format(i=str(dr_id), e=str(ex)))
                continue
        log.info('Completed deleting inactive DRs in VR ID: {i}'.format(i=str(vr_id)))

    def release_active_runs_in_virtualization_realm(self, vr_id):
        """Releases all active runs in a virtualization realm

        :param vr_id: (int) virtualization realm ID
        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.release_active_runs_in_virtualization_realm')

        # Ensure the vr_id is an int
        if not isinstance(vr_id, int):
            try:
                vr_id = int(vr_id)
            except ValueError:
                msg = 'vr_id arg must be an Integer, found: {t}'.format(t=vr_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        # List active runs in the virtualization realm
        try:
            drs = self.list_deployment_runs_in_virtualization_realm(vr_id=vr_id, search_type='SEARCH_ACTIVE')
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            msg = 'Cons3rtApiError: There was a problem listing active deployment runs in VR ID: {i}\n{e}'.format(
                i=str(vr_id), e=str(ex))
            raise Cons3rtApiError, msg, trace

        # Release or cancel each active run
        log.debug('Found active runs in VR ID {i}:\n{r}'.format(i=str(vr_id), r=str(drs)))
        log.info('Attempting to release or cancel active runs from VR ID: {i}'.format(i=str(vr_id)))
        for dr in drs:
            try:
                dr_id = dr['id']
            except KeyError:
                log.warn('Unable to determine the run ID from run: {r}'.format(r=str(dr)))
                continue
            try:
                self.release_deployment_run(dr_id=dr_id)
            except Cons3rtApiError:
                _, ex, trace = sys.exc_info()
                log.warn('Cons3rtApiError: Unable to release or cancel run ID: {i}\n{e}'.format(
                    i=str(dr_id), e=str(ex)))
                continue
        log.info('Completed releasing or cancelling active DRs in VR ID: {i}'.format(i=str(vr_id)))

    def delete_inactive_run(self, dr_id):
        """Deletes an inactive run

        :param dr_id: (int) deployment run ID
        :return: None
        :raises: Cons3rtApiError
        """
        log = logging.getLogger(self.cls_logger + '.delete_inactive_run')

        # Ensure the vr_id is an int
        if not isinstance(dr_id, int):
            try:
                dr_id = int(dr_id)
            except ValueError:
                msg = 'dr_id arg must be an Integer, found: {t}'.format(t=dr_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        log.debug('Attempting to delete run ID: {i}'.format(i=str(dr_id)))
        try:
            self.cons3rt_client.delete_deployment_run(dr_id=dr_id)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Cons3rtClientError: There was a problem deleting run ID: {i}\n{e}'.format(i=str(dr_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        else:
            log.info('Successfully deleted run ID: {i}'.format(i=str(dr_id)))

    def get_virtualization_realm_details(self, vr_id):
        """Queries for details of the virtualization realm ID

        :param vr_id: (int) VR ID
        :return: (dict) VR details
        """
        log = logging.getLogger(self.cls_logger + '.get_virtualization_realm_details')

        # Ensure the vr_id is an int
        if not isinstance(vr_id, int):
            try:
                vr_id = int(vr_id)
            except ValueError:
                msg = 'vr_id arg must be an Integer, found: {t}'.format(t=vr_id.__class__.__name__)
                raise Cons3rtApiError(msg)

        # Query for VR details
        log.debug('Attempting query virtualization realm ID {i}'.format(i=str(vr_id)))
        try:
            vr_details = self.cons3rt_client.get_virtualization_realm_details(vr_id=vr_id)
        except Cons3rtClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query CONS3RT for details on virtualization realm: {i}\n{e}'.format(
                i=str(vr_id), e=str(ex))
            raise Cons3rtApiError, msg, trace
        return vr_details
