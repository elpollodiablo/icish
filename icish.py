#!/usr/bin/env python

import requests
import os.path
MAX_AUTH_ERRORS=3

def _debug(config, string):
	if config.has_key('debug') and config['debug']:
		print string

# implementation of requesting info from icinga
def _get_user_pass(config):
	"""prompt for missing user/password"""

	if not config.has_key('icinga_user'):
		_debug(config, "No user found in config, prompting")
		while True:
			config['icinga_user'] = raw_input("Username for %s: " % config['icinga_uri'])
			if config['icinga_user'] is not '': break
	if not config.has_key('icinga_password'):
		_debug(config, "No password found in config, prompting")
		import getpass
		config['icinga_password'] = getpass.getpass()
	
def _get_auth(config):
	assert config.has_key('icinga_auth')
	assert config['icinga_auth'] in ('gssapi', 'basic', 'digest', 'none')
	if config['icinga_auth'] == "gssapi":
		_debug(config, "Trying to authenticate with GSSAPI")
		from requests_kerberos import HTTPKerberosAuth
		return HTTPKerberosAuth()
	elif config['icinga_auth'] == 'basic':
		_debug(config, "Trying to authenticate with basic authentication")
		_get_user_pass(config)
		from requests.auth import HTTPBasicAuth
		return HTTPBasicAuth(config['icinga_user'], config['icinga_password'])
	elif config['icinga_auth'] == 'digest':
		_debug(config, "Trying to authenticate with digest authentication")
		_get_user_pass(config)
		from requests.auth import HTTPDigestAuth
		return HTTPDigestAuth(config['icinga_user'], config['icinga_password'])
	elif config['icinga_auth'] == 'none':
		return None


def _get_host_list(config, filter=''):
	status_code = 499
	errors = 0

	# dorky auth error checking ...
	while (status_code >= 400) and (status_code < 500) and (errors is not MAX_AUTH_ERRORS):
		auth = _get_auth(config)
		request_uri = config['icinga_uri'] + "/%s/columns[HOST_NAME]/authkey=%s/json" % (filter, config['icinga_authkey'])
		_debug(config, "request uri: %s" % request_uri)
		r=requests.get(request_uri, auth=auth)
		status_code = r.status_code
		_debug(config, "http status: %s" % status_code)
		if status_code == 500:
			print "icinga didn't like our request %s and responded with %s" %(request_uri, status_code)
			import sys
			sys.exit(1)
		errors += 1
	if errors is MAX_AUTH_ERRORS: 
		print "Too many authentication errors (%i)" % MAX_AUTH_ERRORS
		import sys
		sys.exit(1)
	raw = r.json()
	assert raw.has_key("result")
	result = list() 
	for e in raw['result']:
		if e['HOST_NAME'] not in result:
			result.append(e['HOST_NAME'])
	return result

# implementation of logic expression to icinga rpn notation
OPERATORS = [
	[" like ", "|LIKE|", lambda x: x],
	[" is ", "|=|", lambda x: x],
	[">", "|>|", lambda x: x],
	["<", "|<|", lambda x: x],
	[" not ", "|!=|", lambda x: x],
	[" contains ", "|LIKE|", lambda x: '*' + x + '*'],
	[" startswith ", "|LIKE|", lambda x: x + '*'],
	[" endswith ", "|LIKE|", lambda x: '*' + x],
]
LOGIC = [
	[" and ", " & ", "AND("],
	[" or ", " | ", "OR("]
]
VALUES = [
	[" activehosts "," host_is_active is true "],
	[" activeservices "," service_is_active is true "],
	[" true ", " 1 "],
	[" false ", " 0 "],
	[" ok ", " 0 "],
	[" green ", " 0 "],
	[" warning ", " 1 "],
	[" warn ", " 1 "],
	[" yellow ", " 1 "],
	[" orange ", " 1 "],
	[" critical ", " 2 "],
	[" crit ", " 2 "],
	[" failed ", " 2 "],
	[" fail ", " 2 "],
	[" red ", " 2 "],
	[" unknown ", " -1 "],
	[" purple ", " -1 "],
	[" na ", " -1 "],
	[" service_status ", " service_current_state "],
	[" service_state ", " service_current_state "],
	[" host_status ", " service_current_state "],
	[" host_state ", " service_current_state "],
]
KEYWORDS = [
	"SERVICE_NAME",
	"SERVICE_CURRENT_STATE",
	"SERVICE_ID",
	"SERVICE_IS_FLAPPING",
	"SERVICE_OBJECT_ID",
	"SERVICE_IS_ACTIVE",
	"SERVICE_IS_PENDING",
	"SERVICE_DISPLAY_NAME",
	"SERVICE_OUTPUT",
	"SERVICE_PERFDATA",
	"HOST_NAME",
	"HOST_CURRENT_STATE",
	"HOST_INSTANCE_ID",
	"HOST_DISPLAY_NAME",
	"HOST_ADDRESS",
	"HOST_IS_ACTIVE",
	"HOST_IS_PENDING",
	"HOST_ID",
	"HOST_OBJECT_ID",
	"HOST_ALIAS",
	"HOSTGROUP_NAME",
]

