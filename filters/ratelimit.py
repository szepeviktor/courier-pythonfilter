#!/usr/bin/python

import sys
import string
import thread
import time
import courier.control

# The rate is measured in messages / interval in minutes
max_connections = 60
interval = 1

# Keep a dictionary of authenticated senders to avoid more work than
# required.
senders_lock = thread.allocate_lock()
senders = {}

# The senders lists will be scrubbed at the interval indicated in
# seconds.  All records older than the "interval" number of minutes
# will be removed from the lists.
senders_last_purged    = 0
senders_purge_interval = 60 * 60 * 12

# Record in the system log that this filter was initialized.
sys.stderr.write( 'Initialized the ratelimit python filter\n' )



def dofilter( message_body, message_ctrl_files ):
    """
    Search through the control files until the "Received-From-MTA" record
    is found.
    Check how many times this server has connected recently, and decide to
    accept or reject the message.
    """

    global senders_last_purged

    try:
        # Open the first file, read lines until we find one that
        # begins with 'f'.
        ctlfile = open( message_ctrl_files[0] )
    except:
        return '451 Internal failure locating control files'

    sender = courier.control.get_senders_mta( ctlfile )

    senders_lock.acquire()

    now = int( time.time() / 60 )

    # Scrub the lists if it is time to do so.
    if now > (senders_last_purged + (senders_purge_interval / 60)):
        min_age = now - interval
        for age in senders.keys():
            if age < min_age:
                del senders[age]
        senders_last_purged = now

    # First, add this connection to the bucket:
    if not senders.has_key( now ):
        senders[ now ] = {}
    if not senders[ now ].has_key( sender ):
        senders[ now ][ sender ] = 1
    else:
        senders[ now ][ sender ] = senders[ now ][ sender ] + 1

    # Now count the number of connections from this sender
    connections = 0
    for i in range( 0, interval ):
        if not senders.has_key( now - i ) or not senders[ now - i ].has_key( sender ):
            continue
        connections = connections + senders[ now - i ][ sender ]

    # If the connection count is higher than the max_connections setting,
    # return a soft failure.
    if connections > max_connections:
        status = '421 Too many messages from %s, slow down.' % sender
    else:
        status = ''

    senders_lock.release()

    return status
