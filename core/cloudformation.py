__author__ = 'larssonp'
import boto.cloudformation
import yaml
import troposphere_lib
import config
import time
import s3
from troposphere import Template
import os
import re
import threading
import utils
import ec2_connection
import core.elb


def cloudformation_connection(env):
    aws_access_key_id, aws_secret_access_key = config.aws_login(env)

    if aws_access_key_id:
        conn = boto.cloudformation.connect_to_region('eu-west-1',aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)
    else:
        conn = boto.cloudformation.connect_to_region('eu-west-1')
    return conn


def cloudformation_stack_events(stackname, env):
    conn = cloudformation_connection(env)
    events = conn.describe_stack_events(stackname)
    return events


def cloudformation_stack_status(stackname, env):
    conn = cloudformation_connection(env)
    try:
        status = conn.describe_stacks(stackname)
        return status
    except Exception, e:
        error_yaml = yaml.load(e.error_message)
        if error_yaml == ('Stack:%s does not exist' % stackname):
            print error_yaml
            return False
        #print e


def cloudformation_stack_resources(stackname, env, resource_filter=None):
    conn = cloudformation_connection(env)
    resource_list = conn.list_stack_resources(stackname)
    if resource_filter:
        resource_filter_list = []
        for stack_resource in resource_list:
            for filter in resource_filter:
                if stack_resource.logical_resource_id == filter:
                    resource_filter_list.append(stack_resource)
        return resource_filter_list
    else:
        return resource_list


def cloudformation_stack_physical_resource_id(stack_resources, resource_type):
    physical_resource_id_list = []
    for stack_resource in stack_resources:
        if stack_resource.resource_type == resource_type:
            physical_resource_id_list.append(stack_resource.physical_resource_id)
    return physical_resource_id_list


def cloudformation_stack_resource(stackname, logical_resource_id, env):
    conn = cloudformation_connection(env)
    try:
        status = conn.describe_stack_resource(stackname, logical_resource_id)
        return status
    except Exception, e:
        print e


def cloudformation_delete(stackname, env):
    conn = cloudformation_connection(env)
    delete = conn.delete_stack(stackname)
    return delete


def cloudformation_output(stackname, env):
    conn = cloudformation_connection(env)
    stack = conn.describe_stacks(stackname)
    return stack


def update_stack(stack_name, s3url, env, cloudformation_parameters=None, notification_arns=None, tags=None):
    conn = cloudformation_connection(env)
    utils.request_console_confirmation(env)

    try:
        updated_stack = conn.update_stack(stack_name, template_url=s3url,
                                          parameters=cloudformation_parameters, notification_arns=notification_arns, tags=tags)
        print updated_stack
        return updated_stack
    except Exception, e:
        error_yaml = yaml.load(e.error_message)
        if error_yaml['Error']['Message'] == 'No updates are to be performed.':
            print error_yaml['Error']['Message']
            return "created"
        else:
            print error_yaml['Error']['Code']
            print error_yaml['Error']['Message']


def create_stack(stack_name, s3url, env, cloudformation_parameters=None, notification_arns=None, tags=None):
    if notification_arns is None:
        notification_arns = []
    if tags is None:
        tags = {}
    if cloudformation_parameters is None:
        cloudformation_parameters = []

    utils.request_console_confirmation(env)

    conn = cloudformation_connection(env)
    tags["access_key"] = conn.aws_access_key_id
    global stack, e, error_yaml
    try:
        stack = conn.create_stack(stack_name, template_url=s3url,
                                  parameters=cloudformation_parameters, notification_arns=notification_arns, tags=tags)
        print stack
        return stack
    except Exception, e:
        #print e
        error_yaml = yaml.load(e.error_message)
        if error_yaml['Error']['Code'] == 'AlreadyExistsException':
            print error_yaml['Error']['Code']
            print 'Updating stack'
            update_stack(stack_name, s3url, env, cloudformation_parameters, notification_arns, tags)
        else:
            print error_yaml['Error']['Code']
            print error_yaml['Error']['Message']


def list_stack_resources(stack_name, env, nextToken=None):

    conn = cloudformation_connection(env)
    global list_resources, e, error_yaml
    try:
        #  returns list of stack resources
        list_resources = conn.list_stack_resources(stack_name_or_id=stack_name, next_token=nextToken)
        return list_resources
    except Exception, e:
        error_yaml = yaml.load(e.message)
        if error_yaml['Error']['Code'] == 'AlreadyExistsException':
            print error_yaml['Error']['Code']
            print 'List Stack Resources'
        else:
            print error_yaml['Error']['Code']
            print error_yaml['Error']['Message']


