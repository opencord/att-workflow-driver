
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
import time
import os
import sys
from synchronizers.new_base.eventstep import EventStep
from synchronizers.new_base.modelaccessor import AttWorkflowDriverService, AttWorkflowDriverServiceInstance, model_accessor

class ONUEventStep(EventStep):
    topics = ["onu.events"]
    technology = "kafka"

    max_onu_retry = 50

    def __init__(self, *args, **kwargs):
        super(ONUEventStep, self).__init__(*args, **kwargs)

    def get_att_si(self, event):
        try:
            att_si = AttWorkflowDriverServiceInstance.objects.get(serial_number=event["serial_number"])
            att_si.no_sync = False;
            att_si.uni_port_id = event["uni_port_id"]
            att_si.of_dpid = event["of_dpid"]
            self.log.debug("onu.events: Found existing AttWorkflowDriverServiceInstance", si=att_si)
        except IndexError:
            # create an AttWorkflowDriverServiceInstance, the validation will be triggered in the corresponding sync step
            att_si = AttWorkflowDriverServiceInstance(
                serial_number=event["serial_number"],
                of_dpid=event["of_dpid"],
                uni_port_id=event["uni_port_id"],
                owner=AttWorkflowDriverService.objects.first() # we assume there is only one AttWorkflowDriverService
            )
            self.log.debug("onu.events: Created new AttWorkflowDriverServiceInstance", si=att_si)
        return att_si

    def process_event(self, event):
        value = json.loads(event.value)
        self.log.info("onu.events: received event", value=value)

        att_si = self.get_att_si(value)
        if value["status"] == "activated":
            self.log.info("onu.events: activated onu", value=value)
            att_si.onu_state = "ENABLED"
        elif value["status"] == "disabled":
            self.log.info("onu.events: disabled onu", value=value)
            att_si.onu_state = "DISABLED"
            att_si.authentication_state = "AWAITING"
        att_si.save(always_update_timestamp=True)


