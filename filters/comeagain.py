#!/usr/bin/python

import sys
import string
import thread
import time
import anydbm
import md5
import courier.control
import courier.config



# Keep a dictionary of sender/recipient pairs that we've seen before
senders_lock = thread.allocate_lock()
senders_dir = '/var/state/dialback'
try:
    senders = anydbm.open( senders_dir + '/correspondents', 'cw' )
except:
    sys.stderr.write( 'Failed to open correspondents db in %s, make sure that the directory exists\n' % senders_dir )
    sys.exit( 1 )
senders_last_purged = 0

# The good/bad senders lists will be scrubbed at the interval indicated
# in seconds.  All records older than the "listed_for" number of seconds
# will be removed from the lists.
senders_listed_for     = 60 * 60 * 24 * 30
senders_purge_interval = 60 * 60 * 12

# Record in the system log that this filter was initialized.
sys.stderr.write( 'Initialized the "comeagain" python filter\n' )



def dofilter( message_body, message_ctrl_files ):
    '''
    Search through the control files and discover the envelope sender and
    message recipients.  If the sender has written to these recipients
    before, allow the message.  Otherwise, throw a temporary failure, and
    expect the remote MTA to try again.  Many spamware sites and viruses
    will not, preventing these messages from getting into the users''
    mailbox.
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

    senderip = courier.control.get_senders_ip( ctlfile )
    if senderip and courier.config.isrelayed( senderip ):
        # Don't do comeagain on messages from our relay clients.
        return ''

    # Scrub the lists if it is time to do so.
    senders_lock.acquire()
    if time.time() > (senders_last_purged + senders_purge_interval):
        min_age = time.time() - senders_listed_for
        for key in senders.keys():
            if float(senders[key]) < min_age:
                del senders[key]
        senders_last_purged = time.time()
    senders_lock.release()

    # Create a new MD5 object.  The pairs of sender/recipient will
    # be stored in the db in the form of an MD5 digest.
    sendermd5 = md5.new( sender )

    # Create a digest for each recipient and look it up in the db.
    # Update the timestamp of each pair as we look them up.  If any
    # pair does not exist, we'll have to ask the sender to deliver
    # again.
    foundall=1
    for file in message_ctrl_files:
        ctrlfile = open( file )
        senders_lock.acquire()
        for recipient in courier.control.get_recipients( ctrlfile ):
            correspondents = sendermd5.copy()
            correspondents.update( recipient )
            cdigest = correspondents.hexdigest()
            if not senders.has_key( cdigest ):
                foundall = 0
            senders[ cdigest ] = str(time.time())
        senders_lock.release()

    if foundall:
        return ''
    else:
        return( '421-Please send the message again.\n'
                '421-This is not an indication of a problem:  We require\n'
                '421-that any new sender retry their delivery as proof that\n'
                '421-they are not spamware or virusware.\n'
                '421 Thank you.' )



if __name__ == '__main__':
    # For debugging, you can create a file that contains one line,
    # beginning with an 's' character, followed by an email address
    # and more lines, beginning with an 'r' character, for each
    # recipient.  Run this script with the name of that file as an
    # argument, and it'll validate that email address.
    if not sys.argv[1:]:
        print 'Use:  comeagain.py <control file>'
        sys.exit( 1 )
    print dofilter( '', sys.argv[1:] )

