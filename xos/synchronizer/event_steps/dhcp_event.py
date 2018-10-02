
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
from synchronizers.new_base.modelaccessor import VOLTService, RCORDSubscriber, model_accessor

class SubscriberDhcpEventStep(EventStep):
    topics = ["dhcp.events"]
    technology = "kafka"

    def __init__(self, *args, **kwargs):
        super(SubscriberDhcpEventStep, self).__init__(*args, **kwargs)

    def get_onu_sn(self, event):
        olt_service = VOLTService.objects.first()
        onu_sn = olt_service.get_onu_sn_from_openflow(event["deviceId"], event["portNumber"])
        if not onu_sn or onu_sn is None:
            self.log.exception("dhcp.events: Cannot find onu serial number for this event", kafka_event=event)
            raise Exception("dhcp.events: Cannot find onu serial number for this event")

        return onu_sn

    def process_event(self, event):
        value = json.loads(event.value)

        onu_sn = self.get_onu_sn(value)

        subscriber = RCORDSubscriber.objects.get(onu_device=onu_sn)

        self.log.info("dhcp.events: Got event for subscriber", subscriber=subscriber, event_value=value, onu_sn=onu_sn)

        # NOTE it will be better to update the SI and use the model policy to update the subscriber,
        # if this fails for any reason the event is lost
        if subscriber.ip_address != value["ipAddress"] or \
            subscriber.mac_address != value["macAddress"]:

            # FIXME apparently it's always saving
            subscriber.ip_address = value["ipAddress"]
            subscriber.mac_address = value["macAddress"]
            subscriber.save()
