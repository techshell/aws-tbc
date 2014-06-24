__author__ = 'larssonp'

userdata_template = """
#cloud-config

manage_etc_hosts: true
apt_update: true
apt_upgrade: true
apt_reboot_if_required: true
apt_mirror: http://repo.aws.telegraph.co.uk/ubuntu
apt_sources:
 - source: "deb http://repo.aws.telegraph.co.uk/rubygems precise main"
   filename: rubygems.list

user: ubuntu
locale: en_GB.UTF-8
timezone: GB

runcmd:
 - [ sh, -xc, "/usr/local/bin/cfn-init -v -c ascending -s STACK -r LAUNCH_RESOURCE --region eu-west-1 > /var/log/cfn-init.log" ]
 - [ sh, -xc, "/usr/local/bin/chef-solo" ]

final_message: "The system is finally up, after $UPTIME seconds"
"""


def get(stack_name, launch_resource, instance_object, type):
    userdata = userdata_template.replace('STACK', stack_name).replace('LAUNCH_RESOURCE', launch_resource)
    if type == "ec2" or type == "launchconfig":
        if "userdata_mounts" in instance_object:
            userdata_list = userdata.splitlines()
            userdata_list.append("mounts:")
            for mount in instance_object["userdata_mounts"]:
                userdata_list.append(str(" - %s" % mount))
            userdata = '\n'.join(userdata_list)
    return userdata
