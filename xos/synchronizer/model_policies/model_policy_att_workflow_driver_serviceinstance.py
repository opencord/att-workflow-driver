
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


from synchronizers.new_base.modelaccessor import RCORDSubscriber, ONUDevice, model_accessor
from synchronizers.new_base.policy import Policy

class DeferredException(Exception):
    pass

class AttWorkflowDriverServiceInstancePolicy(Policy):
    model_name = "AttWorkflowDriverServiceInstance"

    def handle_create(self, si):
        self.logger.debug("MODEL_POLICY: handle_create for AttWorkflowDriverServiceInstance %s " % si.id)
        self.handle_update(si)

    def handle_update(self, si):

        # TODO if si.onu_state = DISABLED set subscriber.status to need_auth
        # TODO cleanup

        self.logger.debug("MODEL_POLICY: handle_update for AttWorkflowDriverServiceInstance %s, valid=%s " % (si.id, si.valid))

        # Check to make sure the object has been synced. This is to cover a race condition where the model_policy
        # runs, is interrupted by the sync step, the sync step completes, and then the model policy ends up saving
        # a policed_timestamp that is later the updated timestamp set by the sync_step.
        if (si.backend_code!=1):
            raise DeferredException("MODEL_POLICY: AttWorkflowDriverServiceInstance %s has not been synced yet" % si.id)

        # waiting for Whitelist validation
        if not hasattr(si, 'valid') or si.valid is "awaiting":
            raise DeferredException("MODEL_POLICY: deferring handle_update for AttWorkflowDriverServiceInstance %s as not validated yet" % si.id)

        # disabling ONU
        if si.valid == "invalid":
            self.logger.debug("MODEL_POLICY: disabling ONUDevice [%s] for AttWorkflowDriverServiceInstance %s" % (si.serial_number, si.id))
            onu = ONUDevice.objects.get(serial_number=si.serial_number)
            onu.admin_state = "DISABLED"
            onu.save(always_update_timestamp=True)
            return
        if si.valid == "valid":

            # reactivating the ONUDevice
            try:
                onu = ONUDevice.objects.get(serial_number=si.serial_number)
            except IndexError:
                raise Exception("MODEL_POLICY: cannot find ONUDevice [%s] for AttWorkflowDriverServiceInstance %s" % (si.serial_number, si.id))
            if onu.admin_state == "DISABLED":
                self.logger.debug("MODEL_POLICY: enabling ONUDevice [%s] for AttWorkflowDriverServiceInstance %s" % (si.serial_number, si.id))
                onu.admin_state = "ENABLED"
                onu.save(always_update_timestamp=True)

            # handling the subscriber status

            subscriber = None
            try:
                subscriber = [s for s in RCORDSubscriber.objects.all() if s.onu_device.lower() == si.serial_number.lower()][0]
            except IndexError:
                # we just want to find out if it exists or not
                pass

            if subscriber:
                # if the subscriber is there and authentication is complete, update its state
                self.logger.debug("MODEL_POLICY: handling subscriber", onu_device=si.serial_number, authentication_state=si.authentication_state, onu_state=si.onu_state)
                if si.onu_state == "DISABLED":
                    # NOTE do not mess with onu.admin_state as that triggered this condition
                    subscriber.status = "awaiting-auth"
                elif si.authentication_state == "STARTED":
                    subscriber.status = "awaiting-auth"
                elif si.authentication_state == "REQUESTED":
                    subscriber.status = "awaiting-auth"
                elif si.authentication_state == "APPROVED":
                    subscriber.status = "enabled"
                elif si.authentication_state == "DENIED":
                    subscriber.status = "auth-failed"

                subscriber.save(always_update_timestamp=True)
            # if subscriber does not exist
            else:
                self.logger.warn("MODEL_POLICY: subscriber does not exists for this SI, doing nothing")

    def handle_delete(self, si):
        pass
