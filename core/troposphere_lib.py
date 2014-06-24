__author__ = 'larssonp'
from troposphere import Ref, Template, Parameter, Join, GetAtt, Base64, Tags, Output
import troposphere.ec2 as ec2
from troposphere.route53 import RecordSetType
import troposphere.elasticloadbalancing as elb
import troposphere.autoscaling as autoscaling
import troposphere.cloudwatch as cloudwatch
import troposphere.rds as rds
import troposphere.iam as iam
import troposphere.sqs as sqs
import troposphere.sns as sns
import troposphere.s3 as s3
import troposphere.elasticache as elasticache
import securitygroups
import config
import packer

def get_template_parameters(t, env):
    global params, cloudformation_parameters, parameter, key
    params = {}
    cloudformation_parameters = config.get_yaml_as_list('defaults', env)
    for parameter, key in cloudformation_parameters:
        params[parameter] = t.add_parameter(Parameter(
            parameter,
            Type="String"
        ))
    return t, params


def add_db_passwd(t, params, password):
    params[password] = t.add_parameter(Parameter(
            password,
                Type="String",
                NoEcho=True
            ))
    return t, params


def add_parameter(t, params, parameter):
    params[parameter] = t.add_parameter(Parameter(
            parameter,
                Type="String",
            ))
    return t, params


def create_tags(instance_object, name_tag, env, propogate_at_launch=False):
    tag_list = []
    if propogate_at_launch:
        tag_list.append(autoscaling.Tag("Name", name_tag, propogate="true"))
    else:
        tag_list.append(ec2.Tag("Name", name_tag))

    for env_tag in instance_object["tags"]['environment_tags'][env]:
        if propogate_at_launch:
            tag_list.append(autoscaling.Tag(env_tag, instance_object["tags"]['environment_tags'][env][env_tag], propogate="true"))
        else:
            tag_list.append(ec2.Tag(env_tag, instance_object["tags"]['environment_tags'][env][env_tag]))
    return tag_list


def create_instance(t, params, instance_object, instance_name, instance_role, network, timestamp, flavour, jira, ec2_name, az, formation, env, berks_file, resource_security_group=None):
    metadata = create_metadata(instance_object["chef"])
    metadata = add_berksfile(metadata, berks_file)
    secgroup_list = [network['SecurityGroupIds'], Ref(params['EnvironmentSecurityGroupId']), Ref(params['MonitoringSecurityGroup'])]

    if resource_security_group:
        secgroup_list.append(Ref(resource_security_group))

    if 'security_groups' in instance_object:
        if env in instance_object['security_groups']:
            for security_group in instance_object['security_groups'][env]:
                secgroup_list.append(securitygroups.security_group_id(security_group, env))

    # Add userdata parameter
    params[instance_object["userdata"]] = t.add_parameter(Parameter(
        instance_object["userdata"],
        Type="String",
    ))

    name_tag = "%s-%s-%s-%s" % (flavour, ec2_name, jira, timestamp)

    tag_list = create_tags(instance_object, name_tag, env)

    instance = ec2.Instance(instance_name,
                        Metadata=metadata,
                        ImageId=get_ami(instance_object, formation),
                        SecurityGroupIds=secgroup_list,
                        SubnetId=network['SubnetEuWest1%s' % az],
                        UserData=Base64(Ref(params[instance_object["userdata"]])),
                        IamInstanceProfile=Ref(instance_role),
                        InstanceType=instance_object["instance_type"],
                        Monitoring=1,
                        KeyName=Ref(params['KeyName']), Tags=tag_list)

    if "ebs_optimized" in instance_object:
        if instance_object["ebs_optimized"]:
            instance.EbsOptimized = instance_object["ebs_optimized"]

    if "block_device_mappings" in instance_object:
        block_device_list = []
        for block_device in instance_object["block_device_mappings"]:
            ebs_block = ec2.EBSBlockDevice(
                block_device,
                DeleteOnTermination=instance_object["block_device_mappings"][block_device]["delete_on_termination"],
                VolumeSize=instance_object["block_device_mappings"][block_device]["volume_size"]
            )
            if "iops" in instance_object["block_device_mappings"][block_device]:
                ebs_block.Iops = instance_object["block_device_mappings"][block_device]["iops"]

            if "snapshot_id" in instance_object["block_device_mappings"][block_device]:
                ebs_block.SnapshotId = instance_object["block_device_mappings"][block_device]["snapshot_id"][env]
            block_device_mapping = ec2.BlockDeviceMapping(
                block_device,
                DeviceName=instance_object["block_device_mappings"][block_device]["device_name"],
                Ebs=ebs_block
            )
            block_device_list.append(block_device_mapping)
        instance.BlockDeviceMappings = block_device_list

    t.add_output([
        Output(
            instance_name,
            Description="Ip address of instance",
            Value=GetAtt(instance_name, "PrivateIp"),
        ),
    ])
    if formation == "pub":
        eip = ec2.EIP(
            instance_name + "EIP",
            InstanceId=Ref(instance),
            Domain='vpc',
        )
        associate_eip = ec2.EIPAssociation(
            instance_name + "EIPAssociation",
            AllocationId=GetAtt(instance_name + "EIP", "AllocationId"),
            InstanceId=Ref(instance),
        )
        t.add_resource(eip)
        t.add_resource(associate_eip)
    t.add_resource(instance)
    return t


