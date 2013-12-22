from fabric.api import env, run

from icish import get_hosts_from_icinga

icish_config =  {'icinga_uri': 'http://my.icinga.host/icinga-web/web/api', 'use_domain': 'my.domain', 'icinga_authkey': 'dummyauthkey', 'icinga_auth': 'none', 'debug':True}

def set_outdated_hosts(entity='service', filter='activeservices and service_name contains APT and service_state not ok and service_state not na'):
	env.hosts.extend(get_hosts_from_icinga(icish_config, entity, filter))

def host_type():
    run('uname -s')
