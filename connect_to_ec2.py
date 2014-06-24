#! /usr/bin/env python
__author__ = 'larssonp'
import core.ec2_connection as ec2_connection
from optparse import OptionParser
import os

parser = OptionParser()
parser.add_option("-i", "--instance", dest="instance",
                  help="instance id", metavar="INSTANCE")
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
(options, args) = parser.parse_args()
if not options.instance:
    parser.error('Instance not given')
if not options.env:
    parser.error('Env not given')

print options.instance

conn = ec2_connection.ec2_connection(options.env)

instance = conn.get_all_instances(instance_ids=[options.instance])

ipaddress = instance[0].instances[0].private_ip_address

os.system("ssh %s" % ipaddress)