def get_ami(instance_object, formation):

    value_ref = instance_object["ami"]
    #binary compatible - string value.
    if type(value_ref) == str:
        return value_ref
    else:
        # get from packer.
        flavour = instance_object["ami"]["flavour"]
        return packer.get_packer_ami(flavour, formation)


def create_elb(t, params, elb_instance, elb_name, network, env):

    secgroup_list = [network['SecurityGroupIds'], Ref(params['EnvironmentSecurityGroupId']), Ref(params['MonitoringSecurityGroup'])]

    listener_list = []
    if "listeners" in elb_instance:
        for listener in elb_instance["listeners"]:
            listener_list.append(
                elb.Listener(
                    LoadBalancerPort=elb_instance["listeners"][listener]["elb_port"],
                    InstancePort=elb_instance["listeners"][listener]["instance_port"],
                    Protocol=elb_instance["listeners"][listener]["protocol"],
                )
            )
    else:
        listener_list.append(
            elb.Listener(
                LoadBalancerPort=elb_instance["elb_port"],
                InstancePort=elb_instance["instance_port"],
                Protocol=elb_instance["protocol"],
            )
        )

    if 'security_groups' in elb_instance:
        for security_group in elb_instance['security_groups'][env]:
            secgroup_list.append(securitygroups.security_group_id(security_group, env))

    if env == 'prod':
        if 'public_security_group' in elb_instance:
            public_security_group = {}
            public_security_group[elb_name] = {}
            public_security_group[elb_name]['cidr'] = ['0.0.0.0/0']
            public_security_group[elb_name]['config'] = {}
            public_security_group[elb_name]['config']['protocol'] = 'tcp'
            public_security_group[elb_name]['config']['from_port'] = '80'
            public_security_group[elb_name]['config']['to_port'] = '80'
            public_security_group[elb_name]['config']['description'] = 'public security group'

            t, security_group_ref = create_security_group("sg%s" % elb_name, public_security_group, env, network['VpcId'], t)
            secgroup_list.append(Ref(security_group_ref))

    elb_load_balancer = elb.LoadBalancer(
                elb_name,
                Subnets=[network['SubnetEuWest1a'], network['SubnetEuWest1b']],
                SecurityGroups=secgroup_list,
                CrossZone=True,
                Listeners=listener_list,
                HealthCheck=elb.HealthCheck(
                    Target=elb_instance["healthcheckpath"],
                    HealthyThreshold="2",
                    UnhealthyThreshold="5",
                    Interval="10",
                    Timeout="5",
                )
    )

    if "scheme" in elb_instance:
        elb_load_balancer.Scheme = elb_instance["scheme"]

    template_lb = t.add_resource(elb_load_balancer)

    return t, template_lb


