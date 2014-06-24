#! /usr/bin/env python
import time
import core.ec2_connection
import core.config as config
import core.packer as packer
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="Environment, for example prod or preprod", metavar="ENV")
parser.add_option("-i", "--instance", dest="instance",
                  help="Optional, defaults to m1.small. Instance size. For example m1.small", metavar="INSTANCE")
parser.add_option("-a", "--ami", dest="ami",
                  help="Ami id. For example ami-d3xxxx", metavar="AMI")

(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given')
if not options.instance:
    options.instance = "m1.small"
if not options.ami:
    parser.error('Ami not given')

print options.env
print options.instance
print options.ami

env = options.env
instance_size = options.instance
ami = options.ami

conn = core.ec2_connection.ec2_connection(env)

# Read in yaml data
global_yaml = config.get_global_yaml()


def create_instance():
    global dev_sdc, mapping, reservation, instance, status

    reservation = conn.run_instances(ami, key_name=config.get_user_config_value('key_name', 'user_config'),
                                     security_group_ids=packer.get_security_groups(env),
                                     instance_type=instance_size,
                                     placement=global_yaml['defaults'][env]['AvailabilityZones'][0],
                                     #TODO remove hard coded network config
                                     subnet_id=global_yaml['network'][env]['be']['SubnetEuWest1a']
    )
    time.sleep(2)
    instance = reservation.instances[0]
    # Check up on its status every so often
    status = instance.update()

    while status == 'pending':
        status = instance.update()
    if status == 'running':
        print status
    else:
        print('Instance status: ' + status)

    print instance.private_ip_address
    print instance.id
    return instance

instance = create_instance()