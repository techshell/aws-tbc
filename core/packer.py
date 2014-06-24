__author__ = 'pierrelarsson'
import os
import os.path
import subprocess
import yaml
import sys
import config
import securitygroups
import cloudformation
import ec2_connection
import json
import shutil


def get_security_groups(env):
    global securitygroup_ids
    securitygroup_ids = []
    if env == 'preprod':
        securitygroup_ids.append(
            securitygroups.security_group_id("infra-security-group-tmgbase-tmgbase-80VVWSVCK8KH", env))
        securitygroup_ids.append(
            securitygroups.security_group_id("bambooagent-infra-be-bambooagentbambooagentinfra2014181312-NGNBKGVDTNGG",
                                             env))
    else:
        securitygroup_ids.append(
            securitygroups.security_group_id("infra-security-group-tmgbase-tmgbase-8TGWK12LFML2", env))
        securitygroup_ids.append(
            securitygroups.security_group_id("bambooagent-infra-be-bambooagentbambooagentinfra20143191455-QMSXETAFIIEM",
                                             env))
    return securitygroup_ids


def load_config(packer_config, env, flavour, global_yaml, ami_type):
    securitygroup_ids = get_security_groups(env)
    packer_config['default']['builders'][0]['subnet_id'] = global_yaml['network'][env]['be']['SubnetEuWest1a']
    packer_config['default']['builders'][0]['vpc_id'] = global_yaml['network'][env]['be']['VpcId']
    packer_config['default']['builders'][0]['security_group_ids'] = securitygroup_ids
    packer_config['default']['builders'][0]['ami_users'] = ['540421644628', '652511239598', '905794038216']
    packer_config['default']['provisioners'] = packer_config['flavour'][flavour][ami_type]['provisioners']
    return packer_config


