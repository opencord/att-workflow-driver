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

class TestSubscriberAuthEvent(unittest.TestCase):

    def setUp(self):

        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        from multistructlog import create_logger
        log = create_logger(Config().get('logging'))
        # END Setting up the config module

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("att-workflow-driver", "att-workflow-driver.xproto"),
                                              ("olt-service", "volt.xproto"),
                                              ("../profiles/rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor) # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        from dhcp_event import SubscriberDhcpEventStep

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.model_accessor = model_accessor
        self.log = log

        self.event_step = SubscriberDhcpEventStep(model_accessor=self.model_accessor, log=self.log)

        self.event = Mock()

        self.volt = Mock()
        self.volt.name = "vOLT"
        self.volt.leaf_model = Mock()

        # self.subscriber = RCORDSubscriber()
        # self.subscriber.onu_device = "BRCM1234"
        # self.subscriber.save = Mock()

        self.mac_address = "00:AA:00:00:00:01"
        self.ip_address = "192.168.3.5"

        self.si = AttWorkflowDriverServiceInstance()
        self.si.serial_number = "BRCM1234"
        self.si.save = Mock()


    def tearDown(self):
        sys.path = self.sys_path_save

    def test_dhcp_subscriber(self):

        self.event.value = json.dumps({
            "deviceId" : "of:0000000000000001",
            "portNumber" : "1",
            "macAddress" : self.mac_address,
            "ipAddress" : self.ip_address,
            "messageType": "DHCPREQUEST"
        })

        with patch.object(VOLTService.objects, "get_items") as volt_service_mock, \
            patch.object(AttWorkflowDriverServiceInstance.objects, "get_items") as si_mock, \
            patch.object(self.volt, "get_onu_sn_from_openflow") as get_onu_sn:

            self.assertTrue(VOLTService.objects.first() is not None)

            volt_service_mock.return_value = [self.volt]
            get_onu_sn.return_value = "BRCM1234"
            si_mock.return_value = [self.si]

            self.event_step.process_event(self.event)

            self.si.save.assert_called()
            self.assertEqual(self.si.dhcp_state, "DHCPREQUEST")
            self.assertEqual(self.si.mac_address, self.mac_address)
            self.assertEqual(self.si.ip_address, self.ip_address)

if __name__ == '__main__':
    sys.path.append("..") # for import of helpers.py
    unittest.main()