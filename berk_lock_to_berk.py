#! /usr/bin/env python
__author__ = 'larssonp'
import os
import yaml
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-l", "--lockfile", dest="lockfile",
                  help="lockfile id", metavar="LOCKFILE")
parser.add_option("-o", "--output", dest="output",
                  help="output id", metavar="OUTPUT")
(options, args) = parser.parse_args()
if not options.lockfile:
    parser.error('No lockfile given -l Berksfile.lock')
if not options.output:
    parser.error('No output file given')

print options.lockfile

lockfile = options.lockfile
output = options.output

# Read in yaml data
f = open(os.path.expanduser(lockfile), 'r')
filedata = f.read()
config = yaml.safe_load(filedata)

f = open(output, 'w')
for source in config['sources']:
    if 'ref' in config['sources'][source]:
        f.write("cookbook '%s', :git => '%s', :ref => '%s'\n" % (source, config['sources'][source]['git'], config['sources'][source]['ref']))
    else:
        f.write("cookbook '%s', '%s'\n" % (source, config['sources'][source]['locked_version']))
f.close()