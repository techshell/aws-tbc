#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation as cloudformation
import core.config as config
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="Environment, for example prod or preprod", metavar="ENV")
parser.add_option("-s", "--status", dest="status", default=False,
                  help="true or false", metavar="STATUS")

(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given')

print "env %s    " % options.env
print "status %s " % options.status

env = options.env
timestamp = config.get_time_stamp(env)

if bool(options.status):
    status = options.status
else:
    status = None

global_config = config.get_global_yaml()

cloudformation.create_vpc(global_config['vpc'], env, timestamp, status)