def create_metadata(chef):
    solorb = """
    log_level :debug
    log_location STDOUT
    data_bag_path "/var/chef-solo/cookbooks/base/data_bags"
    file_cache_path "/var/chef-solo"
    cookbook_path "/var/chef-solo/cookbooks"
    json_attribs "/etc/chef/node.json"
    log_location "/var/log/chef-solo.log"
    """
    metadata = {
    "AWS::CloudFormation::Init": {
            "configSets" : {
                "ascending" : [ "config" , "executables" ]
            },
            "config": {
                "files": {
                    "/etc/chef/Berksfile": {
                        "content": "",
                        "mode": "000644",
                        "owner": "root",
                        "group": "root"
                    },
                    "/etc/chef/solo.rb": {
                        "content": solorb,
                        "mode": "000644",
                        "owner": "root",
                        "group": "root"
                    },
                    "/etc/chef/node.json": {
                        "content": "",
                        "mode": "000600",
                        "owner": "root",
                        "group": "root"
                    }
                }
            },
            "executables": {
                "commands": {
                    "berkshelf" : {
                        "command" : "/usr/local/bin/berks install --path /var/chef-solo/cookbooks/",
                        "cwd" : "/etc/chef"
                    }
                }
            },
        }
    }
    global_config = config.get_global_yaml()
    chef_run_with_defaults = global_config['defaults']['chef']['run_list']
    for run_list in chef['run_list']:
        chef_run_with_defaults.append(run_list)
    chef['run_list'] = chef_run_with_defaults
    metadata["AWS::CloudFormation::Init"]["config"]["files"]["/etc/chef/node.json"]["content"] = chef
    return metadata


def add_berksfile(metadata, berks_file):
    metadata["AWS::CloudFormation::Init"]["config"]["files"]["/etc/chef/Berksfile"]["content"] = berks_file
    return metadata


def add_instance_profile(t, default_iam_policies, iam_policies, autoscaling_group=0):
    policy_list = []
    for policy in iam_policies:
        policy_list.append(
            iam.Policy(
                PolicyName=policy,
                PolicyDocument={ "Statement":
                    default_iam_policies[policy]["Statement"],
                }
            )

        )
    InstanceRole=t.add_resource(iam.Role(
        "InstanceRole%s" % autoscaling_group,
        Path="/",
        AssumeRolePolicyDocument={"Statement": [{
                                    "Effect": "Allow",
                                    "Principal": {
                                        "Service": ["ec2.amazonaws.com"]
                                    },
                                    "Action": ["sts:AssumeRole"]
                                }]},
        Policies=policy_list
        ,

    ))
    instance_role = t.add_resource(iam.InstanceProfile(
        "InstanceProfile%s" % autoscaling_group,
        Path="/",
        Roles=[
            Ref(InstanceRole)
        ]
    ))
    return t, instance_role


def s3_bucket_policy(bucketname, policydocument):
    policy_name = bucketname.replace("-", "")
    t = Template()
    t.add_resource(s3.BucketPolicy(
     policy_name,
     Bucket=bucketname,
     PolicyDocument=policydocument
    ))
    return t


