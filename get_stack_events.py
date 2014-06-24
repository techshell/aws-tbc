#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation
import core.ec2_connection
from optparse import OptionParser

usage = "usage: %prog -s <stack> -e <environment>"
parser = OptionParser(usage=usage)
parser.add_option("-s", "--stack", dest="stack",
                  help="stack id", metavar="STACK")
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
(options, args) = parser.parse_args()
if not options.stack:
    parser.error('Stack not given -s')
if not options.env:
    parser.error('Env not given -e')

print options.stack

events = core.cloudformation.cloudformation_stack_events(options.stack, options.env)

print "Stack events"
for event in events:
    print event.event_id, event.resource_status_reason

stack = core.cloudformation.cloudformation_output(options.stack, options.env)

print "Stack outputs"
for output in stack[0].outputs:
    print output
