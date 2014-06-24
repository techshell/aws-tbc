#! /usr/bin/env python
import core.ec2_connection
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-i", "--instance", dest="instance",
                  help="instance id", metavar="INSTANCE")
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
(options, args) = parser.parse_args()
if not options.instance:
    parser.error('Instance not given')
if not options.env:
    parser.error('Env not given, for example -e preprod')

print options.instance

conn = core.ec2_connection.ec2_connection(options.env)

output = conn.get_console_output(options.instance)

print output.output
