
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

class TestModelPolicyAttWorkflowDriverServiceInstance(unittest.TestCase):
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
        from model_policy_att_workflow_driver_serviceinstance import AttWorkflowDriverServiceInstancePolicy, model_accessor

        from mock_modelaccessor import MockObjectList

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        # Some of the functions we call have side-effects. For example, creating a VSGServiceInstance may lead to creation of
        # tags. Ideally, this wouldn't happen, but it does. So make sure we reset the world.
        model_accessor.reset_all_object_stores()


        self.policy = AttWorkflowDriverServiceInstancePolicy()
        self.si = AttWorkflowDriverServiceInstance()
        self.si.owner = AttWorkflowDriverService()
        self.si.serial_number = "BRCM1234"

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_update_onu(self):

        onu = ONUDevice(
            serial_number="BRCM1234",
            admin_state="ENABLED"
        )
        with patch.object(ONUDevice.objects, "get_items") as get_onu, \
            patch.object(onu, "save") as onu_save:
            get_onu.return_value = [onu]

            self.policy.update_onu("brcm1234", "ENABLED")
            onu_save.assert_not_called()

            self.policy.update_onu("brcm1234", "DISABLED")
            self.assertEqual(onu.admin_state, "DISABLED")
            onu_save.assert_called_with(always_update_timestamp=True)


    def test_enable_onu(self):
        from helpers import AttHelpers
        with patch.object(AttHelpers, "validate_onu") as validate_onu, \
            patch.object(self.policy, "update_onu") as update_onu, \
            patch.object(self.si, "save") as save_si:
            validate_onu.return_value = [True, "valid onu"]

            self.policy.validate_onu_state(self.si)

            update_onu.assert_called_once()
            update_onu.assert_called_with("BRCM1234", "ENABLED")

            self.assertIn("valid onu", self.si.status_message)

    def test_disable_onu(self):
        from helpers import AttHelpers
        with patch.object(AttHelpers, "validate_onu") as validate_onu, \
                patch.object(self.policy, "update_onu") as update_onu, \
                patch.object(self.si, "save") as save_si:
            validate_onu.return_value = [False, "invalid onu"]

            self.policy.validate_onu_state(self.si)

            update_onu.assert_called_once()
            update_onu.assert_called_with("BRCM1234", "DISABLED")

            self.assertIn("invalid onu", self.si.status_message)

    def test_handle_update_validate_onu(self):
        """
        Testing that handle_update calls validate_onu with the correct parameters
        when necessary
        """
        with patch.object(self.policy, "validate_onu_state") as validate_onu_state, \
            patch.object(self.policy, "update_onu") as update_onu, \
            patch.object(self.policy, "get_subscriber") as get_subscriber:
            update_onu.return_value = None
            get_subscriber.return_value = None

            self.si.onu_state = "AWAITING"
            self.policy.handle_update(self.si)
            validate_onu_state.assert_called_with(self.si)

            self.si.onu_state = "ENABLED"
            self.policy.handle_update(self.si)
            validate_onu_state.assert_called_with(self.si)

            self.si.onu_state = "DISABLED"
            self.policy.handle_update(self.si)
            self.assertEqual(validate_onu_state.call_count, 2)

    def test_get_subscriber(self):

        sub = RCORDSubscriber(
            onu_device="BRCM1234"
        )

        with patch.object(RCORDSubscriber.objects, "get_items") as get_subscribers:
            get_subscribers.return_value = [sub]

            res = self.policy.get_subscriber("BRCM1234")
            self.assertEqual(res, sub)

            res = self.policy.get_subscriber("brcm1234")
            self.assertEqual(res, sub)

            res = self.policy.get_subscriber("foo")
            self.assertEqual(res, None)

    def test_update_subscriber(self):

        sub = RCORDSubscriber(
            onu_device="BRCM1234"
        )

        self.si.status_message = "some content"

        with patch.object(sub, "save") as sub_save:
            self.si.authentication_state = "AWAITING"
            self.policy.update_subscriber(sub, self.si)
            self.assertEqual(sub.status, "awaiting-auth")
            self.assertIn("Awaiting Authentication", self.si.status_message)
            sub_save.assert_called()
            sub_save.reset_mock()
            sub.status = None

            self.si.authentication_state = "REQUESTED"
            self.policy.update_subscriber(sub, self.si)
            self.assertEqual(sub.status, "awaiting-auth")
            self.assertIn("Authentication requested", self.si.status_message)
            sub_save.assert_called()
            sub_save.reset_mock()
            sub.status = None

            self.si.authentication_state = "STARTED"
            self.policy.update_subscriber(sub, self.si)
            self.assertEqual(sub.status, "awaiting-auth")
            self.assertIn("Authentication started", self.si.status_message)
            sub_save.assert_called()
            sub_save.reset_mock()
            sub.status = None

            self.si.authentication_state = "APPROVED"
            self.policy.update_subscriber(sub, self.si)
            self.assertEqual(sub.status, "enabled")
            self.assertIn("Authentication succeded", self.si.status_message)
            sub_save.assert_called()
            sub_save.reset_mock()
            sub.status = None

            self.si.authentication_state = "DENIED"
            self.policy.update_subscriber(sub, self.si)
            self.assertEqual(sub.status, "auth-failed")
            self.assertIn("Authentication denied", self.si.status_message)
            sub_save.assert_called()
            sub_save.reset_mock()
            sub.status = None

    def test_update_subscriber_not(self):
        sub = RCORDSubscriber(
            onu_device="BRCM1234"
        )

        with patch.object(sub, "save") as sub_save:
            sub.status = "awaiting-auth"
            self.si.authentication_state = "AWAITING"
            self.policy.update_subscriber(sub, self.si)
            sub_save.assert_not_called()

            sub.status = "awaiting-auth"
            self.si.authentication_state = "REQUESTED"
            self.policy.update_subscriber(sub, self.si)
            sub_save.assert_not_called()

            sub.status = "awaiting-auth"
            self.si.authentication_state = "STARTED"
            self.policy.update_subscriber(sub, self.si)
            sub_save.assert_not_called()

            sub.status = "enabled"
            self.si.authentication_state = "APPROVED"
            self.policy.update_subscriber(sub, self.si)
            sub_save.assert_not_called()

            sub.status = "auth-failed"
            self.si.authentication_state = "DENIED"
            self.policy.update_subscriber(sub, self.si)
            sub_save.assert_not_called()


    def test_handle_update_subscriber(self):
        self.si.onu_state = "DISABLED"

        sub = RCORDSubscriber(
            onu_device="BRCM1234"
        )

        with patch.object(self.policy, "get_subscriber") as get_subscriber, \
            patch.object(self.policy, "update_onu") as update_onu, \
            patch.object(self.policy, "update_subscriber") as update_subscriber:

            get_subscriber.return_value = None
            self.policy.handle_update(self.si)
            self.assertEqual(update_subscriber.call_count, 0)

            get_subscriber.return_value = sub
            self.policy.handle_update(self.si)
            update_subscriber.assert_called_with(sub, self.si)


if __name__ == '__main__':
    unittest.main()

