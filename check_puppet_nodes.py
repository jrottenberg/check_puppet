#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""

Contact foreman to check the global health
of the puppet nodes.

If not too many clients are out of sync or in error

Few doctests, run with :
 $ python -m doctest check_puppet_nodes.py -v

"""
__author__ = 'Julien Rottenberg'
__date__ = "September 2012"

__version__ = "1.1"
__credits__ = """Thanks to Foreman - http://theforeman.org/"""

from optparse import OptionParser, OptionGroup
import base64
import urllib2
import json
from urllib2 import HTTPError, URLError
from socket import setdefaulttimeout
import sys


def get_data(url, username, password, timeout):
    """
    Initialize the connection to Foreman
    Fetch data using the api
    """

    request = urllib2.Request(url)
    request.add_header('Content-Type', 'application/json')
    request.add_header('Accept', 'application/json')

    if (username and password):
        b64string = base64.encodestring('%s:%s' % (username, password))
        request.add_header("Authorization", "Basic %s" % b64string)

    try:
        setdefaulttimeout(timeout)
        raw_out = urllib2.urlopen(request).read()
        out = json.loads(raw_out)

    except HTTPError:
        print 'CRITICAL - is %s valid mode ? Check credentials' % url
        sys.exit(2)
    except URLError:
        print 'CRITICAL - Error on %s Double check foreman server name' % url
        sys.exit(2)

    return out


def check_result(params, server):
    """
    From the server response and input parameter
    check if the puppet client report should trigger an alert

    http://theforeman.org/projects/foreman/wiki/API
    """

    mode = params['mode']
    target = len(server)
    msg = '%s servers have the status : %s' % (target, mode)

    if (target >= params['critical']):
        status = 'CRITICAL'
    elif (target >= params['warning']):
        status = 'WARNING'
    else:
        servers = ''
        for item in server:
            servers = '%s %s' % (servers, (item['host']['name']))
        msg = '%s -%s' % (msg,  servers)
        status = 'OK'

    msg = '%s (levels at %s/%s)' % (msg, params['warning'], params['critical'])
    return(status, msg)


def usage():
    """
    Return usage text so it can be used on failed human interactions
    """

    usage_string = """
    usage: %prog [options] -H FOREMAN_HOST -m MODE -w WARNING -c CRITICAL

    Warning and Critical are maximum number of hosts foreman has in that MODE

    Ex :

    check_puppet_nodes.py -H foreman.example.com -m out_of_sync -w 5 -c 10
    will check if less than 5 nodes are out of sync, 10 for a critical

    """
    return usage_string


def controller():
    """
    Parse user input, fail quick if not enough parameters
    """

    description = """A Nagios plugin to check if the puppet nodes are
globally healthy : not too many in errors, not too many out of sync."""

    version = "%prog " + __version__
    parser = OptionParser(description=description, usage=usage(),
                          version=version)
    parser.set_defaults(verbose=False)

    parser.add_option('-H', '--hostname', type='string',
                      help='Foreman hostname')

    parser.add_option('-w', '--warning', type='int', default=5,
                      help='Warning threshold in minutes')

    parser.add_option('-c', '--critical', type='int', default=10,
                      help='Critical threshold in minutes')

    parser.add_option('-m', '--mode', type='choice',
                      choices=['out_of_sync', 'errors', 'active'],
                      help='Mode of check')

    connection = OptionGroup(parser, "Connection Options",
                             "Network / Authentication related options")
    connection.add_option('-u', '--username', type='string',
                          help='Foreman username')
    connection.add_option('-p', '--password', type='string',
                          help='Foreman password')
    connection.add_option('-t', '--timeout', type='int', default=10,
                          help='Connection timeout in seconds')
    connection.add_option('-P', '--port', type='int',
                          help='Foreman port',
                          default=80)
    connection.add_option('--prefix', type='string',
                          help='Foreman prefix, if not installed on /',
                          default='/')
    connection.add_option('-S', '--ssl', action="store_true",
                          default=False,
                          help='If the connection requires ssl')
    parser.add_option_group(connection)

    extra = OptionGroup(parser, "Extra Options")
    extra.add_option('-v', action='store_true', dest='verbose',
                     default=False,
                     help='Verbose mode')
    parser.add_option_group(extra)

    options, arguments = parser.parse_args()

    if (arguments != []):
        print """Non recognized option %s
        Please use --help for usage""" % arguments
        print usage()
        sys.exit(2)

    if options.hostname is None:
        print "Missing -H HOSTNAME"
        print "We need the hostname of the Foreman server"
        print usage()
        sys.exit(2)

    if options.mode is None:
        print "\nMissing -m MODE"
        print "\nWhat mode are you executing this check in ?"
        print usage()
        sys.exit(2)

    return vars(options)


def main():
    """
    Runs all the functions
    """

    # Command Line Parameters
    user_in = controller()

    if user_in['verbose']:
        def verboseprint(*args):
            """ http://stackoverflow.com/a/5980173
            print only when verbose ON"""
            # Print each argument separately so caller doesn't need to
            # stuff everything to be printed into a single string
            print
            for arg in args:
                print arg,
            print
    else:
        verboseprint = lambda *a: None      # do-nothing function

    # Validate the port based on the required protocol
    if user_in['ssl']:
        protocol = "https"
        # Unspecified port will be 80 by default, not correct if ssl is ON
        if (user_in['port'] == 80):
            user_in['port'] = 443
    else:
        protocol = "http"

    # Let's avoid the double / if we specified a prefix
    if (user_in['prefix'] != '/'):
        user_in['prefix'] = '/%s/' % user_in['prefix']

    user_in['url'] = "%s://%s:%s%shosts/%s/" % (protocol,
                                                user_in['hostname'],
                                                user_in['port'],
                                                user_in['prefix'],
                                                user_in['mode'])

    verboseprint("CLI Arguments : ", user_in)

    foreman_data = get_data(user_in['url'],
                            user_in['username'],
                            user_in['password'],
                            user_in['timeout'])

    verboseprint("Reply from server : \n%s" % json.dumps(foreman_data,
                                                         sort_keys=True,
                                                         indent=2))

    status, message = check_result(user_in, foreman_data)

    print '%s - %s' % (status, message)
    # Exit statuses recognized by Nagios
    if   status == 'OK':
        sys.exit(0)
    elif status == 'WARNING':
        sys.exit(1)
    elif status == 'CRITICAL':
        sys.exit(2)
    else:
        sys.exit(3)


if __name__ == '__main__':
    main()
