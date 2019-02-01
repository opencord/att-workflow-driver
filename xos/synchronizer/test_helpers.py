# Copyright 2017-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from mock import patch, call, Mock, PropertyMock
import json

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))


class TestAttHelpers(unittest.TestCase):

    def setUp(self):

        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END Setting up the config module

        from multistructlog import create_logger
        self.log = create_logger(Config().get('logging'))

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("att-workflow-driver", "att-workflow-driver.xproto"),
                                              ("olt-service", "volt.xproto"),
                                              ("../profiles/rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor) # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        from helpers import AttHelpers

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.helpers = AttHelpers
        self.model_accessor = model_accessor

        self._volt = VOLTService()
        self._volt.id = 1

        self.volt = Service()
        self.volt.id = 1
        self.volt.name = "vOLT"
        self.volt.leaf_model = self._volt

        self.pon_port = PONPort()
        self.pon_port.port_no = 1234

        self.onu = ONUDevice()
        self.onu.pon_port = self.pon_port
        self.onu.serial_number = "BRCM1234"

        self.att_si = AttWorkflowDriverServiceInstance(
            serial_number="BRCM1234",
            owner=self.volt,
            owner_id=self.volt.id,
            of_dpid="of:1234"
        )

        self.whitelist_entry = AttWorkflowDriverWhiteListEntry(
            serial_number="BRCM1234",
            owner=self.volt,
            owner_id=self.volt.id,
            pon_port_id=1234,
            device_id="of:1234"
        )


    def tearDown(self):
        sys.path = self.sys_path_save

    def test_not_in_whitelist(self):

        with patch.object(AttWorkflowDriverWhiteListEntry.objects, "get_items") as whitelist_mock:
            whitelist_mock.return_value = []

            [res, message] = self.helpers.validate_onu(self.model_accessor, self.log, self.att_si)

            self.assertFalse(res)
            self.assertEqual(message, "ONU not found in whitelist")

    def test_wrong_location_port(self):
        self.pon_port.port_no = 666
        with patch.object(AttWorkflowDriverWhiteListEntry.objects, "get_items") as whitelist_mock, \
            patch.object(ONUDevice.objects, "get_items") as onu_mock:
            whitelist_mock.return_value = [self.whitelist_entry]
            onu_mock.return_value = [self.onu]

            [res, message] = self.helpers.validate_onu(self.model_accessor, self.log, self.att_si)

            self.assertFalse(res)
            self.assertEqual(message, "ONU activated in wrong location")

    def test_wrong_location_device(self):
        self.att_si.of_dpid = 666
        with patch.object(AttWorkflowDriverWhiteListEntry.objects, "get_items") as whitelist_mock, \
            patch.object(ONUDevice.objects, "get_items") as onu_mock:
            whitelist_mock.return_value = [self.whitelist_entry]
            onu_mock.return_value = [self.onu]

            [res, message] = self.helpers.validate_onu(self.model_accessor, self.log, self.att_si)

            self.assertFalse(res)
            self.assertEqual(message, "ONU activated in wrong location")

    def test_deferred_validation(self):
        with patch.object(AttWorkflowDriverWhiteListEntry.objects, "get_items") as whitelist_mock, \
            patch.object(ONUDevice.objects, "get_items") as onu_mock:
            whitelist_mock.return_value = [self.whitelist_entry]
            onu_mock.return_value = []

            with self.assertRaises(Exception) as e:
                self.helpers.validate_onu(self.model_accessor, self.log, self.att_si)

            self.assertEqual(e.exception.message, "ONU device %s is not know to XOS yet" % self.att_si.serial_number)

    def test_validating_onu(self):
        with patch.object(AttWorkflowDriverWhiteListEntry.objects, "get_items") as whitelist_mock, \
            patch.object(ONUDevice.objects, "get_items") as onu_mock:
            whitelist_mock.return_value = [self.whitelist_entry]
            onu_mock.return_value = [self.onu]

            [res, message] = self.helpers.validate_onu(self.model_accessor, self.log, self.att_si)

            self.assertTrue(res)
            self.assertEqual(message, "ONU has been validated")

    def test_validating_onu_lowercase(self):
        self.whitelist_entry.serial_number = "brcm1234"
        with patch.object(AttWorkflowDriverWhiteListEntry.objects, "get_items") as whitelist_mock, \
            patch.object(ONUDevice.objects, "get_items") as onu_mock:
            whitelist_mock.return_value = [self.whitelist_entry]
            onu_mock.return_value = [self.onu]

            [res, message] = self.helpers.validate_onu(self.model_accessor, self.log, self.att_si)

            self.assertTrue(res)
            self.assertEqual(message, "ONU has been validated")

if __name__ == '__main__':
    unittest.main()