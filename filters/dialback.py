#!/usr/bin/python

import os
import sys
import string
import thread
import select
import time
import DNS
import smtplib
import socket
import anydbm
import courier.config



# Keep a dictionary of authenticated senders to avoid more work than
# required.
senders_lock = thread.allocate_lock()
senders_dir = '/var/state/pythonfilter'
try:
    good_senders = anydbm.open( senders_dir + '/goodsenders', 'cw' )
    bad_senders = anydbm.open( senders_dir + '/badsenders', 'cw' )
except:
    sys.stderr.write( 'Failed to open db in %s, make sure that it exists\n' % senders_dir )
    sys.exit( 1 )
senders_last_purged = 0

# The good/bad senders lists will be scrubbed at the interval indicated
# in seconds.  All records older than the "listed_for" number of seconds
# will be removed from the lists.
senders_listed_for = 604800
senders_purge_interval = 43200

# SMTP conversation timeout in seconds.  Setting this too low will
# lead to 4XX failures.
smtptimeout = 60

# Initialize the DNS module
DNS.DiscoverNameServers()

# The postmaster address will be used for the "MAIL" command in the
# dialback conversation.
postmaster_addr = 'postmaster@%s' % courier.config.me()

# Record in the system log that this filter was initialized.
sys.stderr.write( 'Initialized the dialback python filter\n' )



def dofilter( message_body, message_ctrl_files ):
    '''
    Search through the control files until the envelope sender is found.
    Dial back to that sender\'s MX servers and validate that the username
    is valid by checking the server\'s reply to \"RCPT TO\".
    '''

    global senders_last_purged

    try:
        # The envelope sender will always be the first record in the control
        # files, according to the courier documentation.  Open the first file,
        # read the first line, and if it isn't the sender record, return
        # a failure response.
        ctlfile = open( message_ctrl_files[0] )
        ctlline = ctlfile.readline()
    except:
        return '451 Internal failure locating control files'

    if ctlline[0] != 's':
        return '451 Internal failure locating envelope sender record'
    if len( ctlline ) == 2:
        # Null sender is allowed as a non-fatal error
        return ''

    sender = string.strip( ctlline[1:] )

    # If this sender is known already, then we don't actually need to do the
    # dialback.  Update the timestamp in the dictionary and then return the
    # status.
    senders_lock.acquire()
    # Scrub the lists if it is time to do so.
    if time.time() > (senders_last_purged + senders_purge_interval):
        min_age = time.time() - senders_listed_for
        for key in good_senders.keys():
            if float(good_senders[key]) < min_age:
                del good_senders[key]
        for key in bad_senders.keys():
            if float(bad_senders[key]) < min_age:
                del bad_senders[key]
        senders_last_purged = time.time()
    if good_senders.has_key( sender ):
        good_senders[ sender ] = str(time.time())
        senders_lock.release()
        return ''
    if bad_senders.has_key( sender ):
        bad_senders[ sender ] = str(time.time())
        senders_lock.release()
        return '517 Sender does not exist: %s' % sender
    senders_lock.release()

    # The sender is new, so break the address into name and domain parts.
    try:
        ( sender_name, sender_domain ) = string.split( sender , '@' )
    except:
        # Pretty sure this can't happen...
        return '501 Envelope sender is invalid'

    # Look up the MX records for this sender's domain in DNS.  If none are
    # found, then check the domain for an A record, and dial back to that
    # host.  If no A record is found, then perhaps the message is a DSN...
    # Just return a success code if no MX and no A records are found.
    try:
        mxlist = DNS.mxlookup( sender_domain )
        if mxlist == []:
            if socket.getaddrinfo( sender_domain, 'smtp' ):
                # put this host in the mxlist and continue
                mxlist.append( (1, sender_domain) )
            else:
                # no record was found
                return ''
    except:
        # Probably a DNS timeout...
        # Also should never happen, because courier's smtpd should have
        # just validated this domain.
        return '421 DNS failure resolving %s' % sender_domain

    # Loop through the dial-back candidates and ask each one to validate
    # the address that we got as the sender.  If they return a success
    # code to the RCPT command, then we accept the mail.  If they return
    # any 5XX code, we refuse the incoming mail with a 5XX error, as well.
    # If no SMTP server is available, or all report 4XX errors, we'll
    # give a 4XX error to the sender.
    for MX in mxlist:
        # Create a pipe so that we can read the results of the
        # test from the child
        (rpipe, wpipe) = os.pipe()
        # Create an SMTP instance.  If the dialback thread takes
        # too long, we'll close its socket.
        smtpi = smtplib.SMTP()
        # Run the dialback in another thread, and wait for a
        # reply.
        thread.start_new_thread( dialback, (smtpi, MX, sender, wpipe) )

        ready_pipes = select.select( [rpipe],[],[], smtptimeout )
        if rpipe not in ready_pipes[0]:
            # Time to cancel this SMTP conversation
            smtpi.close()
            continue

        status = os.read( rpipe, 1024 )
        if len(status) < 4:
            # not a full status message
            continue
        if status[:3] == '250':
            # Success!  Mark this user good.
            senders_lock.acquire()
            good_senders[ sender ] = str(time.time())
            senders_lock.release()
            return ''
        if status[0] == '5':
            # Mark this user bad.
            senders_lock.acquire()
            bad_senders[ sender ] = str(time.time())
            senders_lock.release()
            return '517-MX server %s said:\n' \
                   '517 Sender does not exist: %s' % ( MX[1], sender )

    return '421 No SMTP servers were available to authenticate sender'



def dialback( SMTP, MX, sender, statuspipe ):
    try:
        SMTP.connect( MX[1] )
        ( code, reply ) = SMTP.helo()
        if code // 100 != 2:
            sys.stderr.write( '%s rejected the HELO command' % MX[1] )
            os.write( statuspipe, '%d %s' % (code, reply) )
            return

        ( code, reply ) = SMTP.mail( postmaster_addr )
        if code // 100 != 2:
            sys.stderr.write( '%s rejected the MAIL FROM command' % MX[1] )
            os.write( statuspipe, '%d %s' % (code, reply) )
            return

        ( code, reply ) = SMTP.rcpt( sender )
        SMTP.quit()
    except:
        code = 400
        reply = 'SMTP class exception'

    # Write the status of the RCPT command back to the caller,
    # and let it be handled there.
    os.write( statuspipe, '%d %s' % (code, reply) )



if __name__ == '__main__':
    # For debugging, you can create a file that contains just one
    # line, beginning with an 's' character, followed by an email
    # address.  Run this script with the name of that file as an
    # argument, and it'll validate that email address.
    if not sys.argv[1:]:
        print 'Use:  dialback.py <control file>'
        sys.exit( 1 )
    print dofilter( '', sys.argv[1:] )

