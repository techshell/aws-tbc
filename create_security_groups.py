#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation as cloudformation
import core.config as config
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
parser.add_option("-n", "--name", dest="name",
                  help="name", metavar="NAME")
(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given please supply for ex -e prod')
if not options.name:
    parser.error('Name not given please supply for ex -n base')

print options.env
print options.name

env = options.env
name = options.name

security_config = config.get_security_yaml()
global_config = config.get_global_yaml()

cloudformation.create_security_groups(security_config["security_groups"][env], env, name, global_config["network"][env]["VpcId"])