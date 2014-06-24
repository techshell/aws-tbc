#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation
import core.ec2_connection
import core.securitygroups
import core.config as config
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
parser.add_option("-j", "--jira", dest="jira",
                  help="jira id", metavar="JIRA")
parser.add_option("-f", "--flavour", dest="flavour",
                  help="flavour id", metavar="FLAVOUR")
parser.add_option("-c", "--configdir", dest="configdir",
                  help="config id", metavar="CONFIG")
(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given')
if not options.flavour:
    parser.error('Flavour not given.')
if not options.jira:
    parser.error('Jira not given')

options.configdir = config.get_user_config_value(options.flavour, 'flavour_config', options.configdir)
if not options.configdir:
    parser.error('No config directory, for example ~/code/my/aws/config')

print "flavour %s" % options.flavour
print "env %s    " % options.env
print "jira %s   " % options.jira
print "options %s" % options.configdir

env = options.env
flavour = options.flavour
jira = options.jira
configdir = options.configdir

berks_file = config.get_environment_berks_file(configdir, flavour)
environment_configuration = config.get_environment_configuration(configdir, flavour)

core.cloudformation.delete_stacks(environment_configuration, env, flavour, jira)

print "Delete environment security group"
delete = core.cloudformation.cloudformation_delete("sg-%s-%s" % (flavour, jira), env)
print delete