def create_ec2_instances(cloudformation_parameters, env_name, ec2_group, ec2_name, params,
                   stack_name, t, network, iam_policies, timestamp, flavour, jira, formation, resource_security_group, env, berks_file):
    t, instance_role = troposphere_lib.add_instance_profile(t, iam_policies, ec2_group["iam_policies"])
    ec2_group["env"] = env_name
    az = "a"
    for count in range(ec2_group["capacity"]):
        # Set unique values for each instance
        count_resource = ec2_name + str(count)
        instance_configuration = {}
        instance_configuration[count_resource] = ec2_group
        instance_configuration[count_resource]["userdata"] = \
            ec2_name + "UserData" + str(count)
        # Add dns configuration
        instance_configuration[count_resource]["dns"] = {}
        suffix = '%s-%s-%s-%s' % (flavour, ec2_name, jira, timestamp)

        dns_resource = count_resource + "Env"
        instance_configuration[count_resource]["dns"][dns_resource] = config.dns_resource({"Ref": "%s" % count_resource}
                                                                    , count_resource, "PrivateIp", "A", suffix)
        dns_resource = count_resource + "Id"
        instance_configuration[count_resource]["dns"][dns_resource] = config.dns_resource({"Ref": "%s" % count_resource}
                                                                    , count_resource, "PrivateIp", "A")
        dns_resource = count_resource + "Dns"
        instance_configuration[count_resource]["dns"][dns_resource] = config.dns_resource(count_resource
                                                                    , count_resource, "PrivateIp", "A")
        if "extra_dns" in instance_configuration[count_resource]:
            dns_resource = count_resource + "ExtraDns"
            instance_configuration[count_resource]["dns"][dns_resource] = config.dns_resource(instance_configuration[count_resource]["extra_dns"]
                                                                    ,count_resource, "PrivateIp", "A", False, True)

        # Configure userdata, chef and create instances
        cloudformation_parameters = config.populate_userdata(instance_configuration[count_resource], "ec2", stack_name,
                                                             cloudformation_parameters, count_resource)
        t = troposphere_lib.create_instance(t, params, instance_configuration[count_resource], count_resource,
                                            instance_role, network, timestamp, flavour, jira, ec2_name, az, formation, resource_security_group, env, berks_file)
        t = troposphere_lib.create_dns_record(t, params, instance_configuration[count_resource])
        az = chr(ord(az) + 1)
    return cloudformation_parameters, t


def add_chef_env(chef, jira, stack_name, zone, env, flavour, env_params=None, db_app_user=None):
    if env_params is None:
        env_params = {}

    global_config = config.get_global_yaml()
    chef_default_parameters = global_config['defaults'][env]['chef']

    for chef_default_section in chef_default_parameters:
        chef[chef_default_section] = chef_default_parameters[chef_default_section]

    if "env" not in chef:
        chef["env"] = {}
    chef["env"]["name"] = jira
    chef["env"]["zone"] = zone
    chef["env"]["stack"] = {}
    chef["env"]["stack"]["name"] = stack_name
    chef["env"]["stack"]["gluster"] = flavour + "-" + jira + "-dat"
    chef["env"]["stack"]["mysql"] = flavour + "-" + jira + "-db"
    chef["env"]["account"] = env

    if db_app_user:
        chef["env"]["app_username"] = db_app_user
        chef["env"]["db_passwd"] = {"Ref": "DbPasswd"}
        chef["env"]["app_passwd"] = {"Ref": "AppPasswd"}
    if env in env_params:
        chef["env"]["params"] = {}
        for params in env_params[env]:
            chef["env"]["params"][params] = env_params[env][params]
    if "postfix" in chef:
        #print "Writing SES Credentials.\n"
        #chef["postfix"]["main"]["relayhost"] = {"Ref": "SesHost"}
        chef["postfix"]["sasl"] = {}
        chef["postfix"]["sasl"]["smtp_sasl_user_name"] = {"Ref": "SesUser"}
        chef["postfix"]["sasl"]["smtp_sasl_passwd"] = {"Ref": "SesPass"}
    return chef


