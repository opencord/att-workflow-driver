
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

class TestModelPolicyAttWorkflowDriverWhiteListEntry(unittest.TestCase):
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
        from model_policy_att_workflow_driver_whitelistentry import AttWorkflowDriverWhiteListEntryPolicy, model_accessor

        from mock_modelaccessor import MockObjectList
        self.MockObjectList = MockObjectList

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        # Some of the functions we call have side-effects. For example, creating a VSGServiceInstance may lead to creation of
        # tags. Ideally, this wouldn't happen, but it does. So make sure we reset the world.
        model_accessor.reset_all_object_stores()

        self.policy = AttWorkflowDriverWhiteListEntryPolicy()

        self.service = AttWorkflowDriverService()


    def tearDown(self):
        sys.path = self.sys_path_save
        self.service = None

    def test_enable_onu(self):
        from helpers import AttHelpers
        si = AttWorkflowDriverServiceInstance(serial_number="BRCM333", owner_id=self.service.id, valid="invalid")
        with patch.object(AttHelpers, "validate_onu") as validate_onu, \
            patch.object(si, "save") as save_si:
            validate_onu.return_value = [True, "valid onu"]

            self.policy.validate_onu_state(si)

            save_si.assert_called_once()
            save_si.assert_called_with(always_update_timestamp=True, update_fields=['onu_state', 'serial_number', 'status_message', 'updated'])

            self.assertEqual("valid onu", si.status_message)

    def test_disable_onu(self):
        from helpers import AttHelpers
        si = AttWorkflowDriverServiceInstance(serial_number="BRCM333", owner_id=self.service.id, valid="invalid")
        with patch.object(AttHelpers, "validate_onu") as validate_onu, \
            patch.object(si, "save") as save_si:
            validate_onu.return_value = [False, "invalid onu"]

            self.policy.validate_onu_state(si)

            save_si.assert_called_once()
            save_si.assert_called_with(always_update_timestamp=True, update_fields=['authentication_state', 'onu_state', 'serial_number', 'status_message', 'updated'])

            self.assertEqual("invalid onu", si.status_message)

    def test_whitelist_update(self):
        si = AttWorkflowDriverServiceInstance(serial_number="BRCM333", owner_id=self.service.id)
        wle = AttWorkflowDriverWhiteListEntry(serial_number="brcm333", owner_id=self.service.id, owner=self.service)
        with patch.object(AttWorkflowDriverServiceInstance.objects, "get_items") as oss_si_items, \
            patch.object(self.policy, "validate_onu_state") as validate_onu_state, \
            patch.object(wle, "save") as wle_save:
            oss_si_items.return_value = [si]


            self.policy.handle_update(wle)

            validate_onu_state.assert_called_with(si)
            self.assertTrue(wle.backend_need_delete_policy)
            wle_save.assert_called_with(update_fields=["backend_need_delete_policy"])

    def test_whitelist_delete(self):
        si = AttWorkflowDriverServiceInstance(serial_number="BRCM333", owner_id=self.service.id)
        wle = AttWorkflowDriverWhiteListEntry(serial_number="brcm333", owner_id=self.service.id, owner=self.service)
        with patch.object(AttWorkflowDriverServiceInstance.objects, "get_items") as oss_si_items, \
                patch.object(self.policy, "validate_onu_state") as validate_onu_state, \
                patch.object(wle, "save") as wle_save:
            oss_si_items.return_value = [si]

            self.policy.handle_delete(wle)

            validate_onu_state.assert_called_with(si)
            self.assertTrue(wle.backend_need_reap)
            wle_save.assert_called_with(update_fields=["backend_need_reap"])
if __name__ == '__main__':
    unittest.main()

