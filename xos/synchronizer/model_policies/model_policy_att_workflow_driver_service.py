
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


from synchronizers.new_base.modelaccessor import AttWorkflowDriverServiceInstance, model_accessor
from synchronizers.new_base.policy import Policy

class AttWorkflowDriverServicePolicy(Policy):
    model_name = "AttWorkflowDriverService"

    def handle_update(self, service):
        self.logger.debug("MODEL_POLICY: handle_update for AttWorkflowDriverService", oss=service)

        sis = AttWorkflowDriverServiceInstance.objects.all()

        # TODO(teone): use the method defined in helpers.py

        whitelist = [x.serial_number.lower() for x in service.whitelist_entries.all()]

        for si in sis:
            if si.serial_number.lower() in whitelist and not si.valid == "valid":
                self.logger.debug("MODEL_POLICY: activating AttWorkflowDriverServiceInstance because of change in the whitelist", si=si)
                si.valid = "valid"
                si.save(update_fields=["valid", "no_sync", "updated"], always_update_timestamp=True)
            if si.serial_number.lower() not in whitelist and not si.valid == "invalid":
                self.logger.debug(
                    "MODEL_POLICY: disabling AttWorkflowDriverServiceInstance because of change in the whitelist", si=si)
                si.valid = "invalid"
                si.save(update_fields=["valid", "no_sync", "updated"], always_update_timestamp=True)


    def handle_delete(self, si):
        pass