def create_autoscaling_group(t, params, autoscaling_object, autoscaling_name, instance_role, network, elb_network, timestamp, flavour, jira, env, berks_file, resource_security_group=None):
    elb_name = autoscaling_name + "LB"
    launch_config_name = autoscaling_name + "LaunchConfig"
    metadata = create_metadata(autoscaling_object["launchconfig"]["chef"])
    metadata = add_berksfile(metadata, berks_file)
    secgroup_list = [network['SecurityGroupIds'], Ref(params['EnvironmentSecurityGroupId']), Ref(params['MonitoringSecurityGroup'])]

    if resource_security_group:
        secgroup_list.append(Ref(resource_security_group))

    if 'security_groups' in autoscaling_object:
        for security_group in autoscaling_object['security_groups'][env]:
            secgroup_list.append(securitygroups.security_group_id(security_group, env))

    name_tag = "%s-%s-%s-%s" % (flavour, autoscaling_name, jira, timestamp)

    tag_list = create_tags(autoscaling_object, name_tag, env, True)

    # Add userdata parameter
    params[autoscaling_object["launchconfig"]["userdata"]] = t.add_parameter(Parameter(
        autoscaling_object["launchconfig"]["userdata"],
        Type="String",
    ))

    t, elb_ref = create_elb(t, params, autoscaling_object["elb"], elb_name, elb_network, env)
    launch_configuration = t.add_resource(autoscaling.LaunchConfiguration(
        launch_config_name,
        Metadata=metadata,
        KeyName=Ref(params['KeyName']),
        IamInstanceProfile=Ref(instance_role),
        ImageId=autoscaling_object['ami'],
        UserData=Base64(Ref(params[autoscaling_object["launchconfig"]["userdata"]])),
        SecurityGroups=secgroup_list,
        InstanceType=autoscaling_object["launchconfig"]["instance_type"],

    ))
    #Added in for Launchconfig on autoscale
    if "block_device_mappings" in autoscaling_object["launchconfig"]:
        block_device_list = []
        for block_device in autoscaling_object["launchconfig"]["block_device_mappings"]:
            ebs_block = ec2.EBSBlockDevice(
                block_device,
                DeleteOnTermination=autoscaling_object["launchconfig"]["block_device_mappings"][block_device]["delete_on_termination"],
                VolumeSize=autoscaling_object["launchconfig"]["block_device_mappings"][block_device]["volume_size"]
            )
            if "snapshot_id" in autoscaling_object["launchconfig"]["block_device_mappings"][block_device]:
                ebs_block.SnapshotId = autoscaling_object["launchconfig"]["block_device_mappings"][block_device]["snapshot_id"][env]
            block_device_mapping = ec2.BlockDeviceMapping(
                block_device,
                DeviceName=autoscaling_object["launchconfig"]["block_device_mappings"][block_device]["device_name"],
                Ebs=ebs_block
            )
            block_device_list.append(block_device_mapping)
        launch_configuration.BlockDeviceMappings = block_device_list
    autoscaling_group = t.add_resource(autoscaling.AutoScalingGroup(
        autoscaling_name,
        VPCZoneIdentifier=[network['SubnetEuWest1a'], network['SubnetEuWest1b'] ],
        LaunchConfigurationName=Ref(launch_configuration),
        MinSize=autoscaling_object["minsize"],
        MaxSize=autoscaling_object["maxsize"],
        DesiredCapacity=autoscaling_object["desired_capacity"],
        LoadBalancerNames=[Ref(elb_ref)],
        AvailabilityZones=autoscaling_object["az"],
        Tags=tag_list,
        NotificationConfiguration=autoscaling.NotificationConfiguration(
        TopicARN=Ref(params['SnsAutoScaling']),
            NotificationTypes=[
                "autoscaling:EC2_INSTANCE_LAUNCH",
                "autoscaling:EC2_INSTANCE_LAUNCH_ERROR",
                "autoscaling:EC2_INSTANCE_TERMINATE",
                "autoscaling:EC2_INSTANCE_TERMINATE_ERROR"
            ]
        )
    ))
    t = create_dns_record(t, params, autoscaling_object)
    if "scaling_policies" in autoscaling_object["launchconfig"]:
        for scaling_policy in autoscaling_object["launchconfig"]["scaling_policies"]:
            t.add_resource(autoscaling.ScalingPolicy(
                scaling_policy,
                AdjustmentType="ChangeInCapacity",
                AutoScalingGroupName=Ref(autoscaling_group),
                Cooldown=autoscaling_object["launchconfig"]["scaling_policies"][scaling_policy]["cooldown"],
                ScalingAdjustment=autoscaling_object["launchconfig"]["scaling_policies"][scaling_policy]["scaling_adjustment"]
            ))
        t = create_cloudwatch_alarms(t, autoscaling_object, autoscaling_group)
    return t


def create_cloudwatch_alarms(t, autoscaling_object, autoscaling_group):
    for alarm in autoscaling_object["launchconfig"]["alarms"]:
        t.add_resource(cloudwatch.Alarm(
            alarm,
            AlarmDescription=autoscaling_object["launchconfig"]["alarms"][alarm]["description"],
            MetricName=autoscaling_object["launchconfig"]["alarms"][alarm]["metric_name"],
            Namespace=autoscaling_object["launchconfig"]["alarms"][alarm]["namespace"],
            Statistic=autoscaling_object["launchconfig"]["alarms"][alarm]["statistic"],
            Period=autoscaling_object["launchconfig"]["alarms"][alarm]["period"],
            EvaluationPeriods=autoscaling_object["launchconfig"]["alarms"][alarm]["evaluation_periods"],
            Threshold=autoscaling_object["launchconfig"]["alarms"][alarm]["threshold"],
            ComparisonOperator=autoscaling_object["launchconfig"]["alarms"][alarm]["comparison_operator"],
            AlarmActions=[{"Ref": autoscaling_object["launchconfig"]["alarms"][alarm]["alarm_actions"]}],
            Dimensions=[
                {"Name": "AutoScalingGroupName",
                 "Value": Ref(autoscaling_group)}
            ]
        ))
    return t


