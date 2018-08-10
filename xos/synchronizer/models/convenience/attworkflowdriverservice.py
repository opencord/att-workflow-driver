
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


# validate_onu received event:
# {
#     'status': 'activate',
#     'serial_number': 'BRCM1234',
#     'of_dpid': 'of:109299321'
# }

from xosapi.orm import register_convenience_wrapper
from xosapi.convenience.serviceinstance import ORMWrapperServiceInstance

import logging as log

class ORMWrapperAttWorkflowService(ORMWrapperServiceInstance):

    def validate_onu(self, event):

        log.info("onu.events: validating ONU %s" % event["serial_number"], event=event)

        try:
            oss_si = self.stub.AttWorkflowDriverServiceInstance.objects.get(serial_number=event["serial_number"])
            oss_si.no_sync = False;
            log.debug("onu.events: Found existing AttWorkflowDriverServiceInstance", si=oss_si)
        except IndexError:
            # create an AttWorkflowDriverServiceInstance, the validation will be triggered in the corresponding sync step
            oss_si = self.stub.AttWorkflowDriverServiceInstance(
                serial_number=event["serial_number"],
                of_dpid=event["of_dpid"]
            )
            log.debug("onu.events: Created new AttWorkflowDriverServiceInstance", si=oss_si)
        
        oss_si.save(always_update_timestamp=True)

register_convenience_wrapper("AttWorkflowDriverService", ORMWrapperAttWorkflowService)
