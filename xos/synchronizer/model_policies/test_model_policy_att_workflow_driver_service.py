
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

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
service_dir=os.path.join(test_path, "../../../..")
xos_dir=os.path.join(test_path, "../../..")
if not os.path.exists(os.path.join(test_path, "new_base")):
    xos_dir=os.path.join(test_path, "../../../../../../orchestration/xos/xos")
    services_dir=os.path.join(xos_dir, "../../xos_services")

def get_models_fn(service_name, xproto_name):
    name = os.path.join(service_name, "xos", "synchronizer", "models", xproto_name)
    if os.path.exists(os.path.join(services_dir, name)):
        return name
    raise Exception("Unable to find service=%s xproto=%s" % (service_name, xproto_name))

class TestModelPolicyAttWorkflowDriverService(unittest.TestCase):
    def setUp(self):
        self.sys_path_save = sys.path
        sys.path.append(xos_dir)
        sys.path.append(os.path.join(xos_dir, 'synchronizers', 'new_base'))

        config = os.path.join(test_path, "../test_config.yaml")
        from xosconfig import Config
        Config.clear()
        Config.init(config, 'synchronizer-config-schema.yaml')

        from synchronizers.new_base.mock_modelaccessor_build import build_mock_modelaccessor
        build_mock_modelaccessor(xos_dir, services_dir, [
            get_models_fn("att-workflow-driver", "att-workflow-driver.xproto"),
            get_models_fn("olt-service", "volt.xproto"),
            get_models_fn("../profiles/rcord", "rcord.xproto")
        ])

        import synchronizers.new_base.modelaccessor
        from model_policy_att_workflow_driver_service import AttWorkflowDriverServicePolicy, model_accessor

        from mock_modelaccessor import MockObjectList
        self.MockObjectList = MockObjectList

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        # Some of the functions we call have side-effects. For example, creating a VSGServiceInstance may lead to creation of
        # tags. Ideally, this wouldn't happen, but it does. So make sure we reset the world.
        model_accessor.reset_all_object_stores()

        self.policy = AttWorkflowDriverServicePolicy()

        self.service = AttWorkflowDriverService(
            id = 5367,
            whitelist_entries = [],
        )

        # needs to be enabled
        self.si1 = AttWorkflowDriverServiceInstance(
            valid="awaiting",
            serial_number="BRCM111"
        )

        # needs to be enabled
        self.si2 = AttWorkflowDriverServiceInstance(
            valid="invalid",
            serial_number="BRCM222"
        )

        # remains disabled
        self.si3 = AttWorkflowDriverServiceInstance(
            valid="invalid",
            serial_number="BRCM333"
        )

        # needs to be disabled
        self.si4 = AttWorkflowDriverServiceInstance(
            valid="valid",
            serial_number="BRCM444"
        )

    def tearDown(self):
        sys.path = self.sys_path_save
        self.service = None

    def test_whitelist_update(self):
        """
        When the whitelist is updated, check for added ONU to be enabled and for removed ONU to be disabled
        """
        with patch.object(AttWorkflowDriverServiceInstance.objects, "get_items") as oss_si, \
            patch.object(self.si1, "save") as si1_save, \
            patch.object(self.si2, "save") as si2_save, \
            patch.object(self.si3, "save") as si3_save, \
            patch.object(self.si4, "save") as si4_save:
            oss_si.return_value = [self.si1, self.si2, self.si3, self.si4]

            wle1 = AttWorkflowDriverWhiteListEntry(owner_id=self.service.id, serial_number="BRCM111")
            wle2 = AttWorkflowDriverWhiteListEntry(owner_id=self.service.id, serial_number="BRCM222")
            self.service.whitelist_entries = self.MockObjectList([wle1, wle2])

            self.policy.handle_update(self.service)

            self.si1.save.assert_called_with(always_update_timestamp=True, update_fields=['valid', 'no_sync', 'updated'])
            self.assertEqual(self.si1.valid, "valid")
            self.si2.save.assert_called_with(always_update_timestamp=True, update_fields=['valid', 'no_sync', 'updated'])
            self.assertEqual(self.si2.valid, "valid")
            self.si3.save.assert_not_called()
            self.assertEqual(self.si3.valid, "invalid")
            self.si4.save.assert_called_with(always_update_timestamp=True, update_fields=['valid', 'no_sync', 'updated'])
            self.assertEqual(self.si4.valid, "invalid")

if __name__ == '__main__':
    unittest.main()

