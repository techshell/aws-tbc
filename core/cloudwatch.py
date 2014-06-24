__author__ = 'larssonp'

import boto.ec2.cloudwatch as cloudwatch
import ConfigParser
from os.path import expanduser
from datetime import datetime
from datetime import timedelta

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

conn = cloudwatch.CloudWatchConnection(aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key,region='eu-west-1')
d = timedelta(days=-1)
current_time = datetime.now()
yesterday = current_time - d

stats = conn.get_metric_statistics(period=3600, start_time=current_time,
                                 end_time=yesterday, metric_name="FreeStorageSpace",
                                 namespace="AWS/RDS", statistics=["Sum"], dimensions={"DBInstanceIdentifier":"jm134009lt55s9s"})

print stats

print "hello"