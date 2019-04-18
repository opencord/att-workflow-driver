
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
from xossynchronizer.event_steps.eventstep import EventStep
from helpers import AttHelpers


class ONUEventStep(EventStep):
    topics = ["onu.events"]
    technology = "kafka"

    max_onu_retry = 50

    def __init__(self, *args, **kwargs):
        super(ONUEventStep, self).__init__(*args, **kwargs)

    def process_event(self, event):
        value = json.loads(event.value)
        self.log.info("onu.events: received event", value=value)

        if value["status"] == "activated":
            self.log.info("onu.events: activated onu", value=value)
            att_si = AttHelpers.find_or_create_att_si(self.model_accessor, self.log, value)
            att_si.no_sync = False
            att_si.uni_port_id = long(value["portNumber"])
            att_si.of_dpid = value["deviceId"]
            att_si.onu_state = "ENABLED"
            att_si.save_changed_fields(always_update_timestamp=True)
        elif value["status"] == "disabled":
            self.log.info("onu.events: disabled onu, not taking any action", value=value)
            return
        else:
            self.log.warn("onu.events: Unknown status value: %s" % value["status"], value=value)
            return
