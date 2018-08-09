
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

    def tearDown(self):
        sys.path = self.sys_path_save
        self.si = None

    def test_not_synced(self):
        self.si.valid = "awaiting"
        self.si.backend_code = 0

        with patch.object(RCORDSubscriber, "save") as subscriber_save, \
            patch.object(ONUDevice, "save") as onu_save:

            with self.assertRaises(Exception) as e:
               self.policy.handle_update(self.si)

            self.assertIn("has not been synced yet", e.exception.message)

    def test_skip_update(self):
        self.si.valid = "awaiting"
        self.si.backend_code = 1

        with patch.object(RCORDSubscriber, "save") as subscriber_save, \
            patch.object(ONUDevice, "save") as onu_save:

            self.policy.handle_update(self.si)
            subscriber_save.assert_not_called()
            onu_save.assert_not_called()

    def test_disable_onu(self):
        self.si.valid = "invalid"
        self.si.serial_number = "BRCM1234"
        self.si.backend_code = 1

        onu = ONUDevice(
            serial_number=self.si.serial_number
        )

        with patch.object(ONUDevice.objects, "get_items") as onu_objects, \
                patch.object(RCORDSubscriber, "save") as subscriber_save, \
                patch.object(ONUDevice, "save") as onu_save:

            onu_objects.return_value = [onu]

            self.policy.handle_update(self.si)
            subscriber_save.assert_not_called()
            self.assertEqual(onu.admin_state, "DISABLED")
            onu_save.assert_called()

    def test_enable_onu(self):
        self.si.valid = "valid"
        self.si.serial_number = "BRCM1234"
        self.si.c_tag = None
        self.si.backend_code = 1

        onu = ONUDevice(
            serial_number=self.si.serial_number,
            admin_state="DISABLED"
        )

        subscriber = RCORDSubscriber(
            onu_device=self.si.serial_number,
            status='pre-provisioned'
        )

        with patch.object(ONUDevice.objects, "get_items") as onu_objects, \
                patch.object(RCORDSubscriber.objects, "get_items") as subscriber_objects, \
                patch.object(ONUDevice, "save") as onu_save:

            onu_objects.return_value = [onu]
            subscriber_objects.return_value = [subscriber]

            self.policy.handle_update(self.si)
            self.assertEqual(onu.admin_state, "ENABLED")
            onu_save.assert_called()

    def test_do_not_create_subscriber(self):
        self.si.valid = "valid"
        self.si.backend_code = 1
        self.si.serial_number = "BRCM1234"
        self.si.authentication_state = "DENIEND"
        self.si.owner.leaf_model.create_on_discovery = False

        onu = ONUDevice(
            serial_number=self.si.serial_number,
            admin_state="DISABLED"
        )
        
        with patch.object(ONUDevice.objects, "get_items") as onu_objects, \
                patch.object(RCORDSubscriber, "save", autospec=True) as subscriber_save, \
                patch.object(ONUDevice, "save") as onu_save:

            onu_objects.return_value = [onu]

            self.policy.handle_update(self.si)

            self.assertEqual(onu.admin_state, "ENABLED")
            onu_save.assert_called()
            self.assertEqual(subscriber_save.call_count, 0)

    def test_create_subscriber(self):
        self.si.valid = "valid"
        self.si.serial_number = "BRCM1234"
        self.si.backend_code = 1

        onu = ONUDevice(
            serial_number=self.si.serial_number,
            admin_state="ENABLED"
        )

        with patch.object(ONUDevice.objects, "get_items") as onu_objects, \
                patch.object(RCORDSubscriber, "save", autospec=True) as subscriber_save, \
                patch.object(ONUDevice, "save") as onu_save:

            onu_objects.return_value = [onu]

            self.policy.handle_update(self.si)
            self.assertEqual(subscriber_save.call_count, 1)

            subscriber = subscriber_save.call_args[0][0]
            self.assertEqual(subscriber.onu_device, self.si.serial_number)

            onu_save.assert_not_called()
    
    def test_create_subscriber_no_create_on_discovery(self):
        """
        test_create_subscriber_no_create_on_discovery
        When si.owner.create_on_discovery = False we still need to create the subscriber after authentication
        """

        self.si.valid = "valid"
        self.si.serial_number = "BRCM1234"
        self.si.backend_code = 1
        self.si.owner.leaf_model.create_on_discovery = False
        self.si.authentication_state = "APPROVED"

        onu = ONUDevice(
            serial_number=self.si.serial_number,
            admin_state="ENABLED"
        )

        with patch.object(ONUDevice.objects, "get_items") as onu_objects, \
                patch.object(RCORDSubscriber, "save", autospec=True) as subscriber_save, \
                patch.object(ONUDevice, "save") as onu_save:

            onu_objects.return_value = [onu]

            self.policy.handle_update(self.si)
            self.assertEqual(subscriber_save.call_count, 1)

            subscriber = subscriber_save.call_args[0][0]
            self.assertEqual(subscriber.onu_device, self.si.serial_number)

            onu_save.assert_not_called()

    def test_create_subscriber_with_ctag(self):
        self.si.valid = "valid"
        self.si.serial_number = "BRCM1234"
        self.si.c_tag = 111
        self.si.backend_code = 1

        onu = ONUDevice(
            serial_number=self.si.serial_number,
            admin_state="ENABLED"
        )

        with patch.object(ONUDevice.objects, "get_items") as onu_objects, \
                patch.object(RCORDSubscriber, "save", autospec=True) as subscriber_save, \
                patch.object(ONUDevice, "save") as onu_save:

            onu_objects.return_value = [onu]

            self.policy.handle_update(self.si)
            self.assertEqual(subscriber_save.call_count, 1)

            subscriber = subscriber_save.call_args[0][0]
            self.assertEqual(subscriber.onu_device, self.si.serial_number)
            self.assertEqual(subscriber.c_tag, self.si.c_tag)

            onu_save.assert_not_called()

    def _test_add_c_tag_to_pre_provisioned_subscriber(self):
        self.si.valid = "valid"
        self.si.serial_number = "BRCM1234"
        self.si.c_tag = 111
        self.si.backend_code = 1

        onu = ONUDevice(
            serial_number=self.si.serial_number,
            admin_state="ENABLED"
        )

        subscriber = RCORDSubscriber(
            onu_device=self.si.serial_number,
        )

        with patch.object(ONUDevice.objects, "get_items") as onu_objects, \
                patch.object(RCORDSubscriber.objects, "get_items") as subscriber_objects, \
                patch.object(RCORDSubscriber, "save", autospec=True) as subscriber_save, \
                patch.object(ONUDevice, "save") as onu_save:

            onu_objects.return_value = [onu]
            subscriber_objects.return_value = [subscriber]

            self.policy.handle_update(self.si)
            self.assertEqual(subscriber_save.call_count, 1)

            subscriber = subscriber_save.call_args[0][0]
            self.assertEqual(subscriber.onu_device, self.si.serial_number)
            self.assertEqual(subscriber.c_tag, self.si.c_tag)

            onu_save.assert_not_called()

if __name__ == '__main__':
    unittest.main()

