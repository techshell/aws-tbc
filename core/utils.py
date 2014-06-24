__author__ = 'dmore'

import sys


def hilite(string, status, bold):
    attr = []
    if status:
        # green
        attr.append('32')
    else:
        # red
        attr.append('31')
    if bold:
        attr.append('1')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), string)


def request_console_confirmation(env):

    result = False
    if env == 'prod':
        user_input = raw_input(hilite("running in %s! Are you sure you want to continue?[Y/n]" % env, False, True))
        if user_input.capitalize() == 'Y':
            print hilite("running in %s" % env, True, True)
            result = True
        elif user_input.capitalize() == '':
            print hilite("running in %s" % env, True, True)
            result = True
        else:
            print hilite("cancelled %s run!" % env, False, True)
            result = False
    else:
        return

    if result == False:
        sys.exit(0)
