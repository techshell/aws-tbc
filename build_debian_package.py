#! /usr/bin/env python
__author__ = 'larssonp'
import core.debian_package as debian_package
import core.config as config
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-j", "--jira", dest="jira",
                  help="The jira identifier", metavar="JIRA")
parser.add_option("-f", "--flavour", dest="flavour",
                  help="Flavour, for example blogs, my, tcuk4", metavar="FLAVOUR")
parser.add_option("-t", "--type", dest="type",
                  help="Type, for example app, cms, be", metavar="TYPE")
parser.add_option("-s", "--source_directory", dest="source_directory",
                  help="Source directory. For example opt/", metavar="SOURCE_DIRECTORY")
parser.add_option("-c", "--configdir", dest="configdir",
                  help="Debian config directory for service for example ~/code/git/blogs/aws/config", metavar="CONFIG")
parser.add_option("-v", "--version", dest="version",
                  help="Package version", metavar="VERSION")
parser.add_option("-i", "--iteration", dest="iteration",
                  help="Iteration of the package", metavar="ITERATION")

(options, args) = parser.parse_args()
if not options.flavour:
    parser.error('Flavour not given. For ex escenic54, my')
if not options.jira:
    parser.error('Jira not given')
if not options.source_directory:
    parser.error('Source directory not given')
if not options.configdir:
    configdir = "config/deb_package"
if not options.type:
    parser.error('Type not given')
if not options.version:
    parser.error('No version')
if not options.iteration:
    parser.error('Iteration not given')

print "flavour %s" % options.flavour
print "jira %s   " % options.jira
print "type %s   " % options.type
print "Source directory %s   " % options.source_directory

flavour = options.flavour
jira = options.jira
type = options.type
source_directory = options.source_directory
version = options.version
iteration = options.iteration

debian_configuration = config.get_environment_configuration(configdir, flavour)
result = debian_package.create(flavour, jira, type, source_directory, debian_configuration, version, iteration)
print result