def create_dns_record(t, params, instance_object):
    for dns_resource in instance_object["dns"]:
        if "extra_dns" in instance_object["dns"][dns_resource]:
            name_list = [instance_object["dns"][dns_resource]["name"], ".",
                      Ref(params['HostedZone']), "."]
        elif "suffix" in instance_object["dns"][dns_resource]:
            name_list = [instance_object["dns"][dns_resource]["name"], ".", instance_object["dns"][dns_resource]["suffix"], ".",
                      Ref(params['HostedZone']), "."]
        else:
            name_list = [instance_object["dns"][dns_resource]["name"], ".", instance_object["env"], ".",
                      Ref(params['HostedZone']), "."]

        #identify a static or dynamic resource record.
        if "Static" in instance_object["dns"][dns_resource]["resource_type"]:
            resource_records = instance_object["dns"][dns_resource]["resource_value"]
        else:
            resource_records = GetAtt(instance_object["dns"][dns_resource]["resource"], instance_object["dns"][dns_resource]["resource_type"])

        dns_record = t.add_resource(RecordSetType(
        dns_resource,
        HostedZoneName=Join("", [Ref(params['HostedZone']), "."]),
        Comment="DNS name for my instance.",
        Name=Join("", name_list ),
        Type=instance_object["dns"][dns_resource]["type"],
        TTL="300",
        ResourceRecords=[resource_records],
        ))
        t.add_output([
            Output(
                dns_resource,
                Description="DNS name",
                Value=Ref(dns_record),
            ),
        ])
    return t


def create_sqs_queue(name, t):

    sqs_queue = t.add_resource(sqs.Queue(
        name,
    ))
    return sqs_queue, t


def create_sns_topic(name, t, subscription):

    sns_topic = t.add_resource(sns.Topic(
        name,
        Subscription=[subscription],
        DisplayName=name
    ))
    return sns_topic, t


def create_sns_subscription(name, endpoint, protocol):

    sns_subscription = sns.Subscription(
        name,
        Endpoint=endpoint,
        Protocol=protocol
    )
    return sns_subscription


def create_rds_instance(t, params, rds_instance, rds_name, db_parameters, db_network, timestamp, flavour, jira, env):
    subnet_group_name = "%sSubnetGroup" % rds_name
    parameter_group_name = "%sParameterGroup" % rds_name

    name_tag = "%s-%s-%s-%s" % (flavour, rds_name, jira, timestamp)

    rds_parameter_group = t.add_resource(rds.DBParameterGroup(
        parameter_group_name,
        Description="Tuned for %s" % flavour,
        Family=rds_instance["db"]["family"],
        Parameters=db_parameters
    ))

    tag_list = create_tags(rds_instance, name_tag, env)

    subnet_group = t.add_resource(rds.DBSubnetGroup(
        subnet_group_name,
        DBSubnetGroupDescription=rds_instance["rds_subnet_group"]["group_description"],
        SubnetIds=[db_network["SubnetEuWest1a"], db_network["SubnetEuWest1b"]]
    ))

    rds_template = rds.DBInstance(
                    rds_name,
                    VPCSecurityGroups=[Ref(params['EnvironmentSecurityGroupId']), Ref(params['MonitoringSecurityGroup'])],
                    DBSubnetGroupName=Ref(subnet_group),
                    DBParameterGroupName=Ref(rds_parameter_group),
                    AllocatedStorage=rds_instance["db"]["allocated_storage"],
                    AutoMinorVersionUpgrade=rds_instance["db"]["auto_minor_version_upgrade"],
                    DBInstanceClass=rds_instance["db"]["instance_class"],
                    EngineVersion=rds_instance["db"]["engine_version"],
                    Engine="MySQL",
                    MultiAZ=rds_instance["db"]["multiaz"],
                    MasterUsername=rds_instance["db"]["master_username"],
                    MasterUserPassword=Ref(params['DbPasswd']),
                    Tags=tag_list
                )

    if "snapshot" in rds_instance["db"]:
        rds_template.DBSnapshotIdentifier = rds_instance["db"]["snapshot"][env]

    t.add_resource(rds_template)
    t = create_dns_record(t, params, rds_instance)


    return t


