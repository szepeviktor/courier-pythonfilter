#!/usr/bin/python

import sys
import string
import courier.control
import courier.config


# Run before any other filter.
order = 0

# Record in the system log that this filter was initialized.
sys.stderr.write( 'Initialized the "whitelist" python filter\n' )



def dofilter( message_body, message_ctrl_files ):
    '''
    Search through the control files and discover the address of the sender.
    If the IP is one which we relay for, return a 200 code so pythonfilter
    stops processing individual filters.
    '''

    try:
        ctlfile = open( message_ctrl_files[0] )
    except:
        return '451 Internal failure locating control files'

    senderip = courier.control.get_senders_ip( ctlfile )
    if senderip and courier.config.isrelayed( senderip ):
        # Don't filter any messages from our relay clients.
        return '200 Ok'

    # Return no decision for everyone else.
    return ''



if __name__ == '__main__':
    # For debugging, you can create a file that contains one line,
    # formatted as Courier's Received-From-MTA record:
    # faddresstype; address
    # Run this script with the name of that file as an argument,
    # and it'll print either "200 Ok" to indicate that the address
    # is whitelisted, or nothing to indicate that the remaining
    # filters would be run.
    if not sys.argv[1:]:
        print 'Use:  whitelist.py <control file>'
        sys.exit( 1 )
    print dofilter( '', sys.argv[1:] )

