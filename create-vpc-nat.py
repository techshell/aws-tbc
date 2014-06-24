#! /usr/bin/env python
import core.ec2_connection
import yaml
#import time

conn = core.ec2_connection.ec2_connection()

# Read in yaml data
f = open('config/config.yaml', 'r')
filedata = f.read()
config = yaml.load(filedata)

print config['ec2']['ami_vpc_nat']

reservation = conn.run_instances(config['ec2']['ami_vpc_nat'], key_name=config['ec2']['key_name'],
                                    instance_type=config['ec2']['instance_type'],
                                    placement=config['ec2']['availability_zone'],
                                    subnet_id=config['ec2']['zoo_public_vpc_subnet'],
                                    security_group_ids=config['ec2']['zoo_tmg_base']
                                    )

eip = conn.allocate_address('vpc')

instance = reservation.instances[0]

# Check up on its status every so often
status = instance.update()
print status
while status == 'pending':
    status = instance.update()

if status == 'running':
    print status
    print instance.id
    # Associate EIP address
    conn.associate_address(instance_id=instance.id,
                               public_ip=None,
                               allocation_id=eip.allocation_id)
else:
    print('Instance status: ' + status)

instance.modify_attribute('sourceDestCheck', 0)

print instance.dns_name
print instance.id