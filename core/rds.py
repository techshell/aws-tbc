__author__ = 'larssonp'
import boto.rds
import ConfigParser
from os.path import expanduser
import config


def rds_connection(env):
    aws_access_key_id, aws_secret_access_key = config.aws_login(env)

    if aws_access_key_id:
        conn = boto.rds.connect_to_region("eu-west-1", aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)
    else:
        conn = boto.rds.connect_to_region('eu-west-1')
    return conn


def get_rds_instance(rds_instance, env):
    conn = rds_connection(env)
    rds_instance = conn.get_all_dbinstances(instance_id=rds_instance)
    return rds_instance


def get_rds_instance_status(rds_instance, env):
    conn = rds_connection(env)
    rds_instance = conn.get_all_dbinstances(instance_id=rds_instance)
    status = rds_instance[0].status
    return status


def get_all_dbinstances():
    conn = rds_connection()
    rds_instances = conn.get_all_dbinstances()
    return rds_instances

def change_security_group(rds_instance, security_group):
    conn = rds_connection()
    mod = conn.modify_dbinstance(rds_instance, vpc_security_groups=[security_group])
    return mod

test = get_all_dbinstances()
print "hello"