def create_ami(flavour):
    global ami_id
    command = "/usr/local/bin/packer build -debug -machine-readable %s_ami.json" % flavour

    try:
        print "Building %s Ami image" % flavour
        process = subprocess.Popen(command, shell=True, cwd="packer", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        while True:
            next_line = process.stdout.readline()
            log_line = next_line.split(',')
            if len(log_line) > 4:
                if log_line[2] == 'artifact' and log_line[4] == 'id':
                    ami_id = log_line[5].rsplit(':')[1].rsplit("\n")[0]
                    print "New ami id %s" % ami_id
            if next_line == '' and process.poll() != None:
                break
            sys.stdout.write(next_line)
            sys.stdout.flush()

        exitCode = process.returncode
        print "Build completed with exit code %s" % exitCode
        if ami_id:
            return ami_id
        else:
            raise subprocess.CalledProcessError(command, exitCode)
            print "Build failure"
            sys.exit(1)
    except subprocess.CalledProcessError, e:
        print e.output
        sys.exit(1)


def git_clone_flavour(gitrepo, flavour, branch):
    try:
        if os.path.exists('packer/%s/' % flavour):
            shutil.rmtree('packer/%s/' % flavour)
        print "checking out %s" % flavour
        command = '/usr/bin/git clone -b %s %s packer/%s' % (branch, gitrepo, flavour)
        git_clone_log = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        print git_clone_log
    except Exception, e:
        print e
        sys.exit(1)


def create_node_json(flavour, chef_path, env):
    f = open('packer/%s/config/%s.yaml' % (flavour, flavour), 'r+')
    filedata = f.read()
    f.close()
    flavour_yaml = yaml.load(filedata)

    if chef_path['type'] == "autoscaling_group":
        chef = \
            flavour_yaml['formations'][chef_path['network']]['autoscaling_groups'][chef_path['name']]['launchconfig'][
                'chef']
    chef = cloudformation.add_chef_env(chef, 'ami_build', 'ami_build', 'ami_build', env, flavour, flavour_yaml['env'])

    global_config = config.get_global_yaml()
    chef_run_with_defaults = global_config['defaults']['chef']['run_list']
    for run_list in chef['run_list']:
        chef_run_with_defaults.append(run_list)
    chef['run_list'] = chef_run_with_defaults
    if os.path.exists('packer/%s/config/node.json' % flavour):
        os.remove('packer/%s/config/node.json' % flavour)
    f = open('packer/%s/config/node.json' % flavour, 'w')
    f.write(json.dumps(chef, sort_keys=True, indent=4, separators=(',', ': ')))
    f.close()


def create_solo_rb(flavour):
    solorb = """
    log_level :debug
    log_location STDOUT
    data_bag_path "/var/chef-solo/cookbooks/base/data_bags"
    file_cache_path "/var/chef-solo"
    cookbook_path "/var/chef-solo/cookbooks"
    json_attribs "/etc/chef/node.json"
    log_location "/var/log/chef-solo.log"
    """
    if os.path.exists('packer/%s/config/solo.rb' % flavour):
        os.remove('packer/%s/config/solo.rb' % flavour)
    f = open('packer/%s/config/solo.rb' % flavour, 'w')
    f.write(solorb)
    f.close()


def push_ami_to_git(flavour, ami_id, ami_type):
    # Read in yaml data and commit new AMI id to git
    f = open('config/packer.yaml', 'r+')
    filedata = f.read()
    f.close()
    os.remove('config/packer.yaml')
    f = open('config/packer.yaml', 'w')
    config = yaml.load(filedata)
    config['flavour'][flavour][ami_type]['ami'] = str(ami_id)
    f.write(yaml.dump(config, default_flow_style=False))
    f.close()
    try:
        print "Committing change to packer.yaml"
        command = '/usr/bin/git commit -m "Setting new %s %s ami image %s" packer.yaml' % (flavour, ami_type, ami_id)
        git_log = subprocess.check_output(command, shell=True, cwd="config", stderr=subprocess.STDOUT)
        print git_log
    except Exception, e:
        print e
        sys.exit(1)
    try:
        print "Setting remote git repository - hack for Bamboo"
        command = 'git remote set-url origin ssh://git@stash.aws.telegraph.co.uk:8080/in/aws.git'
        git_remote_log = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        print git_remote_log
    except Exception, e:
        print e
        sys.exit(1)
    try:
        print "Pulling from stash"
        command = '/usr/bin/git pull origin master'
        git_pull_log = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        print git_pull_log
    except Exception, e:
        print e
        sys.exit(1)
    try:
        print "Pushing to stash"
        command = '/usr/bin/git push'
        git_push_log = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        print git_push_log
    except Exception, e:
        print e
        sys.exit(1)

def cleanup_packer(flavour):
    try:
        if (flavour == 'gold'):
            print "Removing temporary files packer/%s_ami.json packer/ec2_amazon-ebs.pem" % flavour
        else:
            print "Removing temporary files packer/%s/ packer/%s_ami.json packer/ec2_amazon-ebs.pem" % (flavour, flavour)
            shutil.rmtree('packer/%s/' % flavour)
        os.remove('packer/%s_ami.json' % flavour)
        os.remove('packer/ec2_amazon-ebs.pem')
    except Exception, e:
        print e
        sys.exit(1)


def get_packer_yaml():
    # Read in yaml and return ami for flavour.
    # If flavour is empty pull gold.
    try:
        f = open('config/packer.yaml', 'r+')
        filedata = f.read()
        f.close()
        packer_config = yaml.load(filedata)
        return packer_config
    except Exception, e:
        print "could not open packer.yaml."
        sys.exit(1)


def get_packer_ami(flavour, formation):
    print "get_packer_ami for flavour: %s formation: %s" % (flavour, formation)
    # Read in yaml and return ami for flavour.
    packer_config = get_packer_yaml()

    try:
        #set gold flavour as default
        ami = get_gold_ami()
        print "default gold ami is %s" % ami

        #there exist many formations types for any given flavour
        for item in packer_config["flavour"][flavour]:
            if item == formation:
                ami = packer_config["flavour"][flavour][formation]["ami"]
                break
            else:
                print "ami not found for flavour: %s formation: %s" % (flavour, formation)

        print "ami from packer set to %s " % ami
        return ami

    except Exception, e:
        print "formation: %s flavour: %s not found on packer.yaml - %s" % (formation, flavour, e.message)
        if ami == "":
            print "could not find any ami for flavour nor gold default: %s formation: %s " % (formation, flavour)
            sys.exit(1)
        else:
            print "using default ami! - set %s" % ami
            return ami


def get_gold_ami():
    packer_config = get_packer_yaml()
    return packer_config["flavour"]["gold"]["default"]["ami"]


def update_yamls_amis():
    packer_config = get_packer_yaml()
    #loop through the yamls configured
    for flavour in packer_config["flavour"]:
        if flavour != 'gold':
            if flavour in packer_config.get('flavour', {}):
                print "flavour : [%s]" % flavour
                filename = "config/%s.yaml" % flavour
                if os.path.isfile(filename):
                    f = open(filename, 'r')
                    filedata = f.read()
                    flavour_config = yaml.load(filedata)
                    f.close()
                else:
                    print "[%s] not found [SKIPPED]!" % filename
                    continue

                for formation in packer_config["flavour"][flavour]:
                    print "checking [%s][%s]" % (flavour, formation)
                    # checking if there are formations defined
                    if formation in flavour_config.get('formations', {}):
                        #we need to loop all the instances under an app block. usually referenced as ec2.
                        for category in flavour_config['formations'][formation]:
                            # do we have autoscaling groups?
                            if category == 'autoscaling_groups':
                                change_ami_on_instance(category, flavour, formation, flavour_config, packer_config, filename)
                            elif category == 'ec2':
                                change_ami_on_instance(category, flavour, formation, flavour_config, packer_config, filename)
                    else:
                        print "packer.yaml [%s][%s] undefined" % (flavour, formation)
                        continue


def get_ami_from_packer(packer_config, flavour, formation, instance, entity, filename):

    gold_ami = get_gold_ami()
    if formation in packer_config.get('flavour', {}).get(flavour, {}):
        #check for null contents
        if packer_config['flavour'][flavour].get(formation, {}) is not None:
            if packer_config['flavour'][flavour][formation].get(instance, {}) is not None:
                #if there is an entity get that.
                if instance not in packer_config['flavour'][flavour][formation]:
                    print "missing configuration block on packer.yaml-->['flavour'][%s][%s][%s]" \
                          % (flavour, formation, instance)
                else:
                    if packer_config['flavour'][flavour][formation][instance].get(entity, {}) is not None:
                        if 'ami' in packer_config['flavour'][flavour][formation][instance].get(entity, {}):
                            flavour_ami = packer_config["flavour"][flavour][formation][instance][entity]["ami"]
                            print "packer.yaml [%s][%s][%s][%s]['ami'] => %s " % (flavour, formation, instance, entity, flavour_ami)
                        elif 'ami' in packer_config['flavour'][flavour][formation].get(instance, {}):
                            flavour_ami = packer_config["flavour"][flavour][formation][instance]["ami"]
                            print "packer.yaml [%s][%s][%s]['ami'] => %s " % (flavour, formation, instance, flavour_ami)
                        else:
                            print "packer.yaml [%s][%s][%s][%s]['ami'] not found. setting golden ami %s" % (flavour, formation, instance, entity, gold_ami)
                            flavour_ami = gold_ami
                    else:
                        print "packer.yaml [%s][%s][%s]['ami'] not found. setting golden ami %s" % (flavour, formation, instance, gold_ami)
                        flavour_ami = gold_ami
            else:
                print "configuration of packer.yaml is null for [%s][%s] - [ignoring] !" % (flavour, formation)
        else:
            print "configuration of packer.yaml is null for [%s][%s] - [ignoring] !" % (flavour, formation)
    else:
        print "configuration of packer.yaml is null for [%s][%s] - [ignoring] !" % (flavour, formation)
    return flavour_ami


def change_ami_on_instance(instance, flavour, formation, flavour_config, packer_config, filename):
    #print "identified instance %s" % instance
    #does it contain flavour sub reference??
    #can also contain subobjects which hold amis.
    if flavour_config['formations'][formation].get(instance, {}) is not None:
        for element in flavour_config['formations'][formation][instance]:
            flavour_ami = get_ami_from_packer(packer_config, flavour, formation, instance, element, filename)
            if 'ami' in flavour_config['formations'][formation][instance][element]:
                existing_ami = flavour_config['formations'][formation][instance][element]['ami']
                if existing_ami == flavour_ami:
                    #nothing to do
                    print "ami match %s [%s][%s][%s][%s]['ami'] %s ==  %s " % (filename, flavour, formation, instance, element, existing_ami, flavour_ami)
                else:
                    flavour_config['formations'][formation][instance][element]['ami'] = str(flavour_ami)
                    f = open(filename, 'w')
                    f.write(yaml.dump(flavour_config, default_flow_style=False, default_style=''))
                    f.close()
                    print "ami updated %s [%s][%s][%s][%s]['ami'] from %s => to %s " % (filename, flavour, formation, instance, element, existing_ami, flavour_ami)
            else:
                continue
    else:
        print "expected type ref under ['formations'][%s][%s][%s]!" % (
            formation, instance, flavour)





