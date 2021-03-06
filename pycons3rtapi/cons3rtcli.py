#!/usr/bin/env python

import sys

from cons3rtapi import Cons3rtApi
from pycons3rtlibs import Cons3rtApiError


class Cons3rtCliError(Exception):
    pass


class Cons3rtCli(object):

    def __init__(self, args):
        self.args = args
        self.ids = []
        try:
            self.c5t = Cons3rtApi()
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            self.err('Missing or incomplete authentication information, run [cons3rt config] to fix\n{e}'.format(
                e=str(ex)))

    def validate_args(self):
        try:
            self.validate_ids()
            self.validate_id()
        except Cons3rtCliError:
            return False
        return True

    def validate_id(self):
        if self.args.id:
            try:
                self.ids.append(int(self.args.id))
            except ValueError:
                msg = 'Cloudspace ID provided is not an int: {i}'.format(i=str(self.args.id))
                self.err(msg)
                raise Cons3rtCliError(msg)

    def validate_ids(self):
        if self.args.ids:
            if ',' not in self.args.ids:
                msg = 'IDs provided should be comma-separated: --ids=1,2,3'
                self.err(msg)
                raise Cons3rtCliError(msg)
            for an_id in self.args.ids.split(','):
                try:
                    an_id = int(an_id)
                except ValueError:
                    msg = 'An ID provided is not an int: {i}'.format(i=str(an_id))
                    self.err(msg)
                    raise Cons3rtCliError(msg)
                self.ids.append(an_id)

    @staticmethod
    def dict_id_comparator(element):
        if not isinstance(element, dict):
            return 0
        if 'id' in element:
            try:
                element_id = int(element['id'])
            except ValueError:
                return 0
            else:
                return element_id
        else:
            return 0

    @staticmethod
    def sort_by_id(unsorted_list):
        return sorted(unsorted_list, key=Cons3rtCli.dict_id_comparator)

    @staticmethod
    def err(msg):
        print('ERROR: {m}'.format(m=msg))

    @staticmethod
    def print_drs(dr_list):
        msg = 'ID\tName\t\t\t\t\t\tStatus\t\tProject\t\tCreator\n'
        for dr_info in dr_list:

            if 'id' in dr_info:
                msg += str(dr_info['id'])
            else:
                msg += '      '
            msg += '\t'
            if 'name' in dr_info:
                msg += dr_info['name']
            else:
                msg += '                '
            msg += '\t\t\t\t\t\t'
            if 'fapStatus' in dr_info:
                msg += dr_info['fapStatus']
            else:
                msg += '              '
            msg += '\t\t'
            if 'project' in dr_info:
                msg += dr_info['project']['name']
            else:
                msg += '                 '
            msg += '\t\t'
            if 'creator' in dr_info:
                msg += dr_info['creator']['username']
            else:
                msg += '         '
            msg += '\n'
        print(msg)

    @staticmethod
    def print_projects(project_list):
        msg = 'ID\tName\n'
        for project in project_list:
            if 'id' in project:
                msg += str(project['id'])
            else:
                msg += '      '
            msg += '\t'
            if 'name' in project:
                msg += project['name']
            else:
                msg += '                '
            msg += '\n'
        print(msg)

    @staticmethod
    def print_clouds(cloud_list):
        msg = 'ID\tName\t\t\t\tType\n'
        for cloud in cloud_list:
            if 'id' in cloud:
                msg += str(cloud['id'])
            else:
                msg += '      '
            msg += '\t'
            if 'name' in cloud:
                msg += cloud['name']
            else:
                msg += '                '
            msg += '\t\t\t'
            if 'cloudType' in cloud:
                msg += cloud['cloudType']
            else:
                msg += '           '
            msg += '\n'
        print(msg)

    @staticmethod
    def print_teams(teams_list):
        msg = 'ID\tName\n'
        for team in teams_list:
            if 'id' in team:
                msg += str(team['id'])
            else:
                msg += '      '
            msg += '\t'
            if 'name' in team:
                msg += team['name']
            else:
                msg += '                '
            msg += '\n'
        print(msg)