def create_formation_security_group(flavour, jira, timestamp, network, env):
    name_tag = "sg%s%s%s" % (flavour, jira, timestamp)
    name_tag = name_tag.replace("-", "")
    stack_name = "sg-%s-%s" % (flavour, jira)
    stack = cloudformation_stack_status(stack_name, env)
    if stack:
        if (stack[0].stack_status == 'CREATE_COMPLETE') or (stack[0].stack_status == 'UPDATE_COMPLETE'):
            print "%s already created" % stack_name
            stack_resource = cloudformation_stack_resource(stack_name, name_tag, env)
            stack_resource_detail = stack_resource['DescribeStackResourceResponse']['DescribeStackResourceResult']['StackResourceDetail']
            return stack_resource_detail['PhysicalResourceId']
    else:
        t = Template()
        t, resource_security_group = troposphere_lib.create_resource_security_group(name_tag, t, network['VpcId'])
        s3url = s3.s3_upload_string(env, 'telegraph-cloudformation-templates', stack_name, t.to_json(), env)
        create_stack(stack_name, s3url, env, [], [], {"timestamp": timestamp, "Billing": flavour})
        s3.s3_delete_key(env,'telegraph-cloudformation-templates', stack_name, env)
        time.sleep(1)
        stack = cloudformation_stack_status(stack_name, env)
        print stack[0].stack_status
        while stack[0].stack_status != "CREATE_COMPLETE":
            stack = cloudformation_stack_status(stack_name, env)
            print "status is %s" % stack[0].stack_status
            time.sleep(5)
            print "Creating cloudformation %s" % stack_name
        print stack[0].stack_status
        stack_resource = cloudformation_stack_resource(stack_name, name_tag, env)
        stack_resource_detail = stack_resource['DescribeStackResourceResponse']['DescribeStackResourceResult']['StackResourceDetail']
        return stack_resource_detail['PhysicalResourceId']


