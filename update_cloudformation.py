#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation as cloudformation
import core.config as config
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
parser.add_option("-s", "--stack", dest="stack",
                  help="stack name", metavar="STACK")
parser.add_option("-c", "--configdir", dest="configdir",
                  help="config id", metavar="CONFIG")
#TODO remove timestamp requirement
parser.add_option("-t", "--timestamp", dest="timestamp",
                  help="timestamp", metavar="TIMESTAMP")
(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given')
if not options.stack:
    parser.error('Stack not given. For ex my-stack-app')
if not options.timestamp:
    parser.error('Time stamp not given. Please find out the timestamp for this stack')

stack = options.stack
split = stack.partition('-')
flavour = split[0]
second_split = split[2].rpartition('-')
jira = second_split[0]
target_layer = second_split[2]

options.configdir = config.get_user_config_value(flavour, 'flavour_config', options.configdir)
if not options.configdir:
    parser.error('No config directory, for example ~/code/service/aws/config')

print options.stack
print options.env
print options.configdir

env = options.env
timestamp = options.timestamp
configdir = options.configdir

berks_file = config.get_environment_berks_file(configdir, flavour)
environment_configuration = config.get_environment_configuration(configdir, flavour)

target_formation = environment_configuration['formations'][target_layer]
environment_configuration['formations'] = {}
environment_configuration['formations'][target_layer] = target_formation
environment_configuration['KeyName'] = config.get_user_config_value('key_name', 'user_config')

cloudformation.create_cloudformation_template(environment_configuration, jira, env, flavour, timestamp, berks_file)
