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

import json
from synchronizers.new_base.syncstep import SyncStep, model_accessor
from synchronizers.new_base.modelaccessor import AttWorkflowDriverServiceInstance, AttWorkflowDriverWhiteListEntry

from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))

class SyncAttWorkflowDriverServiceInstance(SyncStep):
    provides = [AttWorkflowDriverServiceInstance]
    observes = AttWorkflowDriverServiceInstance

    def validate_in_external_oss(self, si):
        # This is where you may want to call your OSS Database to verify if this ONU can be activated
        oss_service = si.owner.leaf_model

        # See if there is a matching entry in the whitelist.

        matching_entries = AttWorkflowDriverWhiteListEntry.objects.filter(owner_id=oss_service.id,
                                                                  serial_number=si.serial_number)

        return len(matching_entries)>0

    def get_suscriber_c_tag(self, serial_number):
        # If it's up to your OSS to generate c_tags, fetch them here
        # otherwise XOS will generate one for your subscriber
        return None

    def sync_record(self, o):
        log.info("synching AttWorkflowDriverServiceInstance", object=str(o), **o.tologdict())

        if not self.validate_in_external_oss(o):
            log.error("ONU with serial number %s is not valid in the OSS Database" % o.serial_number)
            o.valid = "invalid"
        else:
            if self.get_suscriber_c_tag(o.serial_number):
                self.c_tag = self.get_suscriber_c_tag(o.serial_number)

            o.valid = "valid"

        # Set no_sync=True to prevent the syncstep from running again, and set alway_update_timestamp=True to cause
        # the model_policy to run again.
        # TODO(smbaker): Revisit this after fixing this issue in the core.
        o.no_sync = True
        o.save(update_fields=["valid", "no_sync", "updated"], always_update_timestamp=True)

    def delete_record(self, o):
        pass