def create_cloudformation_template(environment_configuration, jira, env, flavour, timestamp, berks_file, status=None):
    global_config = config.get_global_yaml()
    #Set the ssh key for created instances
    zone = global_config['defaults'][env]['HostedZone']
    environment_configuration["network"] = global_config['network'][env]
    environment_configuration["iam_policies"] = global_config['iam_policies']

    if env == "preprod":
        password_ref = jira + '-' + flavour
    else:
        password_ref = flavour

    if "dbpasswd" in environment_configuration:
        db_passwd = config.get_db_passwd(env, 'db_passwd', environment_configuration["dbpasswd"][env], 'rds-secure')
    else:
        db_passwd = config.get_db_passwd(env, 'db_passwd', password_ref, 'rds-secure')

    app_passwd = config.get_db_passwd(env, 'app_passwd', password_ref, 'rds-secure')

    if "seshost" in global_config['defaults']:
        ses_host = config.get_db_passwd(env, 'ses_host', global_config['defaults']["seshost"][env], 'rds-secure')
    else:
        ses_host = config.get_db_passwd(env, 'ses_host', password_ref, 'rds-secure')

    if "sesuser" in global_config['defaults']:
        ses_user = config.get_db_passwd(env, 'ses_user', global_config['defaults']["sesuser"][env], 'rds-secure')
    else:
        ses_user = config.get_db_passwd(env, 'ses_user', password_ref, 'rds-secure')

    if "sespass" in global_config['defaults']:
        ses_pass = config.get_db_passwd(env, 'ses_pass', global_config['defaults']["sespass"][env], 'rds-secure')
    else:
        ses_passwd = config.get_db_passwd(env, 'ses_pass', password_ref, 'rds-secure')

    formation_security_group = create_formation_security_group(flavour, jira, timestamp, environment_configuration["network"], env)

    stacks = []

    for formation in environment_configuration["formations"]:
        # Yaml data as list
        cloudformation_parameters = config.get_yaml_as_list('defaults', env)
        create_stack_arn = [global_config['defaults'][env]['SnsCreateStack']]
        t = Template()
        t, params = troposphere_lib.get_template_parameters(t, env)
        stack_name = "%s-%s-%s" % (flavour, jira, formation)

        cloudformation_parameters.append(('KeyName', environment_configuration['KeyName']))
        t, params = troposphere_lib.add_parameter(t, params, 'KeyName')

        cloudformation_parameters.append(('EnvironmentSecurityGroupId', formation_security_group))
        t, params = troposphere_lib.add_parameter(t, params, 'EnvironmentSecurityGroupId')

        cloudformation_parameters.append(('DbPasswd', db_passwd))
        t, params = troposphere_lib.add_db_passwd(t, params, 'DbPasswd')

        cloudformation_parameters.append(('AppPasswd', app_passwd))
        t, params = troposphere_lib.add_db_passwd(t, params, 'AppPasswd')

        cloudformation_parameters.append(('SesHost', ses_host))
        t, params = troposphere_lib.add_db_passwd(t, params, 'SesHost')

        cloudformation_parameters.append(('SesUser', ses_user))
        t, params = troposphere_lib.add_db_passwd(t, params, 'SesUser')

        cloudformation_parameters.append(('SesPass', ses_pass))
        t, params = troposphere_lib.add_db_passwd(t, params, 'SesPass')

        print "Deploying stack formation %s in stack %s" % (formation, stack_name)

        # For some reason passing the AZ list directly as a reference fails. This is a workaround.
        global az_list
        for item in cloudformation_parameters:
            if item[0] == "AvailabilityZones":
                az_list = item[1]

        t.add_description(environment_configuration["formations"][formation]["description"])
        for resource in environment_configuration["formations"][formation]:
            if resource == "ec2":
                for ec2_instance in environment_configuration["formations"][formation][resource]:
                    name_tag = "%s%s%s%s" % (flavour, ec2_instance, jira, timestamp)
                    name_tag = name_tag.replace("-", "")
                    ec2_object = environment_configuration["formations"][formation][resource][ec2_instance]

                    t, resource_security_group = troposphere_lib.create_resource_security_group(name_tag, t, environment_configuration["network"][formation]['VpcId'])

                    if "env" in environment_configuration:
                        ec2_object["chef"] = \
                            add_chef_env(ec2_object["chef"],
                                         jira, stack_name, zone, env, flavour, environment_configuration["env"])
                    elif "app_username" in ec2_object:
                        ec2_object["chef"] = \
                            add_chef_env(ec2_object["chef"],
                                         jira, stack_name, zone, env, flavour, None, ec2_object["app_username"])
                    else:
                        ec2_object["chef"] = \
                            add_chef_env(ec2_object["chef"],
                                         jira, stack_name, zone, env, flavour)
                    cloudformation_parameters, t = create_ec2_instances(cloudformation_parameters, jira,
                                              ec2_object, ec2_instance, params, stack_name, t,
                                              environment_configuration["network"][formation],
                                              environment_configuration["iam_policies"], timestamp, flavour, jira, formation, env, berks_file, resource_security_group)
            elif resource == "autoscaling_groups":
                for autoscaling_group in environment_configuration["formations"][formation][resource]:
                    name_tag = "%s%s%s%s" % (flavour, autoscaling_group, jira, timestamp)
                    name_tag = name_tag.replace("-", "")
                    autoscaling_object = environment_configuration["formations"][formation][resource][autoscaling_group]

                    t, resource_security_group = troposphere_lib.create_resource_security_group(name_tag, t, environment_configuration["network"][formation]['VpcId'])

                    t, instance_role = troposphere_lib.add_instance_profile(t, environment_configuration["iam_policies"],
                        autoscaling_object["launchconfig"]["iam_policies"], autoscaling_group)
                    if "env" in environment_configuration:
                        autoscaling_object["launchconfig"]["chef"] = \
                            add_chef_env(autoscaling_object["launchconfig"]["chef"],
                                         jira, stack_name, zone, env, flavour, environment_configuration["env"],
                                         autoscaling_object["app_username"])
                    else:
                        autoscaling_object["launchconfig"]["chef"] = \
                            add_chef_env(autoscaling_object["launchconfig"]["chef"], jira, stack_name, zone, env, flavour, None,
                                         autoscaling_object["app_username"])
                    autoscaling_configuration = environment_configuration["formations"][formation][resource]

                    autoscaling_object["launchconfig"]["userdata"] = autoscaling_group + "UserData"
                    cloudformation_parameters = config.populate_userdata(autoscaling_configuration[autoscaling_group],
                                                                         "launchconfig", stack_name, cloudformation_parameters, autoscaling_group)
                    autoscaling_configuration[autoscaling_group]["env"] = jira
                    autoscaling_configuration[autoscaling_group]["az"] = az_list

                    dns_resource = autoscaling_group + "Env"
                    suffix = "%s-%s-%s-%s" % (flavour, "elb", jira, timestamp)
                    autoscaling_configuration[autoscaling_group]["dns"][dns_resource]\
                        = config.dns_resource("elb%s" % autoscaling_group, autoscaling_group + "LB", "DNSName", "CNAME", suffix)

                    t = troposphere_lib.create_autoscaling_group(t, params, autoscaling_configuration[autoscaling_group]
                                                        ,autoscaling_group, instance_role,
                                                        environment_configuration["network"][formation],
                                                        environment_configuration["network"]["pub"], timestamp, flavour, jira, env, berks_file, resource_security_group)
            elif resource == "rds":
                for rds_instance in environment_configuration["formations"][formation][resource]:
                    rds_object = environment_configuration["formations"][formation][resource][rds_instance]
                    rds_object["env"] = jira

                    suffix = "%s-%s-%s-%s" % (flavour, resource, jira, timestamp)
                    if "extra_dns" in rds_object:
                        dns_resource = rds_instance + "ExtraDns"
                        rds_object["dns"][dns_resource] = config.dns_resource(rds_object["extra_dns"]
                                                                                ,rds_instance, "Endpoint.Address", "CNAME", False, True)
                    dns_resource = rds_instance + "Env"
                    rds_object["dns"][dns_resource]\
                            = config.dns_resource(rds_instance , rds_instance, "Endpoint.Address", "CNAME", suffix)
                    t = troposphere_lib.create_rds_instance(t, params, rds_object, rds_instance,
                                                        environment_configuration["db_parameters"],
                                                        environment_configuration["network"]["db"], timestamp, flavour, jira, env)
            elif resource == "elasticache":
                for elasticache_instance in environment_configuration["formations"][formation][resource]:
                    environment_configuration["formations"][formation][resource][elasticache_instance]["env"] = jira
                    dns_resource = elasticache_instance + "Env"
                    suffix = "%s-%s-%s-%s" % (flavour, 'ec', jira, timestamp)
                    environment_configuration["formations"][formation][resource][elasticache_instance]["dns"][dns_resource]\
                        = config.dns_resource(elasticache_instance , elasticache_instance, "ConfigurationEndpoint.Address", "CNAME", suffix)
                    t = troposphere_lib.create_elasticache(t, params,
                                                            environment_configuration["formations"][formation][resource][elasticache_instance], elasticache_instance,
                                                        environment_configuration["network"][formation],
                                                        environment_configuration["network"]["app"])

        #print t.to_json()
        config.write_template(stack_name, t.to_json())
        s3url = s3.s3_upload_string(env, 'telegraph-cloudformation-templates', stack_name, t.to_json(), env)
        tags = {"timestamp": timestamp, "Billing": flavour}
        stack_formation = [stack_name, s3url, env, cloudformation_parameters, create_stack_arn, tags, status]
        stacks.append(stack_formation)
    create_stacks(stacks)
    if env == 'prod':
        create_release_log(env, flavour, timestamp, jira, tags)


