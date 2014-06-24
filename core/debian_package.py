__author__ = 'larssonp'
import subprocess
import sys
import core.config as config
import ast


def create(flavour, jira, type, source_directory, debian_configuration, version, iteration):
    last_log = ""
    dep_string = ""
    
    deb_config = debian_configuration[type]

    command_base = "/usr/local/bin/fpm -s %s -t %s -n %s-%s -a %s -v %s --deb-user %s --deb-group %s --iteration %s" % \
        (deb_config['package_source'], deb_config['package_type'], deb_config['package_name'],
         jira, deb_config['arch'], version, deb_config['deb-user'], deb_config['deb-group'], iteration)

    if 'after-install' in deb_config:
        config.list_to_file(deb_config['after-install'], '%s/after-install' % source_directory)
        command = command_base + " --after-install after-install "
    if 'before-install' in deb_config:
        config.list_to_file(deb_config['before-install'], '%s/before-install' % source_directory)
        command = command + " --before-install before-install "
    if 'depends' in deb_config:
        for dep in deb_config['depends']:
            dep_string = dep_string + " -d %s " % dep
        command = command + " %s " % dep_string

    command_tail = " %s" % deb_config['root_dir']
    command = command + command_tail

    print "Will run: %s" % command

    try:
        print "Building %s Debian package, version %s with iteration %s" % (flavour, version, iteration)
        process = subprocess.Popen(command, shell=True, cwd=source_directory, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        while True:
            next_line = process.stdout.readline()
            if next_line != "":
                last_log = next_line
            if next_line == '' and process.poll() != None:
                break
            sys.stdout.write(next_line)
            sys.stdout.flush()

        exitCode = process.returncode
        print "Build completed with exit code %s" % exitCode
        if last_log.find("fatal") > 0:
                print "found fatal in package build"
                sys.exit(1)
        else:
            last_log_array = last_log.split(":")
            package = last_log_array[5].split('"')[1]
            return package

    except subprocess.CalledProcessError, e:
        print e.output
        sys.exit(1)
        return 1
