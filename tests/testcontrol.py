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


class TestCourierControl(unittest.TestCase):
    
    def setUp(self):
        os.mkdir('tmp')
        os.system('cp -a queuefiles tmp/queuefiles')
        os.system('cp -a configfiles tmp/configfiles')

    def tearDown(self):
        os.system('rm -rf tmp')

    def testGetLines(self):
        self.assertEqual(courier.control.getLines(['tmp/queuefiles/control-xalias'], 's'),
                         ['root@ascension.private.dragonsdawn.net'])
        self.assertEqual(courier.control.getLines(['tmp/queuefiles/control-xalias'], 'f'),
                         ['dns; localhost (localhost [127.0.0.1])'])
        self.assertEqual(courier.control.getLines(['tmp/queuefiles/control-xalias'], 'e'),
                         [''])

    def testGetSendersMta(self):
        self.assertEqual(courier.control.getSendersMta(['tmp/queuefiles/control-xalias']),
                         'dns; localhost (localhost [127.0.0.1])')

    def testGetSendersIP(self):
        self.assertEqual(courier.control.getSendersIP(['tmp/queuefiles/control-xalias']),
                         '127.0.0.1')

    def testGetSender(self):
        self.assertEqual(courier.control.getSender(['tmp/queuefiles/control-xalias']),
                         'root@ascension.private.dragonsdawn.net')

    def testGetRecipients(self):
        self.assertEqual(courier.control.getRecipients(['tmp/queuefiles/control-xalias']),
                         ['".xalias/testalias@ascension+2eprivate+2edragonsdawn+2enet"@ascension.private.dragonsdawn.net'])

    def testGetRecipientsData(self):
        self.assertEqual(courier.control.getRecipientsData(['tmp/queuefiles/control-xalias']),
                         [['".xalias/testalias@ascension+2eprivate+2edragonsdawn+2enet"@ascension.private.dragonsdawn.net',
                           'rfc822;testalias@ascension.private.dragonsdawn.net',
                           '']])

    def testGetControlData(self):
        self.assertEqual(courier.control.getControlData(['tmp/queuefiles/control-xalias']),
                         {'e': '',
                          'f': 'dns; localhost (localhost [127.0.0.1])',
                          's': 'root@ascension.private.dragonsdawn.net',
                          'r': [['".xalias/testalias@ascension+2eprivate+2edragonsdawn+2enet"@ascension.private.dragonsdawn.net',
                                 'rfc822;testalias@ascension.private.dragonsdawn.net',
                                 '']],
                          'U': '',
                          't': '',
                          'V': None,
                          'u': 'local'})

    def testAddRecipient(self):
        courier.control.addRecipient(['tmp/queuefiles/control-xalias'],
                                     'gordon@ascension.private.dragonsdawn.net')
        self.assertEqual(courier.control.getRecipientsData(['tmp/queuefiles/control-xalias']),
                         [['".xalias/testalias@ascension+2eprivate+2edragonsdawn+2enet"@ascension.private.dragonsdawn.net',
                           'rfc822;testalias@ascension.private.dragonsdawn.net',
                           ''],
                           ['gordon@ascension.private.dragonsdawn.net',
                            '',
                            '']])

    def testAddRecipientData(self):
        courier.control.addRecipientData(['tmp/queuefiles/control-xalias'],
                                         ['gordon@ascension.private.dragonsdawn.net',
                                          'gordon@dragonsdawn.net',
                                          'N'])
        self.assertEqual(courier.control.getRecipientsData(['tmp/queuefiles/control-xalias']),
                         [['".xalias/testalias@ascension+2eprivate+2edragonsdawn+2enet"@ascension.private.dragonsdawn.net',
                           'rfc822;testalias@ascension.private.dragonsdawn.net',
                           ''],
                           ['gordon@ascension.private.dragonsdawn.net',
                            'gordon@dragonsdawn.net',
                            'N']])


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCourierControl)
    unittest.TextTestRunner(verbosity=2).run(suite)
