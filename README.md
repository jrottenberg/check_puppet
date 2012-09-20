Check\_Puppet\_*
================


### Usage

#### Command line

You can test it quickly with :

    ./check_puppet.py  -w 30 -c 60 -H server1.example.com -F foreman_host 

Will make sure server1.example has successfully ran puppet and reported back within 30 min (one hour for a critical) 

#### Nagios    

##### Define a command 

    # check puppet 
    # Note : we have ssl ON by default on our foreman installation 
    define command{
        command_name    check_puppet
        command_line    $USER2$/check_puppet.py -S -H $HOSTNAME$ -F foreman.example.com -w $ARG1$ -c $ARG2$
    }

##### Then a service

    define service{
         use                     generic-service
         service_description     check_puppet 
         check_command           check_puppet!60!120!
         host_name               puppet-client1.example.com
    }




[![Build Status](https://secure.travis-ci.org/jrottenberg/check_puppet.png)](http://travis-ci.org/jrottenberg/check_puppet)
