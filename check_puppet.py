#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""

Contact foreman to see when was the last puppet run for a given client.

If the client reported within valid period,
check also that puppet reported a success



Few doctests, run with :
 $ python -m doctest check_puppet.py -v

"""
__author__ = 'Julien Rottenberg'
__date__ = "February 2012"

__version__ = "1.0"
__credits__ = """Thanks to Foreman - http://theforeman.org/"""

from datetime import timedelta, datetime
from optparse import OptionParser, OptionGroup
import base64
import urllib2
import re
import json
from urllib2 import HTTPError, URLError
from socket import setdefaulttimeout


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
        raise SystemExit, 2
    except URLError:
        print 'CRITICAL - Error on %s Double check foreman name' % url
        raise SystemExit, 2

    return out


def seconds2human(my_time):
    """
    Convert given duration in seconds into human readable string

    >>> seconds2human(60)
    '0:01:00'

    >>> seconds2human(300)
    '0:05:00'

    >>> seconds2human(3601)
    '1:00:01'

    >>> seconds2human(86401)
    '1 day, 0:00:01'
    """

    time_delta = timedelta(seconds=my_time)
    return str(time_delta)


def check_result(params, server):
    """
    From the server response and input parameter
    check if the puppet client report should trigger an alert

    http://theforeman.org/projects/foreman/wiki/API
    """

    last_report_str = server['reported_at']
    report_summary = server['summary']

    try:
        total_report_time = server['metrics']['time']['total']
    # foreman seems to have issue with sum of time for some reports
    except KeyError:
        total_report_time = 'N/A'
    # No dateutil.parser on centos5 stock (python-dateutil.noarch)
    # we know output timezone is Zulu
    last_report = datetime(*map(int, re.split('[^\d]', last_report_str)[:-1]))
    # see http://stackoverflow.com/a/127872 for details

    now = params['now']
    now_since_last_report = now - last_report

    msg = 'Last report was marked as %s %s ago - took %s seconds' % (
                    report_summary,
                    now_since_last_report,
                    total_report_time)

    if (now_since_last_report >= timedelta(minutes=params['critical'])):
        status = 'CRITICAL'
    elif (now_since_last_report >= timedelta(minutes=params['warning'])):
        status = 'WARNING'
    else:
        if (report_summary != 'Success'):
            status = 'WARNING'
        else:
            status = 'OK'

    return(status, msg)


def usage():
    """
    Return usage text so it can be used on failed human interactions
    """

    usage_string = """
    usage: %prog [options] -H SERVER -F FOREMAN_HOST -w WARNING -c CRITICAL

    Make sure the last report seen by report for the given host is not too old
    or exiting with an error

    Warning and Critical are defined in minutes

    Ex :

    check_puppet.py -H server1.example.com -F foreman.example.com -w 60 -c 120
    will check if the server1 has reported to foreman.example.com in the last hour

    """
    return usage_string


def controller():
    """
    Parse user input, fail quick if not enough parameters
    """

    description = """A Nagios plugin to check if the last report
for a puppet client was successful and not too long ago."""

    version = "%prog " + __version__
    parser = OptionParser(description=description, usage=usage(),
                            version=version)
    parser.set_defaults(verbose=False)

    parser.add_option('-H', '--hostname', type='string',
                        help='Puppet client hostname')

    parser.add_option('-w', '--warning', type='int', default=30,
                        help='Warning threshold in minutes')

    parser.add_option('-c', '--critical', type='int', default=60,
                        help='Critical threshold in minutes')

    parser.add_option('-F', '--foreman', type='string',
                        help='foreman host to contact')

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
        raise SystemExit, 2

    if (options.hostname == None):
        print "-H HOSTNAME"
        print "We need the puppet client hostname to test against"
        print usage()
        raise SystemExit, 2

    if (options.foreman == None):
        print "\n-F FOREMAN_SERVER"
        print "\nWe need to know which Foreman to query against"
        print usage()
        raise SystemExit, 2

    return vars(options)


def main():
    """
    Runs all the functions
    """

    # Command Line Parameters
    user_in = controller()

    if user_in['verbose']:
        def verboseprint(*args):
            """ http://stackoverflow.com/a/5980173 print only when verbose ON"""
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

    user_in['url'] = "%s://%s:%s%shosts/%s/%s" % (protocol,
                        user_in['foreman'],
                        user_in['port'],
                        user_in['prefix'],
                        user_in['hostname'],
                        'reports/last')

    # Get the current UTC time, no need to get the microseconds
    # we use UTC time as foreman output utc time by default
    user_in['now'] = datetime.utcnow().replace(microsecond=0)

    verboseprint("CLI Arguments : ", user_in)

    foreman_out = get_data(user_in['url'],
                           user_in['username'],
                           user_in['password'],
                           user_in['timeout'])

    verboseprint("Reply from server : \n%s" % json.dumps(foreman_out,
                                                         sort_keys=True,
                                                         indent=2))

    status, message = check_result(user_in, foreman_out['report'])

    print '%s - %s' % (status, message)
    # Exit statuses recognized by Nagios
    if   status == 'OK':
        raise SystemExit, 0
    elif status == 'WARNING':
        raise SystemExit, 1
    elif status == 'CRITICAL':
        raise SystemExit, 2
    else:
        raise SystemExit, 3


if __name__ == '__main__':
    main()
