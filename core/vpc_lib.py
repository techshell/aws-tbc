__author__ = 'pierrelarsson'
import boto.vpc
import core.config as config
from optparse import OptionParser


def vpc_connection(env, region):
    aws_access_key_id, aws_secret_access_key = config.aws_login(env)

    if aws_access_key_id:
        conn = boto.vpc.connect_to_region(region, aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)
    else:
        conn = boto.vpc.connect_to_region(region)
    return conn


def get_all_vpcs(env, region):
    conn = vpc_connection(env, region)
    return conn.get_all_vpcs()