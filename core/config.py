__author__ = 'larssonp'
import yaml
import glob
import userdata_lib
import cloudformation
import os
import pwd
from os.path import expanduser
import ConfigParser
import string
import random
import s3
import sys
from datetime import datetime
import threading


def __init__(self):
        self.lock = threading.RLock()


def synchronized_with_attr(lock_name):

    def decorator(method):
        def synced_method(self, *args, **kws):
            lock = getattr(self, lock_name)
            with lock:
                return method(self, *args, **kws)

        return synced_method
    return decorator


def synchronized(func):
    func.__lock__ = threading.Lock()
    def synced_func(*args, **kws):
        with func.__lock__:
            return func(*args, **kws)

    return synced_func


@synchronized
def get_time_stamp(env, formation_security_group=None):
    if formation_security_group:
        stack = cloudformation.cloudformation_stack_status(formation_security_group, env)
    else:
        stack = None
    if stack:
        if (stack[0].stack_status == 'CREATE_COMPLETE') or (stack[0].stack_status == 'UPDATE_COMPLETE'):
            print "%s already created" % formation_security_group
            stack = cloudformation.cloudformation_output(formation_security_group, env)
            timestamp = stack[0].tags["timestamp"]
            return timestamp
        elif (stack[0].stack_status == 'DELETE_IN_PROGRESS'):
            print "Error: %s is being deleted" % formation_security_group
            print stack[0].stack_status
            sys.exit(1)
        elif (stack[0].stack_status == 'DELETE_FAILED'):
            print "Error: %s is and old security group that is has failed to delete" % formation_security_group
            print stack[0].stack_status
            sys.exit(1)
    else:
        now = datetime.now()
        timestamp = "%s%s%s%s%s" % (now.year, now.month, now.day, now.hour, now.minute )
    return timestamp


@synchronized
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


def get_db_passwd(env, password, password_ref, bucket):
    key = s3.s3_check_key(password, env, bucket, password_ref)
    if key:
        return key.get_contents_as_string()
    else:
        db_passwd = id_generator(15)
        s3.s3_upload_key(password, env, bucket, password_ref, db_passwd)
    return db_passwd


@synchronized
def aws_login(env=0):

    global user, creator_tag, home, Config, aws_access_key_id, aws_secret_access_key
    user = pwd.getpwuid(os.getuid())[0]
    creator_tag = dict(creator=user, critical="false")
    home = expanduser("~")
    Config = ConfigParser.ConfigParser()
    if env:
        Config.read("%s/.ssh/aws.%s.cfg" % (home, env))
    else:
        Config.read("%s/.ssh/aws.cfg" % home)
    try:
        aws_access_key_id = Config.get('aws_keys', 'aws_access_key_id')
    except:
        aws_access_key_id = 0
    try:
        aws_secret_access_key = Config.get('aws_keys', 'aws_secret_access_key')
    except:
        aws_secret_access_key = 0
    return aws_access_key_id, aws_secret_access_key


def get_user_config_value(key, section, value=None):
    user_config = get_user_config()
    if value:
        print "Key Value Overriden"
        return value
    else:
        try:
            value = user_config.get(section, key)
        except:
            print("No config defined for %s check your ~/.ssh/environments.cfg" % section)
            sys.exit(1)
        return value


def get_user_config():
    global user, home, Config
    user = pwd.getpwuid(os.getuid())[0]
    home = expanduser("~")
    config = ConfigParser.ConfigParser()
    config.read("%s/.ssh/aws-tbc.cfg" % (home))
    return config


def get_global_yaml():
    # Read in yaml data
    f = open('config/config.yaml', 'r')
    filedata = f.read()
    config = yaml.safe_load(filedata)
    return config


def get_security_yaml():
    # Read in yaml data
    f = open('config/security.yaml', 'r')
    filedata = f.read()
    config = yaml.safe_load(filedata)
    return config


def get_static_dns_yaml():
    # Read in yaml data via a h/d ref
    f = open('config/static.yaml', 'r')
    filedata = f.read()
    config = yaml.safe_load(filedata)
    return config


def get_bucket_yaml():
    # Read in yaml data
    f = open('config/bucket.yaml', 'r')
    filedata = f.read()
    config = yaml.safe_load(filedata)
    return config


def populate_userdata(environment_object, type, stack_name, cloudformation_parameters, resource):
    if type == "launchconfig":
        userdata_name = environment_object[type]["userdata"]
        userdata_launch_resource = "%sLaunchConfig" % resource
        userdata = userdata_lib.get(stack_name, userdata_launch_resource, environment_object[type], type)
    else:
        userdata_name = environment_object["userdata"]
        userdata_launch_resource = resource
        userdata = userdata_lib.get(stack_name, userdata_launch_resource, environment_object, type)
    cloudformation_parameters.append((userdata_name, userdata))
    return cloudformation_parameters


