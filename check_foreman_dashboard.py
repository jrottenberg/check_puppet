#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""

Contact foreman to check the global health of the puppet nodes.

If not too many clients are out of sync or in error

"""
__author__ = 'Ewoud Kohl van Wijngaarden'
__date__ = "December 2013"

__version__ = "1.0"
__credits__ = """Thanks to Foreman - http://theforeman.org/"""


from optparse import OptionParser, OptionGroup
import base64
import urllib2
from urllib2 import HTTPError, URLError
from socket import setdefaulttimeout

try:
    import simplejson as json
except ImportError:
    import json


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
        print 'CRITICAL - Check %s does that node ever reported?' % url
        raise SystemExit(2)
    except URLError:
        print 'CRITICAL - Error on %s Double check foreman name' % url
        raise SystemExit(2)

    return out


def check_result(params, dashboard):
    """
    From the server response and input parameter
    check if the puppet client report should trigger an alert

    http://theforeman.org/projects/foreman/wiki/API
    """

    mode = params['mode']
    target = dashboard[mode]
    msg = '%s has %s servers' % (mode, target)

    if (target >= params['critical']):
        status = 'CRITICAL'
    elif (target >= params['warning']):
        status = 'WARNING'
    else:
        msg = '%s - %s' % (msg, dashboard)
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

    check_puppet_nodes.py -H foreman.example.com -m out_of_sync_hosts -w 5 -c 10
    will check if less than 5 nodes are out of sync, 10 for a critical

    """
    return usage_string


def controller():
    """
    Parse user input, fail quick if not enough parameters
    """

    modes = ['pending_hosts', 'good_hosts', 'disabled_hosts',
            'reports_missing', 'active_hosts_ok_enabled',
            'pending_hosts_enabled', 'good_hosts_enabled', 'active_hosts_ok',
            'total_hosts', 'ok_hosts_enabled', 'out_of_sync_hosts_enabled',
            'active_hosts', 'bad_hosts_enabled', 'ok_hosts',
            'out_of_sync_hosts', 'bad_hosts']

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
                      choices=modes, help='Mode of check')

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
        raise SystemExit(2)

    if options.hostname is None:
        print "Missing -H HOSTNAME"
        print "We need the hostname of the Foreman server"
        print usage()
        raise SystemExit(2)

    if options.mode is None:
        print "\nMissing -m MODE"
        print "\nWhat mode are you executing this check in ?"
        print usage()
        raise SystemExit(2)

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

    user_in['url'] = "%s://%s:%s%sapi/dashboard/" % (protocol,
                                                     user_in['hostname'],
                                                     user_in['port'],
                                                     user_in['prefix'])

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
    if status == 'OK':
        raise SystemExit(0)
    elif status == 'WARNING':
        raise SystemExit(1)
    elif status == 'CRITICAL':
        raise SystemExit(2)
    else:
        raise SystemExit(3)


if __name__ == '__main__':
    main()
