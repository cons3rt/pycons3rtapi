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
    def err(msg):
        print('ERROR: {m}'.format(m=msg))


class CloudspaceCli(Cons3rtCli):

    def __init__(self, args):
        Cons3rtCli.__init__(self, args)

    def process_args(self):
        if not self.validate_args():
            return False
        if len(self.ids) < 1:
            self.err('No Cloudspace ID(s) provided, use --id=123 or --ids=3,4,5')
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
