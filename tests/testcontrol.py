#!/usr/bin/python
# pythonfilter -- A python framework for Courier global filters
# Copyright (C) 2006  Gordon Messmer <gordon@dragonsdawn.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os
import unittest
import courier.config


courier.config.sysconfdir = 'tmp/configfiles'


import courier.control


message = {}
message['xalias'] = {'controlFileList': ['tmp/queuefiles/control-xalias'],
                     'controlData': {'e': '',
                                     'f': 'dns; localhost (localhost [127.0.0.1])',
                                     's': 'root@ascension.private.dragonsdawn.net',
                                     'r': [['".xalias/testalias@ascension+2eprivate+2edragonsdawn+2enet"@ascension.private.dragonsdawn.net',
                                            'rfc822;testalias@ascension.private.dragonsdawn.net',
                                            '']],
                                     'U': '',
                                     't': '',
                                     'V': None,
                                     'u': 'local'},
                     'sendersIP': '127.0.0.1'}
message['duplicate'] = {'controlFileList': ['tmp/queuefiles/control-duplicate'],
                        'controlData': {'e': '',
                                        'f': 'dns; localhost (localhost [127.0.0.1])',
                                        's': 'root@ascension.private.dragonsdawn.net',
                                        'r': [['gordon@ascension.private.dragonsdawn.net',
                                               '',
                                               ''],
                                              ['gordon@ascension.private.dragonsdawn.net',
                                               'rfc822;postmaster@ascension.private.dragonsdawn.net',
                                               '']],
                                        'U': '',
                                        't': '',
                                        'V': None,
                                        'u': 'local'},
                        'sendersIP': '127.0.0.1'}
message['ldapalias'] = {'controlFileList':  ['tmp/queuefiles/control-ldapalias'],
                        'controlData':{'e': '',
                                       'f': 'dns; localhost (localhost [127.0.0.1])',
                                       's': 'root@ascension.private.dragonsdawn.net',
                                       'r': [['rob@ascension.private.dragonsdawn.net',
                                              '',
                                              'N'],
                                             ['gordon@ascension.private.dragonsdawn.net',
                                              '',
                                              'N'],
                                             ['testldap@ascension.private.dragonsdawn.net',
                                              '',
                                              '']],
                                       'U': '',
                                       't': '',
                                       'V': None,
                                       'u': 'local'},
                        'sendersIP': '127.0.0.1'}
rcptA = ['gordon@ascension.private.dragonsdawn.net',
         '',
         '']
rcptB = ['gordon@ascension.private.dragonsdawn.net',
         'gordon@dragonsdawn.net',
         'N']


class TestCourierControl(unittest.TestCase):
    
    def setUp(self):
        os.mkdir('tmp')
        os.system('cp -a queuefiles tmp/queuefiles')
        os.system('cp -a configfiles tmp/configfiles')

    def tearDown(self):
        os.system('rm -rf tmp')

    def testGetLines(self):
        for x in message.values():
            self.assertEqual(courier.control.getLines(x['controlFileList'], 's'),
                             [x['controlData']['s']])
            self.assertEqual(courier.control.getLines(x['controlFileList'], 'f'),
                             [x['controlData']['f']])
            self.assertEqual(courier.control.getLines(x['controlFileList'], 'e'),
                             [x['controlData']['e']])

    def testGetSendersMta(self):
        for x in message.values():
            self.assertEqual(courier.control.getSendersMta(x['controlFileList']),
                             x['controlData']['f'])

    def testGetSendersIP(self):
        for x in message.values():
            self.assertEqual(courier.control.getSendersIP(x['controlFileList']),
                             x['sendersIP'])

    def testGetSender(self):
        for x in message.values():
            self.assertEqual(courier.control.getSender(x['controlFileList']),
                             x['controlData']['s'])

    def testGetRecipients(self):
        for x in message.values():
            self.assertEqual(courier.control.getRecipients(x['controlFileList']),
                             [y[0] for y in x['controlData']['r']])

    def testGetRecipientsData(self):
        for x in message.values():
            self.assertEqual(courier.control.getRecipientsData(x['controlFileList']),
                             x['controlData']['r'])

    def testGetControlData(self):
        for x in message.values():
            self.assertEqual(courier.control.getControlData(x['controlFileList']),
                             x['controlData'])

    def testAddRecipient(self):
        for x in message.values():
            courier.control.addRecipient(x['controlFileList'],
                                         rcptA[0])
            self.assertEqual(courier.control.getRecipientsData(x['controlFileList']),
                             x['controlData']['r'] + [rcptA])

    def testAddRecipientData(self):
        for x in message.values():
            courier.control.addRecipientData(x['controlFileList'],
                                             rcptB)
            self.assertEqual(courier.control.getRecipientsData(x['controlFileList']),
                             x['controlData']['r'] + [rcptB])

    def testDelRecipient(self):
        for x in message.values():
            courier.control.addRecipient(x['controlFileList'],
                                         rcptA[0])
            self.assertEqual(courier.control.getRecipientsData(x['controlFileList']),
                             x['controlData']['r'] + [rcptA])
            courier.control.delRecipient(x['controlFileList'],
                                         rcptA[0])
            self.assertEqual(courier.control.getRecipientsData(x['controlFileList']),
                             x['controlData']['r'] + [rcptA])

    def testDelRecipientData(self):
        for x in message.values():
            courier.control.addRecipientData(x['controlFileList'],
                                             rcptB)
            self.assertEqual(courier.control.getRecipientsData(x['controlFileList']),
                             x['controlData']['r'] + [rcptB])
            courier.control.delRecipientData(x['controlFileList'],
                                             rcptB)
            self.assertEqual(courier.control.getRecipientsData(x['controlFileList']),
                             x['controlData']['r'] + [rcptB])


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCourierControl)
    unittest.TextTestRunner(verbosity=2).run(suite)
