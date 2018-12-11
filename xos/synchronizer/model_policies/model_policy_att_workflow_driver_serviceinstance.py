
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



from synchronizers.new_base.modelaccessor import RCORDSubscriber, RCORDIpAddress, ONUDevice, model_accessor
from synchronizers.new_base.policy import Policy

import os
import sys

sync_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
sys.path.append(sync_path)

from helpers import AttHelpers

class DeferredException(Exception):
    pass

class AttWorkflowDriverServiceInstancePolicy(Policy):
    model_name = "AttWorkflowDriverServiceInstance"

    def handle_create(self, si):
        self.logger.debug("MODEL_POLICY: handle_create for AttWorkflowDriverServiceInstance %s " % si.id)
        self.handle_update(si)

    def handle_update(self, si):
        self.logger.debug("MODEL_POLICY: handle_update for AttWorkflowDriverServiceInstance %s " % (si.id), onu_state=si.onu_state, authentication_state=si.authentication_state)

        # validating ONU
        if si.onu_state == "AWAITING" or si.onu_state == "ENABLED":
            # we validate the ONU state only if it is enabled or awaiting,
            # if it's disabled it means someone has disabled it
            self.validate_onu_state(si)
        else:
            # clean the status and verify that the ONU is actually disabled
            si.status_message = "ONU has been disabled"
            self.update_onu(si.serial_number, "DISABLED")

        # handling the subscriber status
        subscriber = self.get_subscriber(si.serial_number)

        if subscriber:
            self.update_subscriber(subscriber, si)

        if si.authentication_state in ["AWAITING", "REQUESTED", "STARTED"]:
            si.ip_address = ""
            si.mac_address = ""
            si.dhcp_state = ""

        si.save_changed_fields()

    def validate_onu_state(self, si):
        [valid, message] = AttHelpers.validate_onu(self.logger, si)
        si.status_message = message
        if valid:
            si.onu_state = "ENABLED"
            self.update_onu(si.serial_number, "ENABLED")
        else:
            si.onu_state = "DISABLED"
            self.update_onu(si.serial_number, "DISABLED")

    def update_onu(self, serial_number, admin_state):
        onu = [onu for onu in ONUDevice.objects.all() if onu.serial_number.lower() == serial_number.lower()][0]
        if onu.admin_state == admin_state:
            self.logger.debug("MODEL_POLICY: ONUDevice [%s] already has admin_state to %s" % (serial_number, admin_state))
        else:
            self.logger.debug("MODEL_POLICY: setting ONUDevice [%s] admin_state to %s" % (serial_number, admin_state))
            onu.admin_state = admin_state
            onu.save_changed_fields(always_update_timestamp=True)

    def get_subscriber(self, serial_number):
        try:
            return [s for s in RCORDSubscriber.objects.all() if s.onu_device.lower() == serial_number.lower()][0]
        except IndexError:
            # If the subscriber doesn't exist we don't do anything
            self.logger.debug("MODEL_POLICY: subscriber does not exists for this SI, doing nothing", onu_device=serial_number)
            return None

    def update_subscriber_ip(self, subscriber, ip):
        # TODO check if the subscriber has an IP and update it,
        # or create a new one
        try:
            ip = RCORDIpAddress.objects.filter(
                subscriber_id=subscriber.id,
                ip=ip
            )[0]
            self.logger.debug("MODEL_POLICY: found existing RCORDIpAddress for subscriber", onu_device=subscriber.onu_device, subscriber_status=subscriber.status, ip=ip)
            ip.save_changed_fields()
        except IndexError:
            self.logger.debug("MODEL_POLICY: Creating new RCORDIpAddress for subscriber", onu_device=subscriber.onu_device, subscriber_status=subscriber.status, ip=ip)
            ip = RCORDIpAddress(
                subscriber_id=subscriber.id,
                ip=ip,
                description="DHCP Assigned IP Address"
            )
            ip.save()

    def delete_subscriber_ip(self, subscriber, ip):
        try:
            ip = RCORDIpAddress.objects.filter(
                subscriber_id=subscriber.id,
                ip=ip
            )[0]
            self.logger.debug("MODEL_POLICY: delete RCORDIpAddress for subscriber", onu_device=subscriber.onu_device, subscriber_status=subscriber.status, ip=ip)
            ip.delete()
        except:
            self.logger.warning("MODEL_POLICY: no RCORDIpAddress object found, cannot delete", ip=ip)

    def update_subscriber(self, subscriber, si):
        cur_status = subscriber.status
        if si.authentication_state == "AWAITING":
            subscriber.status = "awaiting-auth"
            si.status_message += " - Awaiting Authentication"
        elif si.authentication_state == "REQUESTED":
            subscriber.status = "awaiting-auth"
            si.status_message += " - Authentication requested"
        elif si.authentication_state == "STARTED":
            subscriber.status = "awaiting-auth"
            si.status_message += " - Authentication started"
        elif si.authentication_state == "APPROVED":
            subscriber.status = "enabled"
            si.status_message += " - Authentication succeded"
        elif si.authentication_state == "DENIED":
            subscriber.status = "auth-failed"
            si.status_message += " - Authentication denied"

        # NOTE we save the subscriber only if:
        # - the status has changed
        # - we get a DHCPACK event
        if cur_status != subscriber.status or si.dhcp_state == "DHCPACK":
            self.logger.debug("MODEL_POLICY: updating subscriber", onu_device=subscriber.onu_device, authentication_state=si.authentication_state, subscriber_status=subscriber.status)
            if subscriber.status == "awaiting-auth":
                self.delete_subscriber_ip(subscriber, si.ip_address)
                subscriber.mac_address = ""
            elif si.ip_address and si.mac_address:
                self.update_subscriber_ip(subscriber, si.ip_address)
                subscriber.mac_address = si.mac_address
            subscriber.save_changed_fields(always_update_timestamp=True)
        else:
            self.logger.debug("MODEL_POLICY: subscriber status has not changed", onu_device=subscriber.onu_device,
                              authentication_state=si.authentication_state, subscriber_status=subscriber.status)

    def handle_delete(self, si):
        pass
