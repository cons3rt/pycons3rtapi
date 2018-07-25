#!/usr/bin/env python

import logging
import sys

from requests_toolbelt import MultipartEncoder

import requests
from requests.exceptions import RequestException, SSLError

from pycons3rt.logify import Logify

from pycons3rtlibs import Cons3rtClientError

# Set up logger name for this module
mod_logger = Logify.get_name() + '.pycons3rtapi.httpclient'


class Client:

    def __init__(self, base):
        self.base = base

        if not self.base.endswith('/'):
            self.base = self.base + '/'

        self.cls_logger = mod_logger + '.Client'
        # Remove once cert handling is more developed
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecurePlatformWarning)
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.SNIMissingWarning)

    @staticmethod
    def get_auth_headers(rest_user):
        """Returns the auth portion of the headers including:
        * token
        * username (only for non-cert auth sites)

        :param rest_user: (RestUser) user info
        :return: (dict) headers
        """
        if rest_user is None:
            raise Cons3rtClientError('rest_user provided was None')

        if rest_user.cert_file_path:
            return {
                'token': rest_user.token,
                'Accept': 'application/json'
            }
        else:
            return {
                'username': rest_user.username,
                'token': rest_user.token,
                'Accept': 'application/json'
            }

    @staticmethod
    def validate_target(target):
        """ Validates that a target was provided and is a string
        :param target: the target url for the http request
        :return: void
        :raises: Cons3rtClientError
        """

        if target is None or not isinstance(target, basestring):
            raise Cons3rtClientError('Invalid target arg provided')

    def http_get(self, rest_user, target):
        """Runs an HTTP GET request to the CONS3RT ReST API

        :param rest_user: (RestUser) user info
        :param target: (str) URL
        :return: http response
        """
        log = logging.getLogger(self.cls_logger + '.http_get')

        self.validate_target(target)

        # Set the URL
        url = self.base + target
        log.debug('Querying http GET with URL: {u}'.format(u=url))

        # Determine the headers
        headers = self.get_auth_headers(rest_user=rest_user)

        try:
            response = requests.get(url, headers=headers, verify=False, cert=rest_user.cert_file_path)
        except RequestException as ex:
            raise Cons3rtClientError(str(ex))
        except SSLError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was an SSL error making an HTTP GET to URL: {u}\n{e}'.format(
                n=ex.__class__.__name__, u=url, e=str(ex))
            raise Cons3rtClientError, msg, trace
        return response

    def http_delete(self, rest_user, target, content=None, keep_alive=False):
        self.validate_target(target)

        url = self.base + target

        headers = self.get_auth_headers(rest_user=rest_user)
        headers['Content-Type'] = 'application/json'

        if keep_alive:
            headers['Connection'] = 'Keep-Alive'

        try:
            if content is None:
                response = requests.delete(url, headers=headers, verify=False, cert=rest_user.cert_file_path)
            else:
                response = requests.delete(
                    url, headers=headers, data=content, verify=False, cert=rest_user.cert_file_path)
        except RequestException as ex:
            raise Cons3rtClientError(str(ex))
        except SSLError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was an SSL error making an HTTP GET to URL: {u}\n{e}'.format(
                n=ex.__class__.__name__, u=url, e=str(ex))
            raise Cons3rtClientError, msg, trace
        return response

    def http_post(self, rest_user, target, content_file=None, content_type='application/json'):
        """Makes an HTTP Post to the requested URL

        :param rest_user: (RestUser) user info
        :param target: (str) ReST API target URL
        :param content_file: (str) path to the content file
        :param content_type: (str) Content-Type, default is application/json
        :return: (str) HTTP Response or None
        :raises: Cons3rtClientError
        """
        self.validate_target(target)

        url = self.base + target

        headers = self.get_auth_headers(rest_user=rest_user)
        headers['Content-Type'] = '{t}'.format(t=content_type)

        response = None

        if content_file is None:
            try:
                response = requests.post(url, headers=headers, verify=False, cert=rest_user.cert_file_path)
            except SSLError:
                _, ex, trace = sys.exc_info()
                msg = '{n}: There was an SSL error making an HTTP POST to URL: {u}\n{e}'.format(
                    n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except requests.ConnectionError:
                _, ex, trace = sys.exc_info()
                msg = '{n}: Connection error encountered making HTTP Post:\n{e}'.format(
                        n=ex.__class__.__name__, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except requests.Timeout:
                _, ex, trace = sys.exc_info()
                msg = '{n}: HTTP post to URL {u} timed out\n{e}'.format(n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except RequestException:
                _, ex, trace = sys.exc_info()
                msg = '{n}: There was a problem making an HTTP post to URL: {u}\n{e}'.format(
                        n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except Exception:
                _, ex, trace = sys.exc_info()
                msg = '{n}: Generic error caught making an HTTP post to URL: {u}\n{e}'.format(
                        n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
        else:
            with open(content_file, 'r') as f:
                x = f.read()
                try:
                    response = requests.post(url, headers=headers, data=x, verify=False, cert=rest_user.cert_file_path)
                except SSLError:
                    _, ex, trace = sys.exc_info()
                    msg = '{n}: There was an SSL error making an HTTP POST to URL: {u}\n{e}'.format(
                        n=ex.__class__.__name__, u=url, e=str(ex))
                    raise Cons3rtClientError, msg, trace
                except requests.ConnectionError:
                    _, ex, trace = sys.exc_info()
                    msg = '{n}: Connection error encountered making HTTP Post:\n{e}'.format(
                        n=ex.__class__.__name__, e=str(ex))
                    raise Cons3rtClientError, msg, trace
                except requests.Timeout:
                    _, ex, trace = sys.exc_info()
                    msg = '{n}: HTTP post to URL {u} timed out\n{e}'.format(n=ex.__class__.__name__, u=url, e=str(ex))
                    raise Cons3rtClientError, msg, trace
                except RequestException:
                    _, ex, trace = sys.exc_info()
                    msg = '{n}: There was a problem making an HTTP post to URL: {u}\n{e}'.format(
                        n=ex.__class__.__name__, u=url, e=str(ex))
                    raise Cons3rtClientError, msg, trace
                except Exception:
                    _, ex, trace = sys.exc_info()
                    msg = '{n}: Generic error caught making an HTTP post to URL: {u}\n{e}'.format(
                        n=ex.__class__.__name__, u=url, e=str(ex))
                    raise Cons3rtClientError, msg, trace
        return response

    def http_put(self, rest_user, target, content_data=None, content_file=None, content_type='application/json'):
        """Makes an HTTP Post to the requested URL

        :param rest_user: (RestUser) user info
        :param target: (str) ReST API target URL
        :param content_data: (str) body data
        :param content_file: (str) path to the content file containing body data
        :param content_type: (str) Content-Type, default is application/json
        :return: (str) HTTP Response or None
        :raises: Cons3rtClientError
        """
        self.validate_target(target)
        url = self.base + target
        headers = self.get_auth_headers(rest_user=rest_user)
        content = None

        # Read data from the file if provided
        if content_file:
            try:
                with open(content_file, 'r') as f:
                    content = f.read()
            except (OSError, IOError):
                _, ex, trace = sys.exc_info()
                msg = '{n}: Unable to read contents of file: {f}\n{e}'.format(
                    n=ex.__class__.__name__, f=content_file, e=str(ex))
                raise Cons3rtClientError, msg, trace
        # Otherwise use data provided as content
        elif content_data:
            content = content_data

        # Add content type if content was provided
        if content:
            headers['Content-Type'] = '{t}'.format(t=content_type)

        # Make the put request
        try:
            response = requests.put(url, headers=headers, data=content, verify=False, cert=rest_user.cert_file_path)
        except SSLError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was an SSL error making an HTTP PUT to URL: {u}\n{e}'.format(
                n=ex.__class__.__name__, u=url, e=str(ex))
            raise Cons3rtClientError, msg, trace
        except requests.ConnectionError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Connection error encountered making HTTP Put:\n{e}'.format(
                n=ex.__class__.__name__, e=str(ex))
            raise Cons3rtClientError, msg, trace
        except requests.Timeout:
            _, ex, trace = sys.exc_info()
            msg = '{n}: HTTP put to URL {u} timed out\n{e}'.format(n=ex.__class__.__name__, u=url, e=str(ex))
            raise Cons3rtClientError, msg, trace
        except RequestException:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem making an HTTP put to URL: {u}\n{e}'.format(
                n=ex.__class__.__name__, u=url, e=str(ex))
            raise Cons3rtClientError, msg, trace
        except Exception:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Generic error caught making an HTTP put to URL: {u}\n{e}'.format(
                n=ex.__class__.__name__, u=url, e=str(ex))
            raise Cons3rtClientError, msg, trace
        return response

    def http_put_multipart(self, rest_user, target, content_file):
        """Makes an HTTP Put request

        :param rest_user: (RestUser) user info
        :param target: (str) ReST API target URL
        :param content_file: (str) path to the content file
        :return: (str) HTTP Response or None
        :raises: Cons3rtClientError
        """
        log = logging.getLogger(self.cls_logger + '.http_put_multipart')
        self.validate_target(target)

        url = self.base + target

        if not content_file:
            raise Cons3rtClientError('Invalid content_file arg provided')

        headers = self.get_auth_headers(rest_user=rest_user)
        headers['Accept'] = 'application/json'
        headers['Connection'] = 'Keep-Alive'

        log.info('Making HTTP request to URL [{u}], with headers: {h}'.format(u=url, h=headers))

        response = None
        with open(content_file, 'r') as f:
            try:
                form = MultipartEncoder({
                    "file": ("asset.zip", f, "application/octet-stream"),
                    "filename": "asset.zip"
                })

                headers["Content-Type"] = form.content_type

                response = requests.put(url, headers=headers, data=form, verify=False, cert=rest_user.cert_file_path)
            except SSLError:
                _, ex, trace = sys.exc_info()
                msg = '{n}: There was an SSL error making an HTTP PUT to URL: {u}\n{e}'.format(
                    n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except requests.ConnectionError:
                _, ex, trace = sys.exc_info()
                msg = '{n}: Connection error encountered making HTTP PUT:\n{e}'.format(
                        n=ex.__class__.__name__, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except requests.Timeout:
                _, ex, trace = sys.exc_info()
                msg = '{n}: HTTP PUT to URL {u} timed out\n{e}'.format(n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except RequestException:
                _, ex, trace = sys.exc_info()
                msg = '{n}: There was a problem making an HTTP PUT to URL: {u}\n{e}'.format(
                        n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
        return response

    def http_post_multipart(self, rest_user, target, content_file):
        """Makes an HTTP Put request

        :param rest_user: (RestUser) user info
        :param target: (str) ReST API target URL
        :param content_file: (str) path to the content file
        :return: (str) HTTP Response or None
        :raises: Cons3rtClientError
        """
        log = logging.getLogger(self.cls_logger + '.http_put_multipart')
        self.validate_target(target)

        url = self.base + target

        if not content_file:
            raise Cons3rtClientError('Invalid content_file arg provided')

        headers = self.get_auth_headers(rest_user=rest_user)
        headers['Accept'] = 'application/json'
        headers['Connection'] = 'Keep-Alive'

        log.info('Making HTTP request to URL [{u}], with headers: {h}'.format(u=url, h=headers))

        response = None
        with open(content_file, 'r') as f:
            try:
                form = MultipartEncoder({
                    "file": ("asset.zip", f, "application/octet-stream"),
                    "filename": "asset.zip"
                })

                headers["Content-Type"] = form.content_type

                response = requests.post(url, headers=headers, data=form, verify=False, cert=rest_user.cert_file_path)
            except SSLError:
                _, ex, trace = sys.exc_info()
                msg = '{n}: There was an SSL error making an HTTP POST to URL: {u}\n{e}'.format(
                    n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except requests.ConnectionError:
                _, ex, trace = sys.exc_info()
                msg = '{n}: Connection error encountered making HTTP POST multipart:\n{e}'.format(
                    n=ex.__class__.__name__, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except requests.Timeout:
                _, ex, trace = sys.exc_info()
                msg = '{n}: HTTP POST to URL {u} timed out\n{e}'.format(n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
            except RequestException:
                _, ex, trace = sys.exc_info()
                msg = '{n}: There was a problem making an HTTP POST multipart to URL: {u}\n{e}'.format(
                    n=ex.__class__.__name__, u=url, e=str(ex))
                raise Cons3rtClientError, msg, trace
        return response

    def parse_response(self, response):
        log = logging.getLogger(self.cls_logger + '.parse_response')
        log.debug('Parsing response with content: {s}'.format(s=response.content))
        if response.status_code == requests.codes.ok:
            log.debug('Received an OK HTTP Response Code!')
            return response.content
        elif response.status_code == 202:
            log.debug('Received an ACCEPTED HTTP Response Code!')
            return response.content
        else:
            msg = 'Received HTTP code [{n}] with content:\n{c}'.format(n=str(response.status_code), c=response.content)
            log.info(msg)
            raise Cons3rtClientError(msg)
