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

from xossynchronizer.steps.syncstep import DeferredException

class AttHelpers():
    @staticmethod
    def validate_onu(model_accessor, log, att_si):
        """
        This method validate an ONU against the whitelist and set the appropriate state.
        It's expected that the deferred exception is managed in the caller method,
        for example a model_policy or a sync_step.

        :param att_si: AttWorkflowDriverServiceInstance
        :return: [boolean, string]
        """

        oss_service = att_si.owner.leaf_model

        # See if there is a matching entry in the whitelist.
        matching_entries = model_accessor.AttWorkflowDriverWhiteListEntry.objects.filter(
            owner_id=oss_service.id,
        )
        matching_entries = [e for e in matching_entries if e.serial_number.lower() == att_si.serial_number.lower()]

        if len(matching_entries) == 0:
            log.warn("ONU not found in whitelist", object=str(att_si), serial_number=att_si.serial_number, **att_si.tologdict())
            return [False, "ONU not found in whitelist"]

        whitelisted = matching_entries[0]
        try:
            pon_port = model_accessor.ONUDevice.objects.get(serial_number=att_si.serial_number).pon_port
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
    def find_or_create_att_si(model_accessor, log, event):
        try:
            att_si = model_accessor.AttWorkflowDriverServiceInstance.objects.get(
                serial_number=event["serialNumber"]
            )
            log.debug("AttHelpers: Found existing AttWorkflowDriverServiceInstance", si=att_si)
        except IndexError:
            # create an AttWorkflowDriverServiceInstance, the validation will be
            # triggered in the corresponding sync step
            att_si = model_accessor.AttWorkflowDriverServiceInstance(
                serial_number=event["serialNumber"],
                of_dpid=event["deviceId"],
                uni_port_id=long(event["portNumber"]),
                # we assume there is only one AttWorkflowDriverService
                owner=model_accessor.AttWorkflowDriverService.objects.first()
            )
            log.debug("AttHelpers: Created new AttWorkflowDriverServiceInstance", si=att_si)
        return att_si
