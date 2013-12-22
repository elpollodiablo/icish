icish
=====

A small python script (or module) for producing host lists from an icinga-web server using an almost sane query language.

It uses the requests module to access the icinga-web API, and if this is protected by mod_krb5, you'll also need requests-kerberos.

config
------

The supplied config will need
- icinga_uri: the uri to your icinga-web API endpoint
- icinga_auth: the method of HTTP authentication for the endpoint, if any: gssapi, basic, digest, none
- icinga_authkey: the API authkey that you set up in icinga-web
Optional:
- icinga_user: the user for HTTP authentication. icish.py will ask you for one if you don't supply this value and didn't select gssapi or none as auth method.
- icinga_password: the password for HTTP authentication. icish.py will ask you for one if you don't supply this value and didn't select gssapi or none as auth method.
- debug: you can set this to true to get some useless debug output
- use_domain: the domain that should be suffixed to all hosts produced by icish.py - if you don't have it in your search order.

You can call icish.py all alone:
    ./icish.py <config.yml> [host|service] <filter expression>

A filter expression is constructed by using keywords, operators and values. Call icish.py without any argument for lists of all the keywords and operators (and some shorthands) at your disposal:

    construct conditions using these keywords:
      service_name, service_current_state, service_id, service_is_flapping, service_object_id, service_is_active, service_is_pending, service_display_name, service_output, service_perfdata, host_name, host_current_state, host_instance_id, host_display_name, host_address, host_is_active, host_is_pending, host_id, host_object_id, host_alias, hostgroup_name

    and these operators:
      like, is, >, <, not, contains, startswith, endswith

    use shorthands for some values:
      activehosts (host_is_active is true), activeservices (service_is_active is true), true (1), false (0), ok (0), green (0), warning (1), warn (1), yellow (1), orange (1), critical (2), crit (2), failed (2), fail (2), red (2), unknown (-1), purple (-1), na (-1), service_status (service_current_state), service_state (service_current_state), host_status (service_current_state), host_state (service_current_state)

    combine the resulting conditions with "and" and "or" and (optionally) nest them in parentheses for explicit expressions.


Examples:
---------

* standalone:
    ./icish.py config.yml service 'activeservices and (host_name contains prod or host_name contains infra) and service_current_state is critical and service_name contains load'

* with the onboard, dinky serial-execute.sh:
    ./serial_execute.sh service "service_name contains APT and service_state not ok and service_state not na" "sudo apt-get upgrade -y"

* with pssh:
    parallel-ssh -H "`./icish.py config.yml service 'activeservices and service_name contains APT and service_state not ok and service_state not na'`" sudo apt-get upgrade -y

* with fabric: see fabfile.py

TODO:
-----
- [x] write readme
- [x] give a fabric example
- [ ] better error handling
- [ ] better help
- [ ] maybe better/more shorthand filters
