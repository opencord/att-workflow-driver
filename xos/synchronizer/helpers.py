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

from synchronizers.new_base.syncstep import DeferredException
from synchronizers.new_base.modelaccessor import AttWorkflowDriverWhiteListEntry, AttWorkflowDriverServiceInstance, ONUDevice, VOLTService, model_accessor

class AttHelpers():
    @staticmethod
    def validate_onu(log, att_si):
        """
        This method validate an ONU against the whitelist and set the appropriate state.
        It's expected that the deferred exception is managed in the caller method,
        for example a model_policy or a sync_step.

        :param att_si: AttWorkflowDriverServiceInstance
        :return: [boolean, string]
        """

        oss_service = att_si.owner.leaf_model

        # See if there is a matching entry in the whitelist.
        matching_entries = AttWorkflowDriverWhiteListEntry.objects.filter(
            owner_id=oss_service.id,
        )
        matching_entries = [e for e in matching_entries if e.serial_number.lower() == att_si.serial_number.lower()]

        if len(matching_entries) == 0:
            log.warn("ONU not found in whitelist", object=str(att_si), serial_number=att_si.serial_number, **att_si.tologdict())
            return [False, "ONU not found in whitelist"]

        whitelisted = matching_entries[0]
        try:
            pon_port = ONUDevice.objects.get(serial_number=att_si.serial_number).pon_port
        except IndexError:
            raise DeferredException("ONU device %s is not know to XOS yet" % att_si.serial_number)

        if pon_port.port_no != whitelisted.pon_port_id or att_si.of_dpid != whitelisted.device_id:
            log.warn("ONU disable as location don't match",
                     object=str(att_si),
                     serial_number=att_si.serial_number,
                     pon_port=pon_port.port_no,
                     whitelisted_pon_port=whitelisted.pon_port_id,
                     device_id=att_si.of_dpid,
                     whitelisted_device_id=whitelisted.device_id,
                     **att_si.tologdict())
            return [False, "ONU activated in wrong location"]

        return [True, "ONU has been validated"]

    @staticmethod
    def get_onu_sn(log, event):
        olt_service = VOLTService.objects.first()
        onu_sn = olt_service.get_onu_sn_from_openflow(event["deviceId"], event["portNumber"])
        if not onu_sn or onu_sn is None:
            log.exception("Cannot find onu serial number for this event", kafka_event=event)
            raise Exception("Cannot find onu serial number for this event")

        return onu_sn

    @staticmethod
    def get_si_by_sn(log, serial_number):
        try:
            return AttWorkflowDriverServiceInstance.objects.get(serial_number=serial_number)
        except IndexError:
            log.exception("Cannot find att-workflow-driver service instance for this serial number", serial_number=serial_number)
            raise Exception("Cannot find att-workflow-driver service instance for this serial number %s", serial_number)