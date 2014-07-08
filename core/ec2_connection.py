__author__ = 'larssonp'
import boto
from boto.ec2 import EC2Connection
import config


def ec2_connection(env):
    aws_access_key_id, aws_secret_access_key = config.aws_login(env)
    region = config.get_env_region(env)

    if aws_access_key_id:
        conn = boto.ec2.connect_to_region(region, aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)
    else:
        conn = boto.ec2.connect_to_region(region)
    return conn
