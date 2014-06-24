__author__ = 'pierrelarsson'
import boto.s3
import config


def s3_connection(env):
    aws_access_key_id, aws_secret_access_key = config.aws_login(env)

    if aws_access_key_id:
        conn = boto.s3.connect_to_region('eu-west-1',aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)
    else:
        conn = boto.s3.connect_to_region('eu-west-1')
    return conn


def s3_check_key(password, env, bucketname, flavour):
    conn = s3_connection(env)
    bucket = conn.get_bucket(bucketname)
    print "%s/%s-%s" % (env, flavour, password)
    key = bucket.get_key("%s/%s-%s" % (env, flavour, password))
    return key


def s3_upload_key(password, env, bucketname, flavour, new_password):
    conn = s3_connection(env)
    bucket = conn.get_bucket(bucketname)
    key = bucket.new_key("%s/%s-%s" % (env, flavour, password))
    result = key.set_contents_from_string(new_password)
    key.set_canned_acl('authenticated-read')
    return result


def s3_upload_string(env, bucketname, filename, file_contents, path=None):
    conn = s3_connection(env)
    bucket = conn.get_bucket(bucketname)
    key = bucket.new_key("%s/%s" % (path, filename))
    result = key.set_contents_from_string(file_contents)
    set_canned = key.set_canned_acl('public-read')
    #s3url = key.generate_url(500, query_auth=True, force_http=True)
    #s3url = key.generate_url(0, query_auth=False, force_http=True)
    s3url = conn.generate_url(0, query_auth=False, method='GET', force_http=True, bucket=bucketname, key='%s/%s' % (path, filename))

    return s3url


def s3_delete_key(env, bucketname, filename, path):
    conn = s3_connection(env)
    bucket = conn.get_bucket(bucketname)
    key = bucket.get_key("%s/%s" % (path, filename))
    return key.delete()


def s3_bucket_policy(bucketname, bucket_config):
    policy_document={ "Statement": [
		{
			"Sid": "%spolicy" % bucketname,
			"Action": "s3:*",
			"Effect": "Allow",
			"Resource": [
				"arn:aws:s3:::%s" % bucketname,
				"arn:aws:s3:::%s/*" % bucketname
			],
			"Principal": {
				"AWS": bucket_config['principals']
			}
		}
	]
    }
    return policy_document