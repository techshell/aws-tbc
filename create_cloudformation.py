#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation as cloudformation
import core.config as config
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="Environment, for example prod or preprod", metavar="ENV")
parser.add_option("-j", "--jira", dest="jira",
                  help="The jira identifier", metavar="JIRA")
parser.add_option("-f", "--flavour", dest="flavour",
                  help="Flavour, service name", metavar="FLAVOUR")
parser.add_option("-c", "--configdir", dest="configdir",
                  help="Aws config directory for service for example ~/code/service/aws/config", metavar="CONFIG")
parser.add_option("-t", "--timestamp", dest="timestamp",
                  help="timestamp", metavar="TIMESTAMP")
parser.add_option("-s", "--status", dest="status", default=False,
                  help="true or false", metavar="STATUS")

(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given')
if not options.flavour:
    parser.error('Flavour not given.')
if not options.jira:
    parser.error('Jira not given')

options.configdir = config.get_user_config_value(options.flavour, 'flavour_config', options.configdir)
if not options.configdir:
    parser.error('No config directory, for example ~/code/service/aws/config')

print "flavour %s" % options.flavour
print "env %s    " % options.env
print "jira %s   " % options.jira
print "options %s" % options.configdir
print "status %s " % options.status

env = options.env
flavour = options.flavour
jira = options.jira
configdir = options.configdir
if bool(options.status):
    status = options.status
else:
    status = None

berks_file = config.get_environment_berks_file(configdir, flavour)
environment_configuration = config.get_environment_configuration(configdir, flavour)
formation_security_group = ("sg-%s-%s" % (flavour, jira))
environment_configuration['KeyName'] = config.get_user_config_value('key_name', 'user_config')

if options.timestamp:
    timestamp = options.timestamp
else:
    timestamp = config.get_time_stamp(formation_security_group, env)

cloudformation.create_cloudformation_template(environment_configuration, jira, env, flavour, timestamp, berks_file, status)