def create_security_groups(security_groups, env, name, vpcid):
    t = Template()

    t, security_group_ref = troposphere_lib.create_security_group(name, security_groups[name], env, vpcid, t)
    stack_name = "infra-security-group-" + name
    s3url = s3.s3_upload_string(env, 'telegraph-cloudformation-templates', stack_name, t.to_json(), env)
    create_stack(stack_name, s3url, env)


def create_bucket_policy(env, bucket, bucket_config):
    policy_document = s3.s3_bucket_policy(bucket, bucket_config)
    t = troposphere_lib.s3_bucket_policy(bucket, policy_document)
    stack_name = "infra-bucket-policy-" + bucket
    s3url = s3.s3_upload_string(env, 'telegraph-cloudformation-templates', stack_name, t.to_json(), env)
    create_stack(stack_name, s3url, env)


def create_static_dns_entries(environment_configuration, env, name):

    t = Template()

    t, params = troposphere_lib.get_template_parameters(t, env)

    for resource_config in environment_configuration["resources"]:
        instance_configuration = {}
        instance_configuration = environment_configuration["resources"][resource_config]
        instance_configuration["env"] = env  #required by existing function
        t = troposphere_lib.create_dns_record(t, params, instance_configuration)

    #build stack and upload to s3.
    stack_name = "infra-static-dns-entries-" + name
    s3url = s3.s3_upload_string(env, 'telegraph-cloudformation-templates', stack_name, t.to_json(), env)

    #create stack from regional s3 as url.
    create_stack(stack_name, s3url, env)


