__author__ = 'larssonp'
import core.ec2_connection
import time


def delete_sgroup_by_filter(ec2_connection, sgroup_filter):
    conn = ec2_connection

    matching_sgroups = conn.get_all_security_groups(filters={'group-name': '*%s*' % sgroup_filter})
    for sgroup in matching_sgroups:
        print sgroup.name
        conn.delete_security_group(group_id=sgroup.id)


def delete_rds_current_security_group(stack_rds, default_security_group):
    global rds, instance, sgroup

    #Change security group to default and then remove the security group
    for rds in stack_rds:
        instance = core.rds.get_rds_instance(rds)
        for sgroup in instance[0].security_groups:
            print "Changing rds instance %s security group to default" % instance[0]
            core.rds.change_security_group(stack_rds[0], default_security_group)

            print "Waiting for security group change"
            rds_status = core.rds.get_rds_instance_status(stack_rds[0])
            while rds_status == 'available':
                rds_status = core.rds.get_rds_instance_status(stack_rds[0])
                print "RDS stack %s status is %s" % (stack_rds[0], rds_status)
                time.sleep(2)
            rds_status = core.rds.get_rds_instance_status(stack_rds[0])

            while rds_status == 'modifying':
                rds_status = core.rds.get_rds_instance_status(stack_rds[0])
                time.sleep(5)
                print "RDS stack %s status is %s" % (stack_rds[0], rds_status)
            print "Removing security group %s" % sgroup.name
            delete_sgroup_by_filter(core.ec2_connection.ec2_connection(), sgroup.name)


def basesecgroup(ec2_connection):

    conn = ec2_connection
    all = conn.get_all_security_groups()
    #basegroup = conn.create_security_group('base','Default security group')

    #basegroup.authorize('tcp', 22, 22, '195.162.12.0/24')
    #basegroup.authorize('tcp', 22, 22, '93.186.36.0/27')
    #basegroup.authorize('tcp', 22, 22, '91.103.133.0/24')
    #basegroup.authorize('tcp', 22, 22, '91.103.134.0/24')
    return


def security_group_id(security_group_name, env):
    conn = core.ec2_connection.ec2_connection(env)
    security_group = conn.get_all_security_groups(filters={"group-name": security_group_name})
    return security_group[0].id




