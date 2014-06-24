#! /usr/bin/env python
__author__ = 'larssonp'
import yaml
import core.config as config
import core.packer as packer
import json
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="Environment, for example prod or preprod", metavar="ENV")
parser.add_option("-f", "--flavour", dest="flavour",
                  help="The image flavour, for example gold, service name", metavar="FLAVOUR")
parser.add_option("-t", "--type", dest="type",
                  help="The type of image, for example default(gold), app, api, cms", metavar="TYPE")
parser.add_option("-b", "--branch", dest="branch",
                  help="Optional, defaults to master. The branch to clone the flavour from", metavar="BRANCH")
(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given')
if not options.flavour:
    parser.error('Flavour not given. for example gold, service name')
if not options.type:
    parser.error('Type not given. for example default(gold), app, api, cms')
if not options.branch:
    options.branch = 'master'

print options.env
print options.flavour
print options.type
print options.branch

env = options.env
flavour = options.flavour
ami_type = options.type
branch = options.branch

aws_access_key_id, aws_secret_access_key = config.aws_login(env)
global_yaml = config.get_global_yaml()
bamboo_agent_instance_role = global_yaml['defaults'][env]['BambooAgentInstanceRole']

#Load packer config
f = open('config/packer.yaml', 'r+')
filedata = f.read()
f.close()
packer_config = yaml.load(filedata)

if flavour != 'gold':
    packer_config['default']['builders'][0]['source_ami'] = packer_config['flavour']['gold']['default']['ami']
    packer.git_clone_flavour(packer_config['flavour'][flavour][ami_type]['gitrepo'], flavour, branch)
    packer.create_node_json(flavour, packer_config['flavour'][flavour][ami_type]['chef_path'], env)
    packer.create_solo_rb(flavour)

packer_config = packer.load_config(packer_config, env, flavour, global_yaml, ami_type)

if aws_access_key_id:
    packer_config['default']['builders'][0]['access_key'] = aws_access_key_id
    packer_config['default']['builders'][0]['secret_key'] = aws_secret_access_key

f = open('packer/%s_ami.json' % flavour, 'w')
f.write(json.dumps(packer_config['default'],sort_keys=True, indent=4, separators=(',', ': ')))
f.close()

ami_id = packer.create_ami(flavour)

packer.cleanup_packer(flavour)

packer.push_ami_to_git(flavour, ami_id, ami_type)
