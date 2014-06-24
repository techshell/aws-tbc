#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation
import core.elb
import core.ec2_connection
import core.securitygroups
import os
from optparse import OptionParser

usage = "usage: %prog -s <stack> -e <environment>"
parser = OptionParser(usage=usage)
parser.add_option("-s", "--stack", dest="stack",
                  help="stack id", metavar="STACK")
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
(options, args) = parser.parse_args()
if not options.stack:
    parser.error('Stack not given, for example -s <stack name>')
if not options.env:
    parser.error('Env not given, for example -e preprod')

print options.stack

stack_resources = core.cloudformation.cloudformation_stack_resources(options.stack, options.env)

stack_elbs = core.cloudformation.cloudformation_stack_physical_resource_id(stack_resources, 'AWS::ElasticLoadBalancing::LoadBalancer')
instance_list = []
for elb in stack_elbs:
    instance = core.elb.get_elb_instances(elb, options.env)
    for instance_result in instance:
        print 'Instance %s is %s' % (instance_result.instance_id, instance_result.state)
        instance_list.append(instance_result.instance_id)

conn = core.ec2_connection.ec2_connection(options.env)

instances = conn.get_all_instances(instance_ids=instance_list)

instance_string = ""
for instance_az in instances:
    for instance in instance_az.instances:
        ipaddress = instance.private_ip_address
        instance_string = instance_string + " " + ipaddress + " "
        print ipaddress
print instance_string
os.system("csshx %s" % instance_string)
