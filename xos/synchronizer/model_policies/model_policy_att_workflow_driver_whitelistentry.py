
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


from synchronizers.new_base.modelaccessor import AttWorkflowDriverServiceInstance, AttWorkflowDriverWhiteListEntry, model_accessor
from synchronizers.new_base.policy import Policy

class AttWorkflowDriverWhiteListEntryPolicy(Policy):
    model_name = "AttWorkflowDriverWhiteListEntry"

    def handle_create(self, whitelist):
        self.handle_update(whitelist)

    def handle_update(self, whitelist):
        self.logger.debug("MODEL_POLICY: handle_update for AttWorkflowDriverWhiteListEntry", whitelist=whitelist)

        # TODO is Django construct '__iexact' available here?
        # sis = AttWorkflowDriverServiceInstance.objects.filter(
        #     serial_number = whitelist.serial_number,
        #     owner_id = whitelist.owner.id)

        sis = AttWorkflowDriverServiceInstance.objects.all()

        for si in sis:

            if si.serial_number.lower() != whitelist.serial_number.lower():
                # NOTE we don't care about this SI as it has a different serial number
                continue

            if si.valid != "valid":
                self.logger.debug("MODEL_POLICY: activating AttWorkflowDriverServiceInstance because of change in the whitelist", si=si)
                si.valid = "valid"
                si.save(update_fields=["valid", "no_sync", "updated"], always_update_timestamp=True)

        whitelist.backend_need_delete_policy=True
        whitelist.save(update_fields=["backend_need_delete_policy"])

    def handle_delete(self, whitelist):
        self.logger.debug("MODEL_POLICY: handle_delete for AttWorkflowDriverWhiteListEntry", whitelist=whitelist)

        # BUG: Sometimes the delete policy is not called, because the reaper deletes

        assert(whitelist.owner)

        sis = AttWorkflowDriverServiceInstance.objects.filter(serial_number = whitelist.serial_number,
                                                   owner_id = whitelist.owner.id)

        for si in sis:
            if si.valid != "invalid":
                self.logger.debug(
                    "MODEL_POLICY: disabling AttWorkflowDriverServiceInstance because of change in the whitelist", si=si)
                si.valid = "invalid"
                si.save(update_fields=["valid", "no_sync", "updated"], always_update_timestamp=True)

        whitelist.backend_need_reap=True
        whitelist.save(update_fields=["backend_need_reap"])
