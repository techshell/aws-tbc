#! /usr/bin/env python
import time
import core.ec2_connection
import core.config as config
import core.packer as packer
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="Environment, for example prod or preprod", metavar="ENV")
parser.add_option("-s", "--search", dest="search",
                  help="Optional, filter for this volume name", metavar="SEARCH")
parser.add_option("-t", "--tag", dest="tag",
                  help="Tag and values, eg \"-t Billing,Junk,Pierre,Larsson\" would set tags Billing=Junk and Pierre=Larsson", metavar="TAG")

(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given')
if not options.tag:
    parser.error('Tag not given')

print options.env
print options.tag
if options.search:
    print options.search

env = options.env
tag = options.tag
if options.search:
    search = options.search

conn = core.ec2_connection.ec2_connection(env)
tag_list = tag.split(",")

tag_dict = dict(zip(tag_list[0::2], tag_list[1::2]))

all_instances = conn.get_only_instances(filters={"tag:Name": "*%s*" % search})

for instance in all_instances:
    print "Finding volumes for instance %s" % instance.id
    for block_device in instance.block_device_mapping:
        volumes = conn.get_all_volumes(volume_ids=[instance.block_device_mapping[block_device].volume_id])
        for volume in volumes:
            print "Tagging volume %s" % volume.id
            conn.create_tags(resource_ids=volume.id,tags=tag_dict)
