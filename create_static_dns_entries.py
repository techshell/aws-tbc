#! /usr/bin/env python
# associate static resources with dynamic route53 entries to help manage those pre-generation dns allocation/tracking
__author__ = 'mored'
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

static_dns_config = config.get_static_dns_yaml()

cloudformation.create_static_dns_entries(static_dns_config["static"][env], env, name)