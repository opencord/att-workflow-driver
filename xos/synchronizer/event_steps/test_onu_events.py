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

class TestSyncOLTDevice(unittest.TestCase):

    def setUp(self):

        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END Setting up the config module

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("att-workflow-driver", "att-workflow-driver.xproto"),
                                              ("olt-service", "volt.xproto"),
                                              ("rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor) # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        from onu_event import ONUEventStep

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.model_accessor = model_accessor
        self.log = Mock()

        self.event_step = ONUEventStep(model_accessor=self.model_accessor, log=self.log)

        self.event = Mock()
        self.event_dict = {
            'status': 'activated',
            'serial_number': 'BRCM1234',
            'of_dpid': 'of:109299321',
            'uni_port_id': 16
        }
        self.event.value = json.dumps(self.event_dict)

        self.att = AttWorkflowDriverService(name="att-workflow-driver")

    def tearDown(self):
        sys.path = self.sys_path_save


    def test_create_instance(self):

        with patch.object(AttWorkflowDriverServiceInstance.objects, "get_items") as att_si_mock , \
            patch.object(AttWorkflowDriverService.objects, "get_items") as service_mock, \
            patch.object(AttWorkflowDriverServiceInstance, "save", autospec=True) as mock_save:

            att_si_mock.return_value = []
            service_mock.return_value = [self.att]

            self.event_step.process_event(self.event)

            att_si = mock_save.call_args[0][0]

            self.assertEqual(mock_save.call_count, 1)

            self.assertEqual(att_si.serial_number, self.event_dict['serial_number'])
            self.assertEqual(att_si.of_dpid, self.event_dict['of_dpid'])
            self.assertEqual(att_si.uni_port_id, self.event_dict['uni_port_id'])
            self.assertEqual(att_si.onu_state, "ENABLED")

    def test_reuse_instance(self):

        si = AttWorkflowDriverServiceInstance(
            serial_number=self.event_dict["serial_number"],
            of_dpid="foo",
            uni_port_id="foo"
        )

        with patch.object(AttWorkflowDriverServiceInstance.objects, "get_items") as att_si_mock , \
            patch.object(AttWorkflowDriverServiceInstance, "save", autospec=True) as mock_save:

            att_si_mock.return_value = [si]

            self.event_step.process_event(self.event)

            att_si = mock_save.call_args[0][0]

            self.assertEqual(mock_save.call_count, 1)

            self.assertEqual(att_si.serial_number, self.event_dict['serial_number'])
            self.assertEqual(att_si.of_dpid, self.event_dict['of_dpid'])
            self.assertEqual(att_si.uni_port_id, self.event_dict['uni_port_id'])
            self.assertEqual(att_si.onu_state, "ENABLED")

    def test_disable_onu(self):
        self.event_dict = {
            'status': 'disabled',
            'serial_number': 'BRCM1234',
            'of_dpid': 'of:109299321',
            'uni_port_id': 16
        }
        self.event.value = json.dumps(self.event_dict)

        with patch.object(AttWorkflowDriverServiceInstance.objects, "get_items") as att_si_mock , \
            patch.object(AttWorkflowDriverService.objects, "get_items") as service_mock, \
            patch.object(AttWorkflowDriverServiceInstance, "save", autospec=True) as mock_save:

            att_si_mock.return_value = []
            service_mock.return_value = [self.att]

            self.event_step.process_event(self.event)

            att_si = mock_save.call_args[0][0]

            self.assertEqual(mock_save.call_count, 1)

            self.assertEqual(att_si.serial_number, self.event_dict['serial_number'])
            self.assertEqual(att_si.of_dpid, self.event_dict['of_dpid'])
            self.assertEqual(att_si.uni_port_id, self.event_dict['uni_port_id'])
            self.assertEqual(att_si.onu_state, "DISABLED")

if __name__ == '__main__':
    sys.path.append("..")  # for import of helpers.py
    unittest.main()