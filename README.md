Check\_Puppet\_*
================


### Usage

#### Command line

You can test it quickly with :

    ./check_puppet.py  -w 30 -c 60 -H server1.example.com -f foreman_host 

Will make sure server1.example has successfully ran puppet and reported back within 30 min (one hour for a critical) 

#### Nagios    

##### Define a command 

    # check puppet 
    # Note : we have ssl ON by default on our foreman installation 
    define command{
        command_name    check_jenkins_job
        command_line    $USER2$/check_jenkins_job.py -S -H $HOSTNAME$ -j $ARG1$ -w $ARG2$ -c $ARG3$ -u $ARG4$ -p $ARG5$ 
    }

##### Then a service

    define service{
         use                     generic-service
         service_description     check_jenkins Process data
         check_command           check_jenkins_job!Large_data_process!360!540!nagios!readonly!
         host_name               data-process-01.acme.tld
    }


I'd recommend to put the various scripts in a folder defined with `$USER2$` in resource.cfg, to avoid having it with system package based checks in `$USER1$`