def get_user_data(cloudformation_parameters, formation, stack_name):
    # Read in cloud config user data
    for resource in formation:
        if resource == "Gluster":
            cloudformation_parameters = populate_userdata(formation[resource], "ec2", stack_name, cloudformation_parameters)
        elif resource == "autoscaling_groups":
            cloudformation_parameters = populate_userdata(formation[resource], "launchconfig", stack_name, cloudformation_parameters)
    return cloudformation_parameters


def get_yaml_as_list(config_area, env):
    yaml = get_global_yaml()
    yaml_list = []
    if yaml[config_area]:
        for key, value in yaml[config_area][env].iteritems():
            yaml_list.append((key, value))
    return yaml_list


def dns_resource(name, resource, resource_type, type, suffix=0, extra_dns=0):
    dns_config = {}
    dns_config["name"] = name
    dns_config["resource"] = resource
    dns_config["resource_type"] = resource_type
    dns_config["type"] = type
    if suffix:
        dns_config["suffix"] = suffix
    if extra_dns:
        dns_config["extra_dns"] = 1
    return dns_config


def append_chef_parameters(cloudformation_global_parameters_json, flavour):
    # Read in chef-solo config and append to cloudformation_parameters
    chef_node_jsons = glob.glob("config/%s/chef-solo-config/*.json" % flavour)
    for chef_node_json in chef_node_jsons:
        chef_node_json_name = chef_node_json.rpartition("/")[2].rpartition(".")[0]
        cloudformation_global_parameters_json['Parameters'][chef_node_json_name] = {"Type" : "String"}
    cloudformation_global_parameters_json['Parameters']['SoloRb'] = {"Type" : "String"}
    return cloudformation_global_parameters_json


def append_yaml_parameters(config_area, cloudformation_global_parameters_json):
    yaml = get_global_yaml()
    yaml_list = []
    for key, value in yaml[config_area].iteritems():
        yaml_list.append((key,value))
        cloudformation_global_parameters_json['Parameters'][key] = {"Type" : "String"}
    return cloudformation_global_parameters_json


def get_environment_configuration(configdir, flavour):
    # Read in yaml data
    f = open('%s/%s.yaml' % (os.path.expanduser(configdir), flavour), 'r')
    filedata = f.read()
    config = yaml.safe_load(filedata)
    return config


def get_environment_parameter(env, parameter):
    global_config = get_global_yaml()
    return global_config['defaults'][env][parameter]


def get_cloudformation_secure_bucket(env):
    global_config = get_global_yaml()
    return global_config['defaults'][env]['CloudFormationS3Bucket']


def get_cloudformation_template_bucket(env):
    global_config = get_global_yaml()
    return global_config['defaults'][env]['CloudFormationTemplateBucket']


def get_env_region(env):
    global_config = get_global_yaml()
    return global_config['defaults'][env]['Region']


def set_vpc_id(vpc, network, env, global_config):

    if env in global_config['network']:
        network['VpcId'] = global_config['network'][env]['VpcId']
    else:
        vpc_stack_resource = cloudformation.cloudformation_stack_resource('infra-vpc-' + vpc, vpc, env)
        vpc_resource_detail = vpc_stack_resource['DescribeStackResourceResponse']['DescribeStackResourceResult']['StackResourceDetail']
        network['VpcId'] = vpc_resource_detail['PhysicalResourceId']
    return network


def set_subnets(formation, network, env, global_config, vpc):

    if env in global_config['network']:
        network['subnets'] = global_config['network'][env][formation]['subnets']
    else:
        vpc_stack_resource = cloudformation.cloudformation_stack_resources('infra-vpc-' + vpc, env)
        if vpc_stack_resource:
            subnets = cloudformation.cloudformation_stack_physical_resource_id(vpc_stack_resource, 'AWS::EC2::Subnet')
            network['subnets'] = subnets
    return network



def get_environment_berks_file(configdir, flavour):
    # Read in yaml data
    try:
        f = open('%s/%s.berksfile' % (os.path.expanduser(configdir), flavour), 'r')
    except IOError as e:
        print "Using default berksfile"
        f = open('config/default.berksfile', 'r')
    filedata = f.read()
    return filedata


def write_template(template, template_data):
    print "writing %s.json to templates directory" % template
    if not os.path.exists("templates"):
        os.makedirs("templates")
    f = open('templates/%s.json' % template, 'w')
    file_handle = f.write(template_data)
    f.close()
    return file_handle


def get_berksfile(flavour):
    # Read in berksfile data
    try:
        f = open('config/%s.berksfile' % flavour, 'r')
    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)
        print "Using default berksfile"
        f = open('config/default.berksfile', 'r')
    filedata = f.read()
    return filedata


def find_dictionary_value(d):
    matches = []
    for k, v in d.iteritems():
        if isinstance(v, dict):
            find_dictionary_value(v)
        else:
            if k == "userdata":
                matches.append(v)
    return matches


def list_to_file(list, filename):
    try:
        f = open( filename, 'w')
        for item in list:
            f.write("%s\n" % item)
        f.close()
    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)