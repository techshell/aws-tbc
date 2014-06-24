#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation as cloudformation
import core.config as config
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
parser.add_option("-j", "--jira", dest="jira",
                  help="jira id", metavar="JIRA")
parser.add_option("-f", "--flavour", dest="flavour",
                  help="Flavour, for example blogs, my, tcuk4", metavar="FLAVOUR")
parser.add_option("-c", "--configdir", dest="configdir",
                  help="Aws config directory for service for example ~/code/service/trunk/aws/config", metavar="CONFIG")
parser.add_option("-p", "--package", dest="package",
                  help="debian package", metavar="PACKAGE")
parser.add_option("-t", "--targetelbs", dest="targetelbs",
                  help="This is the resource name or list of resource names for the elb(s),"
                       " for example FeServerLB or ApiServerLb as declared in the yaml + LB"
                       " FeServerLB,ApiServerLB", metavar="TARGETELBS")
(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given')
if not options.package:
    parser.error('Package not given. For ex service-name.deb')
if not options.jira:
    parser.error('Jira not given. JIRA-123')
if not options.targetelbs:
    parser.error('This is the resource name for the elb, for example FeServerLB or '
                 'ApiServerLB as declared in the yaml but + LB')
if not options.flavour:
    parser.error('Flavour not given.')
if not options.jira:
    parser.error('Jira not given')

options.configdir = config.get_user_config_value(options.flavour, 'flavour_config', options.configdir)
if not options.configdir:
    parser.error('No config directory, for example ~/code/service/aws/config')

print options.jira
print options.flavour
print options.configdir
print options.env
print options.package
print options.targetelbs

env = options.env
package = options.package
target_elbs = options.targetelbs.split(',')
flavour = options.flavour
jira = options.jira
configdir = options.configdir
environment_configuration = config.get_environment_configuration(configdir, flavour)

cloudformation.deploy_debian_package(jira, env, package, target_elbs, flavour, environment_configuration)
