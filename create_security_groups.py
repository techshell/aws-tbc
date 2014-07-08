#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation as cloudformation
import core.config as config
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
parser.add_option("-v", "--vpc", dest="vpc",
                  help="vpc", metavar="VPC")
parser.add_option("-n", "--name", dest="name",
                  help="name", metavar="NAME")
(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given please supply for ex -e prod')
if not options.name:
    parser.error('Name not given please supply for ex -n base')
if not options.vpc:
    parser.error('Vpc not given, for ex -n application')

print options.env
print options.name
print options.vpc

env = options.env
name = options.name
vpc = options.vpc

security_config = config.get_security_yaml()
global_config = config.get_global_yaml()
network = {}
network = config.set_vpc_id(vpc, network, env, global_config)

cloudformation.create_security_groups(security_config["security_groups"][env], env, name, network["VpcId"])