#!/usr/bin/python

import sys
import string
import courier.control
import spf

# Author: Jon Nelson <jnelson@jamponi.net>
# License: GPL v2

# Record in the system log that this filter was initialized.
sys.stderr.write( 'Initialized the SPF python filter\n' )

def get_sender(ctlfile):
    lines = courier.control.get_lines(ctlfile,'s')
    return lines[0]

def dofilter( message_body, message_ctrl_files ):
    """
    Use the SPF mechanism to whitelist, blacklist, or graylist
    email.  blacklisted email is rejected, whitelisted email is
    accepted, and greylisted email is accepted with a logline.
    Currently, it's probably far too optimistic to log greylisted.
    """
    noisy = 0
    if noisy:
        sys.stderr.write('Got %s for the message body length\n' % (len(message_body)))
        for mcf in message_ctrl_files:
            sys.stderr.write('Got %s as a message control file\n' % (mcf))
            lines = open(mcf,'r').readlines()
            lines = map(string.strip, lines)
            count = 0
            for line in lines:
                count = count + 1
                sys.stderr.write('%3d. %s' % (count, line))
        sys.stderr.write('Done\n')

    try:
        # Open the first file, read lines until we find one that
        # begins with 'f'.
        ctlfile = open( message_ctrl_files[0] )
    except:
        return '451 Internal failure locating control files'

    sender_mta = courier.control.get_senders_mta( ctlfile )
    if noisy:
        sys.stderr.write("sender_mta: %s\n" % (sender_mta))
    senders_ip = courier.control.get_senders_ip( ctlfile )
    if noisy:
        sys.stderr.write("senders ip: %s\n" % (senders_ip))
    ip = senders_ip
    sender = get_sender(ctlfile)
    # question: what if sender is '' or '<>' or '<@>' or '@' ??
    helo = string.split(sender_mta,' ')[1]
    results = spf.check(i=ip,s=sender,h=helo)
    if sender:
        sys.stderr.write("check(%s,%s,%s): %s\n" % (ip, sender, helo, results))
    # results are pass,deny,unknown
    (decision,numeric,text) = results
    if decision == 'pass':
        return ''
    elif decision == 'unknown':
        sys.stderr.write('SPF returns "unknown" for %s,%s,%s\n' % (ip,sender,helo))
        return ''
    elif decision == 'deny':
        return '517 SPF returns deny'
    else:
        sys.stderr.write('SPF returns "%s" which is not understood.' % (results))

    status = ''
    return status
