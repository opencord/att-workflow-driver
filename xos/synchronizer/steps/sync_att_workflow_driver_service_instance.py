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
from synchronizers.new_base.modelaccessor import AttWorkflowDriverServiceInstance, AttWorkflowDriverWhiteListEntry, ONUDevice

from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))

class SyncAttWorkflowDriverServiceInstance(SyncStep):
    provides = [AttWorkflowDriverServiceInstance]
    observes = AttWorkflowDriverServiceInstance

    def validate_onu(self, si):
        # This is where you may want to call your OSS Database to verify if this ONU can be activated
        oss_service = si.owner.leaf_model

        # See if there is a matching entry in the whitelist.

        matching_entries = AttWorkflowDriverWhiteListEntry.objects.filter(owner_id=oss_service.id,
                                                                  serial_number=si.serial_number)

        # check that it's in the whitelist
        if len(matching_entries) == 0:
            log.warn("ONU disable as not in whitelist", object=str(si), serial_number=si.serial_number, **si.tologdict())
            return False

        whitelisted = matching_entries[0]

        # FIXME if the ONU is not there yet it raise an index error, if that happens raise DeferredException
        pon_port = ONUDevice.objects.get(serial_number=si.serial_number).pon_port
        if pon_port.port_no != whitelisted.pon_port_id or si.of_dpid != whitelisted.device_id:
            log.warn("ONU disable as location don't match", object=str(si), serial_number=si.serial_number,
                     **si.tologdict())
            return False

        return True

    def sync_record(self, si):
        log.info("synching AttWorkflowDriverServiceInstance", object=str(si), **si.tologdict())

        if not self.validate_onu(si):
            log.error("ONU with serial number %s is not valid in the OSS Database" % si.serial_number)
            si.valid = "invalid"
        else:
            si.valid = "valid"

        si.save()

    def delete_record(self, o):
        pass
