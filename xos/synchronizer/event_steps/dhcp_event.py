
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


class SubscriberDhcpEventStep(EventStep):
    topics = ["dhcp.events"]
    technology = "kafka"

    def __init__(self, *args, **kwargs):
        super(SubscriberDhcpEventStep, self).__init__(*args, **kwargs)

    def process_event(self, event):
        value = json.loads(event.value)

        onu_sn = AttHelpers.get_onu_sn(self.model_accessor, self.log, value)
        si = AttHelpers.get_si_by_sn(self.model_accessor, self.log, onu_sn)

        if not si:
            self.log.exception(
                "dhcp.events: Cannot find att-workflow-driver service instance for this event",
                kafka_event=value)
            raise Exception("dhcp.events: Cannot find att-workflow-driver service instance for this event")

        self.log.info("dhcp.events: Got event for subscriber", event_value=value, onu_sn=onu_sn, si=si)

        si.dhcp_state = value["messageType"]
        si.ip_address = value["ipAddress"]
        si.mac_address = value["macAddress"]

        si.save_changed_fields(always_update_timestamp=True)
