
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
import os
import sys

sync_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
sys.path.append(sync_path)

from helpers import AttHelpers

class AttWorkflowDriverWhiteListEntryPolicy(Policy):
    model_name = "AttWorkflowDriverWhiteListEntry"

    def handle_create(self, whitelist):
        self.handle_update(whitelist)

    def validate_onu_state(self, si):
        [valid, message] = AttHelpers.validate_onu(si)
        si.status_message = message
        if valid:
            si.onu_state = "ENABLED"
        else:
            si.onu_state = "DISABLED"
            si.authentication_state = "AWAITING"

        self.logger.debug(
            "MODEL_POLICY: activating AttWorkflowDriverServiceInstance because of change in the whitelist", si=si, onu_state=si.onu_state, authentication_state=si.authentication_state)
        si.save(update_fields=["no_sync", "updated", "onu_state", "status_message", "authentication_state"], always_update_timestamp=True)

    def handle_update(self, whitelist):
        self.logger.debug("MODEL_POLICY: handle_update for AttWorkflowDriverWhiteListEntry", whitelist=whitelist)

        sis = AttWorkflowDriverServiceInstance.objects.all()

        for si in sis:

            if si.serial_number.lower() != whitelist.serial_number.lower():
                # NOTE we don't care about this SI as it has a different serial number
                continue

            self.validate_onu_state(si)

        whitelist.backend_need_delete_policy=True
        whitelist.save(update_fields=["backend_need_delete_policy"])

    def handle_delete(self, whitelist):
        self.logger.debug("MODEL_POLICY: handle_delete for AttWorkflowDriverWhiteListEntry", whitelist=whitelist)

        # BUG: Sometimes the delete policy is not called, because the reaper deletes

        assert(whitelist.owner)

        sis = AttWorkflowDriverServiceInstance.objects.all()
        sis = [si for si in sis if si.serial_number.lower() == whitelist.serial_number.lower()]

        for si in sis:
            self.validate_onu_state(si)

        whitelist.backend_need_reap=True
        whitelist.save(update_fields=["backend_need_reap"])