class CloudspaceCli(Cons3rtCli):

    def __init__(self, args):
        Cons3rtCli.__init__(self, args)

    def process_args(self):
        if not self.validate_args():
            return False
        if len(self.ids) < 1:
            self.err('No Cloudspace ID(s) provided, use --id=123 or --ids=3,4,5')
            return False
        if self.args.list_active_runs or self.args.list:
            try:
                self.list_active_runs()
            except Cons3rtCliError:
                return False
        if self.args.release_active_runs:
            try:
                self.release_active_runs()
            except Cons3rtCliError:
                return False
        if self.args.delete_inactive_runs:
            try:
                self.delete_inactive_runs()
            except Cons3rtCliError:
                return False
        return True

    def list_active_runs(self):
        for cloudspace_id in self.ids:
            self.list_active_runs_in_cloudspace(cloudspace_id)

    def list_active_runs_in_cloudspace(self, cloudspace_id):
        try:
            drs = self.c5t.list_deployment_runs_in_virtualization_realm(
                vr_id=cloudspace_id,
                search_type='SEARCH_ACTIVE'
            )
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            msg = 'There was a problem deleting inactive runs from cloudspace ID: {i}\n{e}'.format(
                i=str(cloudspace_id), e=str(ex))
            self.err(msg)
            raise Cons3rtCliError, msg, trace
        print('Found {n} active runs in Cloudspace ID: {i}'.format(n=str(len(drs)), i=str(cloudspace_id)))
        if len(drs) > 0:
            self.print_drs(dr_list=drs)

    def delete_inactive_runs(self):
        for cloudspace_id in self.ids:
            self.delete_inactive_runs_from_cloudspace(cloudspace_id)

    def delete_inactive_runs_from_cloudspace(self, cloudspace_id):
        try:
            self.c5t.delete_inactive_runs_in_virtualization_realm(vr_id=cloudspace_id)
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            msg = 'There was a problem deleting inactive runs from cloudspace ID: {i}\n{e}'.format(
                i=str(cloudspace_id), e=str(ex))
            self.err(msg)
            raise Cons3rtCliError, msg, trace

    def release_active_runs(self):
        for cloudspace_id in self.ids:
            self.release_active_runs_from_cloudspace(cloudspace_id)

    def release_active_runs_from_cloudspace(self, cloudspace_id):
        try:
            self.c5t.release_active_runs_in_virtualization_realm(vr_id=cloudspace_id)
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            msg = 'There was a problem releasing active runs from cloudspace ID: {i}\n{e}'.format(
                i=str(cloudspace_id), e=str(ex))
            self.err(msg)
            raise Cons3rtCliError, msg, trace


class ProjectCli(Cons3rtCli):

    def __init__(self, args):
        Cons3rtCli.__init__(self, args)

    def process_args(self):
        if not self.validate_args():
            return False
        if self.args.list:
            try:
                self.list_projects()
            except Cons3rtCliError:
                return False
        return True

    def list_projects(self):
        projects = []
        try:
            projects += self.c5t.list_projects()
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            msg = 'There was a problem listing projects\n{e}'.format(e=str(ex))
            self.err(msg)
            raise Cons3rtCliError, msg, trace
        print('You are a member of {n} projects'.format(n=str(len(projects))))
        if not self.args.my:
            try:
                projects += self.c5t.list_expanded_projects()
            except Cons3rtApiError:
                _, ex, trace = sys.exc_info()
                msg = 'There was a problem listing projects\n{e}'.format(e=str(ex))
                self.err(msg)
                raise Cons3rtCliError, msg, trace
        if len(projects) > 0:
            projects = self.sort_by_id(projects)
            self.print_projects(project_list=projects)
        print('Total number of projects found: {n}'.format(n=str(len(projects))))


class CloudCli(Cons3rtCli):

    def __init__(self, args):
        Cons3rtCli.__init__(self, args)

    def process_args(self):
        if not self.validate_args():
            return False
        if self.args.list:
            try:
                self.list_clouds()
            except Cons3rtCliError:
                return False
        return True

    def list_clouds(self):
        clouds = []
        try:
            clouds += self.c5t.list_clouds()
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            msg = 'There was a problem listing clouds\n{e}'.format(e=str(ex))
            self.err(msg)
            raise Cons3rtCliError, msg, trace
        if len(clouds) > 0:
            clouds = self.sort_by_id(clouds)
            self.print_clouds(cloud_list=clouds)
        print('Total number of clouds found: {n}'.format(n=str(len(clouds))))


class TeamCli(Cons3rtCli):

    def __init__(self, args):
        Cons3rtCli.__init__(self, args)

    def process_args(self):
        if not self.validate_args():
            return False
        if self.args.list:
            try:
                self.list_teams()
            except Cons3rtCliError:
                return False
        return True

    def list_teams(self):
        teams = []
        try:
            teams += self.c5t.list_teams()
        except Cons3rtApiError:
            _, ex, trace = sys.exc_info()
            msg = 'There was a problem listing teams\n{e}'.format(e=str(ex))
            self.err(msg)
            raise Cons3rtCliError, msg, trace
        if len(teams) > 0:
            teams = self.sort_by_id(teams)
            self.print_teams(teams_list=teams)
        print('Total number of clouds teams: {n}'.format(n=str(len(teams))))