def evaluate_stack_resources_status(stack_name, env):

    global list_stack_resources, launch_status

    launch_status = 'IN_PROGRESS'

    while launch_status == 'IN_PROGRESS':
        list_stack_resources = cloudformation_stack_resources(stack_name,env)

        # check status of each resource
        for member in list_stack_resources:
            resource_status = member.resource_status
            launch_status = resource_status  # so if all is created proceeds.
            # check regex.
            b = re.compile("FAILED")
            if b.search(resource_status):
                # will exit
                # TODO:View the stack events to see any associated error messages
                print "stack resource HAS FAILED due to %s" % member.resource_status_reason
                break

            a = re.compile("IN_PROGRESS")
            if a.search(resource_status):
                launch_status = "IN_PROGRESS"
                print "stack resources are %s..." % launch_status
                time.sleep(10)
                break  # refresh object...
        # TODO: some resource failed.

    print "stack resources are %s..." % launch_status

    return launch_status


# deleted resources will throw a 400 error when is complete.
def evaluate_deleted_stack_resources_status(stack_name, env):

    global list_stack_resources, launch_status
    launch_status = 'IN_PROGRESS'

    try:
        while launch_status.find("(IN_PROGRESS|CREATE|UPDATE)"):
            list_stack_resources = cloudformation_stack_resources(stack_name,env)

            # check status of each resource
            for member in list_stack_resources:
                resource_status = member.resource_status
                launch_status = resource_status  # so if all is created proceeds.
                # check regex.
                c = re.compile("(CREATE|UPDATE)")
                if c.search(resource_status):
                    # will exit
                    print "stack resource deletion in progress... "
                    time.sleep(10)
                    break
                #resources shared.
                b = re.compile("DELETE_FAILED")
                if b.search(resource_status):
                    launch_status = "DELETE_FAILED"
                    # will exit
                    print "stack shared resource HAS FAILED to delete due to %s" % member.resource_status_reason
                    break

                a = re.compile("IN_PROGRESS")
                if a.search(resource_status):
                    launch_status = "IN_PROGRESS"
                    print "stack resource deletion in progress..."
                    time.sleep(10)
                    break
    except Exception, e:
        #print e
        error_yaml = yaml.load(e.error_message)
        error_gone_token = "Stack with name %s does not exist" % stack_name
        if error_yaml == error_gone_token:
            print error_yaml
            launch_status = 'DONE'
        else:
            print error_yaml
            launch_status = 'DELETE_FAILED'
            print "stack resource deletion has failed %s..." % error_yaml
            return launch_status

    print "stack resources deletion completed with status %s" % launch_status
    return launch_status


def delete_stack(stack_name, env):
    print "Deleting %s" % stack_name
    delete = cloudformation_delete(stack_name, env)
    print delete
    evaluate_deleted_stack_resources_status(stack_name, env)


def delete_stacks(environment_configuration, env, flavour, jira):

    utils.request_console_confirmation(env)
    #join the threads outside...
    threads = []
    for formation in environment_configuration["formations"]:
        stack_name = "%s-%s-%s" % (flavour, jira, formation)
        process_stack = threading.Thread(group=None, name=stack_name, target=delete_stack, args=[stack_name, env])
        threads.append(process_stack)
        process_stack.start()
        time.sleep(1)

    #join all threads of a given name pattern so we wait until all of them are done.
    for process_stack in threads:
            process_stack.join()

    #wait for all stack deleted to continue.
    print "stack formations deleted"


def create_stack_formation(stack_name, s3url, env, cloudformation_parameters, create_stack_arn, tags, status):
    create_stack(stack_name, s3url, env, cloudformation_parameters, create_stack_arn, tags)
    if status != None:
        evaluate_stack_resources_status(stack_name, env)
    s3.s3_delete_key(env, 'telegraph-cloudformation-templates', stack_name, env)


def create_stacks(stacks):

    threads = []
    for stack in stacks:
        stack_name = stack[0]
        process_stack = threading.Thread(group=None, name=stack_name, target=create_stack_formation, args=stack)
        threads.append(process_stack)
        process_stack.start()
        time.sleep(4)

    for process_stack in threads:
            process_stack.join()

    #wait for all stacks to build before continuing
    print "stack formations created"


