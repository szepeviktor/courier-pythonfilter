#!/usr/bin/python

import os
import sys
import string

# Run first
order = 0

# Record in the system log that this filter was initialized.
sys.stderr.write( 'Initialized the "debug" python filter\n' )


def dofilter( message_body, message_ctrl_files ):
    '''
    Print debugging information to stderr.
    '''

    sys.stderr.write( 'Debugging filter invoked:\n' )
    sys.stderr.write( '  PID: %s\n' % os.getpid() )
    sys.stderr.write( '  CWD: %s\n' % os.getcwd() )
    sys.stderr.write( '  EUID: %s\n' % os.geteuid() )
    sys.stderr.write( '  EGID: %s\n' % os.getegid() )
    sys.stderr.write( '  UID: %s\n' % os.getuid() )
    sys.stderr.write( '  GID: %s\n' % os.getgid() )
    sys.stderr.write( '  Additional groups: %s\n' % os.getgroups() )
    sys.stderr.write( '  Body: %s\n' % message_body )
    sys.stderr.write( '    Raw stat: %s\n' % os.stat(message_body) )
    for f in message_ctrl_files:
        sys.stderr.write( '  Control file: %s\n' % f )
        sys.stderr.write( '    Raw stat: %s\n' % os.stat(f) )

    # Return no decision.
    return ''
