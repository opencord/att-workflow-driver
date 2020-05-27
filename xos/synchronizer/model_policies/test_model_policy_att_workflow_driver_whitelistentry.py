
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
from mock import patch

import os
import sys

test_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))


class TestModelPolicyAttWorkflowDriverWhiteListEntry(unittest.TestCase):
    def setUp(self):
        self.sys_path_save = sys.path

        config = os.path.join(test_path, "../test_config.yaml")
        from xosconfig import Config
        Config.clear()
        Config.init(config, 'synchronizer-config-schema.yaml')

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("att-workflow-driver", "att-workflow-driver.xproto"),
                                              ("olt-service", "volt.xproto"),
                                              ("rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor)  # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        from model_policy_att_workflow_driver_whitelistentry import AttWorkflowDriverWhiteListEntryPolicy, AttHelpers
        self.AttHelpers = AttHelpers

        from mock_modelaccessor import MockObjectList
        self.MockObjectList = MockObjectList

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        # Some of the functions we call have side-effects. For example, creating a VSGServiceInstance may lead to
        # creation of tags. Ideally, this wouldn't happen, but it does. So make sure we reset the world.
        model_accessor.reset_all_object_stores()

        self.policy = AttWorkflowDriverWhiteListEntryPolicy(model_accessor=model_accessor)

        self.service = AttWorkflowDriverService()

    def tearDown(self):
        sys.path = self.sys_path_save
        self.service = None

    def test_enable_onu(self):
        si = AttWorkflowDriverServiceInstance(serial_number="BRCM333", owner_id=self.service.id, valid="invalid")
        with patch.object(self.AttHelpers, "validate_onu") as validate_onu, \
                patch.object(si, "save") as save_si:
            validate_onu.return_value = [True, "valid onu"]

            self.policy.validate_onu_state(si)

            save_si.assert_called_once()
            save_si.assert_called_with(
                always_update_timestamp=True, update_fields=[
                    'admin_onu_state', 'serial_number', 'status_message', 'updated'])

    def test_disable_onu(self):
        si = AttWorkflowDriverServiceInstance(serial_number="BRCM333", owner_id=self.service.id, valid="invalid")
        with patch.object(self.AttHelpers, "validate_onu") as validate_onu, \
                patch.object(si, "save") as save_si:
            validate_onu.return_value = [False, "invalid onu"]

            self.policy.validate_onu_state(si)

            save_si.assert_called_once()
            save_si.assert_called_with(
                always_update_timestamp=True, update_fields=[
                    'admin_onu_state', 'serial_number', 'status_message', 'updated'])

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
            wle_save.assert_called_with(
                always_update_timestamp=False, update_fields=[
                    'backend_need_delete_policy', 'owner', 'serial_number'])

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
            wle_save.assert_called_with(
                always_update_timestamp=False, update_fields=[
                    'backend_need_reap', 'owner', 'serial_number'])


if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
    unittest.main()
