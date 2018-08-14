
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
from synchronizers.new_base.modelaccessor import AttWorkflowDriverServiceInstance, model_accessor

class ONUEventStep(EventStep):
    topics = ["onu.events"]
    technology = "kafka"

    max_onu_retry = 50

    def __init__(self, *args, **kwargs):
        super(ONUEventStep, self).__init__(*args, **kwargs)

    def handle_onu_activate_event(self, event):

        # NOTE do we need to wait of the ONU to be there?

        self.log.info("onu.events: validating ONU %s" % event["serial_number"], event_data=event)

        try:
            att_si = AttWorkflowDriverServiceInstance.objects.get(serial_number=event["serial_number"])
            att_si.no_sync = False;
            self.log.debug("onu.events: Found existing AttWorkflowDriverServiceInstance", si=att_si)
        except IndexError:
            # create an AttWorkflowDriverServiceInstance, the validation will be triggered in the corresponding sync step
            att_si = AttWorkflowDriverServiceInstance(
                serial_number=event["serial_number"],
                of_dpid=event["of_dpid"],
                uni_port_id=event["uni_port_id"]
            )
            self.log.debug("onu.events: Created new AttWorkflowDriverServiceInstance", si=att_si)
        att_si.save()

    def process_event(self, event):
        value = json.loads(event.value)
        self.log.info("onu.events: received event", value=value)

        if value["status"] == "activated":
            self.log.info("onu.events: activate onu", value=value)
            self.handle_onu_activate_event(value)

