__author__ = 'larssonp'
import boto
from boto.ec2 import EC2Connection
import boto.ec2.elb
import ConfigParser
import config
from os.path import expanduser

home = expanduser("~")

Config = ConfigParser.ConfigParser()
Config.read("%s/.ssh/aws.cfg" % home)

try:
    aws_access_key_id = Config.get('aws_keys', 'aws_access_key_id')
except:
    print("No aws_access_key_id defined in aws.cfg")

try:
    aws_secret_access_key = Config.get('aws_keys', 'aws_secret_access_key')
except:
    print("No aws_access_key_id defined in aws.cfg")


def elb_connection(env):
    aws_access_key_id, aws_secret_access_key = config.aws_login(env)

    if aws_access_key_id:
        conn = boto.ec2.elb.connect_to_region("eu-west-1", aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)
    else:
        conn = boto.ec2.elb.connect_to_region("eu-west-1")
    return conn


def get_elb_instances(elb_name, env):
    conn = elb_connection(env)
    elb_instances = conn.describe_instance_health(elb_name)
    return elb_instances
