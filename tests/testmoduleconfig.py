#!/usr/bin/python
# pythonfilter -- A python framework for Courier global filters
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

import unittest
import courier.config


class TestModuleConfig(unittest.TestCase):

    def testLoader(self):
        courier.config._standardConfigPaths = './configfiles/pythonfilter-modules.conf'
        config = courier.config.getModuleConfig('test1')
        self.assertEqual(config['name1'], 'value1')
        self.assertEqual(config['name2'], 'value2')
        self.assertEqual('name3' in config, False)
        self.assertEqual('name4' in config, False)
        self.assertEqual('atuple' in config, False)
        self.assertEqual('alist' in config, False)
        self.assertEqual('adict' in config, False)

        config = courier.config.getModuleConfig('test2')
        self.assertEqual(config['name3'], 'value3')
        self.assertEqual(config['name4'], 'value4')
        self.assertEqual('name1' in config, False)
        self.assertEqual('name2' in config, False)
        self.assertEqual('atuple' in config, False)
        self.assertEqual('alist' in config, False)
        self.assertEqual('adict' in config, False)

        config = courier.config.getModuleConfig('test3')
        self.assertEqual('name1' in config, False)
        self.assertEqual('name2' in config, False)
        self.assertEqual('name3' in config, False)
        self.assertEqual('name4' in config, False)
        self.assertEqual(type(config['atuple']), tuple)
        self.assertEqual(config['atuple'], (1,2,3))
        self.assertEqual(type(config['alist']), list)
        self.assertEqual(config['alist'], [1,2,3])
        self.assertEqual(type(config['adict']), dict)
        self.assertEqual(config['adict']['dict1'], 'dictval1')
        self.assertEqual(config['adict']['dict2'], 'dictval2')


    def testApply(self):
        courier.config._standardConfigPaths = './configfiles/pythonfilter-modules.conf'
        config = {}
        courier.config.applyModuleConfig('test1', config)
        self.assertEqual(config['name1'], 'value1')
        self.assertEqual(config['name2'], 'value2')
        self.assertEqual('name3' in config, False)
        self.assertEqual('name4' in config, False)
        self.assertEqual('atuple' in config, False)
        self.assertEqual('alist' in config, False)
        self.assertEqual('adict' in config, False)

        config = {}
        courier.config.applyModuleConfig('test2', config)
        self.assertEqual(config['name3'], 'value3')
        self.assertEqual(config['name4'], 'value4')
        self.assertEqual('name1' in config, False)
        self.assertEqual('name2' in config, False)
        self.assertEqual('atuple' in config, False)
        self.assertEqual('alist' in config, False)
        self.assertEqual('adict' in config, False)

        config = {}
        courier.config.applyModuleConfig('test3', config)
        self.assertEqual('name1' in config, False)
        self.assertEqual('name2' in config, False)
        self.assertEqual('name3' in config, False)
        self.assertEqual('name4' in config, False)
        self.assertEqual(type(config['atuple']), tuple)
        self.assertEqual(config['atuple'], (1,2,3))
        self.assertEqual(type(config['alist']), list)
        self.assertEqual(config['alist'], [1,2,3])
        self.assertEqual(type(config['adict']), dict)
        self.assertEqual(config['adict']['dict1'], 'dictval1')
        self.assertEqual(config['adict']['dict2'], 'dictval2')


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestModuleConfig)
    unittest.TextTestRunner(verbosity=2).run(suite)