def create_release_log(env, flavour, timestamp, jira, tags):

    #read default-default-release.yaml
    default_release_yaml = "config/default-release.yaml"
    if os.path.exists(default_release_yaml):
        fr = open(default_release_yaml, 'r')
        release_yaml_data = fr.read()
        release_yaml_config = yaml.load(release_yaml_data)
        fr.close()

    flavour_release_yaml = "config/%s-release.yaml" % flavour
    if os.path.exists(flavour_release_yaml):
        print "found %s" % flavour_release_yaml
    else:
        print "generating %s" % flavour_release_yaml
    git_commit_refs = []

    #place in function
    #identify berks_file_path
    berks_file_path ="config/%s.berksfile" % flavour
    default_berks_path = "config/default.berksfile"
    if os.path.exists(berks_file_path):
        fb = open(berks_file_path, 'r')
        berks_data = fb.read()
    else:
        berks_file_path = default_berks_path
        fb = open(default_berks_path, 'r')
        berks_data = fb.read()

    lines = berks_data.split(os.linesep)

    if berks_data != "":
        for line in lines:
            elements = line.split(',')
            obj = []
            #used this approach to help reading the file. can jsonize.
            #note yaml editing is not meant to occur at runtime so all content is injected on a field.
            for element in elements:
                if element.find('cookbook') == 0:
                    cookbook_pos = element.find('cookbook')+10
                    cookbook = element[cookbook_pos:-1]
                    obj.append("%s:" % cookbook)

                elif element.find(' => ') > 0:
                    obj_type = element[2:element.find('=')]
                    obj_pos_from = element.find(' => ')+5
                    obj_value = element[obj_pos_from:-1]
                    obj.append("%s:%s" % (obj_type, obj_value))

            git_commit_refs.append(obj)
    else:
        print "no berks file found for %s!! build will pull from latest on all cookbooks" % flavour

    #log release timestamp
    if release_yaml_config.get('release', {}) is not None:
        release_yaml_config['release']['jira'] = jira
        release_yaml_config['release']['flavour'] = flavour
        release_yaml_config['release']['env'] = env
        release_yaml_config['release']['timestamp'] = str(timestamp)
        release_yaml_config['release']['berks']['berks_file'] = berks_file_path
        release_yaml_config['release']['berks']['tags'] = git_commit_refs
        #release_yaml_config['release']['berks']['cookbooks_versions'] = berks_json_config #dump berks_data
        if tags is not None:
            release_yaml_config['release']['tags'] = tags
    #save default-release.yaml
    f = open(flavour_release_yaml, 'w')
    f.write(yaml.dump(release_yaml_config, default_flow_style=None, default_style=''))
    f.close()


def deploy_debian_package(jira, env, package, target_elbs, flavour, environment_configuration):
    for formation in environment_configuration["formations"]:
        stack = "%s-%s-%s" % (flavour, jira, formation)
        stack_ip_list = get_instance_ip_list_from_stack(stack, env, target_elbs)
    for target_elb in target_elbs:
        get_elb_stack_names(target_elbs, jira, flavour)
    stack_ip_list = get_instance_ip_list_from_stack(stack, env, target_elbs)
    for instance in stack_ip_list:
        os.system("scp %s build@%s:" % (package, instance))
        os.system("ssh build@%s sudo /usr/bin/dpkg -i %s" % (instance, package))
        os.system("ssh build@%s rm %s" % (instance, package))


def get_elb_stack_names(target_elbs, jira, flavour):
    stack_list = []
    for target_elb in target_elbs:
        print "t"


def get_instance_ip_list_from_stack(stack, env, target_elbs):
    stack_resources = cloudformation_stack_resources(stack, env, target_elbs)
    if stack_resources:
        stack_elbs = cloudformation_stack_physical_resource_id(stack_resources, 'AWS::ElasticLoadBalancing::LoadBalancer')
        instance_list = []
        for elb in stack_elbs:
            instance = core.elb.get_elb_instances(elb, env)
            for instance_result in instance:
                print 'Instance %s is %s' % (instance_result.instance_id, instance_result.state)
                instance_list.append(instance_result.instance_id)

        conn = ec2_connection.ec2_connection(env)

        instances = conn.get_all_instances(instance_ids=instance_list)

        instance_list = []
        for instance_az in instances:
            for instance in instance_az.instances:
                ipaddress = instance.private_ip_address
                instance_list.append(ipaddress)
        return instance_list
    else:
        print "No Resources"