def create_elasticache(t, params, elasticache_instance, elasticache_name, network, app_network):

    elasticache_subnet_group = elasticache.SubnetGroup(
        elasticache_name + "SubnetGroup",
        Description="Subnet group for %s" % elasticache_name,
        SubnetIds=[app_network['SubnetEuWest1a'], app_network['SubnetEuWest1b']]
    )

    t.add_resource(elasticache_subnet_group)

    t.add_resource(elasticache.CacheCluster(
        elasticache_name,
        AutoMinorVersionUpgrade=elasticache_instance["elasticache"]["auto_minor_version_upgrade"],
        CacheNodeType=elasticache_instance["elasticache"]["instance_class"],
        Engine=elasticache_instance["elasticache"]["engine"],
        NumCacheNodes=elasticache_instance["elasticache"]["capacity"],
        VpcSecurityGroupIds=[network['SecurityGroupIds'], Ref(params['EnvironmentSecurityGroupId']), Ref(params['MonitoringSecurityGroup'])],
        CacheSubnetGroupName=Ref(elasticache_subnet_group),
        EngineVersion=elasticache_instance["elasticache"]["engine_version"],
    ))
    t = create_dns_record(t, params, elasticache_instance)
    return t


def create_security_group(security_group_name, security_groups, env, vpcid, t):
    ingress_list = []
    for security_group in security_groups:
        if security_group == 'nested_security_groups':
            for nested_security_group in security_groups[security_group]['name']:
                nested_security_group_id = securitygroups.security_group_id(nested_security_group, env)
                ingress_list.append(
                    {
                        "IpProtocol": security_groups[security_group]['config']['protocol'],
                        "FromPort": security_groups[security_group]['config']['from_port'],
                        "ToPort": security_groups[security_group]['config']['to_port'],
                        "SourceSecurityGroupId": nested_security_group_id
                    }
                )
        else:
            for cidr in security_groups[security_group]['cidr']:
                ingress_list.append(
                    {
                        "IpProtocol": security_groups[security_group]['config']['protocol'],
                        "FromPort": security_groups[security_group]['config']['from_port'],
                        "ToPort": security_groups[security_group]['config']['to_port'],
                        "CidrIp": cidr
                    }
                )
    if len(ingress_list) > 50:
        print "Maximum security group entries is 50. But you are trying to enter %s" % len(ingress_list)
        exit(1)
    security_group_ref = ec2.SecurityGroup(
        security_group_name,
        VpcId=vpcid,
        GroupDescription=security_group_name,
        SecurityGroupIngress=ingress_list
    )
    t.add_resource(security_group_ref)
    return t, security_group_ref


def create_resource_security_group(security_group_name, t, vpcid):
    security_group = ec2.SecurityGroup(
        security_group_name,
        VpcId=vpcid,
        GroupDescription=security_group_name,

    )
    ingress_list = []
    ingress_list.append(
        {

        }
    )
    security_group_ingress = ec2.SecurityGroupIngress(
        security_group_name + 'Full',
        GroupId=Ref(security_group),
        IpProtocol='tcp',
        FromPort='0',
        ToPort='65535',
        SourceSecurityGroupId=Ref(security_group)
    )

    security_group_ingress_ping = ec2.SecurityGroupIngress(
        security_group_name + 'Ping',
        GroupId=Ref(security_group),
        IpProtocol='icmp',
        FromPort='-1',
        ToPort='-1',
        SourceSecurityGroupId=Ref(security_group)
    )

    t.add_resource(security_group)
    t.add_resource(security_group_ingress_ping)
    t.add_resource(security_group_ingress)
    return t, security_group
