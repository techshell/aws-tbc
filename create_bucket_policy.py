#! /usr/bin/env python
__author__ = 'larssonp'
import core.cloudformation as cloudformation
import core.config as config
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-e", "--env", dest="env",
                  help="env id", metavar="ENV")
parser.add_option("-b", "--bucket", dest="bucket",
                  help="bucket", metavar="NAME")
(options, args) = parser.parse_args()
if not options.env:
    parser.error('Env not given please supply for ex -e prod')
if not options.bucket:
    parser.error('Bucket not given please supply for ex -b my-bucket')

print options.env
print options.bucket

env = options.env
bucket = options.bucket

bucket_config = config.get_bucket_yaml()

cloudformation.create_bucket_policy(env, bucket, bucket_config[env][bucket])