#!/usr/bin/python
# courier.authdaemon -- python module for Courier's authdaemon
# Copyright (C) 2007-2008  Gordon Messmer <gordon@dragonsdawn.net>
#
# This file is part of pythonfilter.
#
# pythonfilter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pythonfilter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pythonfilter.  If not, see <http://www.gnu.org/licenses/>.

import errno
import select
import socket
import courier.config


socketPath = '/var/spool/authdaemon/socket'
_timeoutSock = 10
_timeoutWrite = 10
_timeoutRead = 30


def _setup():
    courier.config.applyModuleConfig('authdaemon.py', globals())


def _connect():
    try:
        authSock = socket.socket(socket.AF_UNIX)
    except socket.error:
        raise IOError('could not create socket')
    if _timeoutSock == 0:
        try:
            authSock.connect(socketPath)
            authSock.setblocking(0)
        except socket.error:
            raise IOError('could not connect to authdaemon socket')
    else:
        # Try to connect to the non-blocking socket.  We expect connect()
        # to throw an error, indicating that the connection is in progress.
        # Use select to wait for the connection to complete, and then check
        # for errors with getsockopt.
        authSock.setblocking(0)
        try:
            authSock.connect(socketPath)
        except socket.error, e:
            if e[0] != errno.EINPROGRESS:
                raise IOError('connection failed, error: %d, "%s"' % (e[0], e[1]))
            readySocks = select.select([authSock], [], [], _timeoutSock)
            if authSock in readySocks[0]:
                soError = authSock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if soError:
                    raise IOError('connection failed, error: %d' % soError)
            else:
                # The connection timed out.
                raise IOError('connection timed out')
    return authSock


def _writeAuth(authSock, cmd):
    try:
        # Loop: Wait for select() to indicate that the socket is ready
        # for data, and call send().  If send returns a value smaller
        # than the total length of cmd, save the remaining data, and
        # continue to attempt to send it.  If select() times out, raise
        # an exception and let the handler close the connection.
        while cmd:
            readySocks = select.select([], [authSock], [], _timeoutWrite)
            if not readySocks[1]:
                raise socket.error('Write timed out.')
            sent = authSock.send(cmd)
            if sent < len(cmd):
                cmd = cmd[sent:]
            else:
                # All the data was written, break the loop.
                break
    except socket.error:
        raise IOError('connection to authdaemon lost while sending request')


def _readAuth(authSock, term):
    data = ''
    datal = 0
    terml = len(term)
    while 1:
        readySocks = select.select([authSock], [], [], _timeoutRead)
        if not readySocks[0]:
            raise IOError('timeout when reading authdaemon reply')
        buf = authSock.recv(1024)
        if not buf:
            raise IOError('connection closed when reading authdaemon reply')
        data += buf
        datal += len(buf)
        # Detect the termination marker from authdaemon
        if datal >= terml and data.endswith(term):
            break
        if datal >= 5 and data.endswith('FAIL\n'):
            break
    return data.split('\n')


def _doAuth(cmd):
    """Send cmd to the authdaemon, and return a dictionary containing its reply."""
    authSock = _connect()
    _writeAuth(authSock, cmd)
    authData = _readAuth(authSock, '\n.\n')
    authInfo = {}
    for authLine in authData:
        if authLine == 'FAIL':
            # Return None, discarding all other data from authdaemon
            return None
        if '=' not in authLine:
            continue
        (authKey, authVal) = authLine.split('=',1)
        authInfo[authKey] = authVal
    return authInfo


def getUserInfo(service, uid):
    cmd = 'PRE . %s %s\n' % (service, uid)
    userInfo = _doAuth(cmd)
    return userInfo


# Call _setup to correct the socket path
_setup()