def icingafy(s):
	"""prepare the filter string and call _create_node_tree"""

	s = " " + s + " "
	s=s.replace(")", " ) ").replace("("," ( ")
	
	for logic in LOGIC:
		s=s.replace(logic[0], logic[1])

	for val in VALUES:
		s=s.replace(val[0], val[1])
	_debug(config, "filter with substitutions: %s" % s)
	nt = _create_node_tree(s)
	if nt[0] not in ['&', '|']:
		nt.insert(0, '&')
	return _assemble_icinga_filter(nt)

def _assemble_icinga_filter(nt):
	"""re-assemble the node tree into a icinga compatible filter,
	substitute comparison operators"""

	result=""
	need_parens = False
	for n in nt:
		done = False
		if type(n) == type([]):
			result += _assemble_icinga_filter(n)
			continue
		for l in LOGIC:
			if n == l[1].strip():
				result += l[2]
				need_parens = True
				done = True
				continue

		for op in OPERATORS:
			if n.find(op[0]) > -1:
				a = [e.strip() for e in n.split(op[0])]
				k = a[0].upper()
				#print k
				if k not in KEYWORDS:
					print "expected %s to be a keyword, one of" % (a[0]), ", ".join([kw.lower() for kw in KEYWORDS])
				result += a[0] + op[1] + op[2](a[1]) + ";"
				done = True
		if not done:
			print "I expected %s to be someething, but it wasn't!" % n, nt
	if need_parens:
		result += ");"
	return result			

def _create_node_tree(s):
	"""dissassemble the string recursively and create a nested
	list of nodes, with the logic operators moved into the right place"""

	my_child_nodes = []
	l = len(s)
	l_counter=0
	l_last=0
	nesting=0
	something_in_parens=False
	#print ">>>> called with ", s

	def icingafy_expression(u):
		return u.strip()

	while l_counter < l:
		if s[l_counter] in ["&", "|"]:
			#print "found op"
			if nesting == 0:
				if s[l_last:l_counter].strip() != "":
					my_child_nodes.append(icingafy_expression(s[l_last:l_counter]))
				# reverse to rpn
				if my_child_nodes[0] in ["&", "|"]:
					if s[l_counter] == my_child_nodes[0]:
						# the current expression already has the right operator
						pass
					else:
						# current expression has a different operator: wrap it and
						# prepend the new one
						my_child_nodes = [s[l_counter], my_child_nodes]
				else:
					# no operator in expression yet: prepend
					my_child_nodes.insert(0, s[l_counter])
				l_last = l_counter + 1
			if nesting > 0:
				something_in_parens = True
		if s[l_counter] is "(":
			if nesting == 0:
				if s[l_last:l_counter].strip() != "":
					my_child_nodes.append(icingafy_expression(s[l_last:l_counter]))
				l_last = l_counter + 1
			nesting += 1
		if s[l_counter] is ")":
			nesting -= 1
			if nesting == 0:
				if something_in_parens:
					something_in_parens = False
        	                	my_child_nodes.append(_create_node_tree(s[l_last:l_counter].strip()))
                        	l_last = l_counter + 1

		if l_counter ==  l - 1 and s[l_last:l_counter + 1].strip() != "":
			my_child_nodes.append(icingafy_expression(s[l_last:l_counter+1]))

		l_counter +=1
	return my_child_nodes


def tests():
	"""FIXME: do something more useful here"""
	tests = {
		"all hosts in icinga":"service_name contains APT and (host_name contains prod or host_name contains dev) and service_current_state is fail",
	}

	for test in tests:
		print "=========================================================================================================================="
		print test
		print _translate_to_rpn(test)
		print

def get_hosts_from_icinga(config, entity, filter_text):
	# we need to wrap the filter in one AND() because icinga wants it like that.
	filter = "%s/filter[%s]" % (entity, icingafy(filter_text))
	_debug(config, "icinga filter string: %s" % filter)
	result=[]
	for host in _get_host_list(config, filter):
		if config.has_key("use_domain"):
			result.append(host + "." + config["use_domain"])
		else:
			result.append(host)
		
	return result


if __name__ == "__main__":
	import sys
	if len(sys.argv) > 1 and sys.argv[2] in ["host", "service"]:
		cf = open(sys.argv[1])
		import yaml
		config = yaml.load(cf)
		cf.close()
		print "\n".join(get_hosts_from_icinga(config, sys.argv[2], sys.argv[3]))
	else:
		print """%s <config.yml> [host|service] <filter expression>

  construct conditions using these keywords:
    %s

  and these operators:
    %s

  use shorthands for some values:
    %s

  combine the resulting conditions with "and" and "or"
  and (optionally) nest then in parentheses for explicit
  expressions.

  Examples:
    %s config.yml service 'host_is_active is true and (host_name contains prod or host_name contains important) and service_current_state is critical and service_name contains load'
""" %(sys.argv[0], ", ".join([k.lower().strip() for k in KEYWORDS]), ", ".join([ op[0].strip() for op in OPERATORS]), ", ".join([ v[0].strip() +" (" + v[1].strip() + ")" for v in VALUES]), sys.argv[0])
