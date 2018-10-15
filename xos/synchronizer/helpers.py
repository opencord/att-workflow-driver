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
from synchronizers.new_base.modelaccessor import AttWorkflowDriverWhiteListEntry, ONUDevice, model_accessor

from xosconfig import Config
from multistructlog import create_logger
import threading

threadLocal = threading.local()

log = create_logger(Config().get('logging'))

class AttHelpers():

    @staticmethod
    def validate_onu(att_si):
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
            log.warn("ONU disable as location don't match", object=str(att_si), serial_number=att_si.serial_number,
                     **att_si.tologdict())
            return [False, "ONU activated in wrong location"]

        return [True, "ONU has been validated"]

    @staticmethod
    def init_state(obj):
        if not getattr(threadLocal, "atthelper", None):
            threadLocal.atthelper = {}
        if obj not in threadLocal.atthelper:
            threadLocal.atthelper[obj] = {}
            threadLocal.atthelper[obj]["new"] = False
            threadLocal.atthelper[obj]["update_fields"] = []

    @staticmethod
    def get_object_dict(obj):
        AttHelpers.init_state(obj)
        return threadLocal.atthelper[obj]

    @staticmethod
    def delete_object_dict(obj):
        del threadLocal.atthelper[obj]

    @staticmethod
    def new_object(obj):
        odict = AttHelpers.get_object_dict(obj)
        odict["new"] = True

    @staticmethod
    def update_field(obj, name, value):
        odict = AttHelpers.get_object_dict(obj)
        oldvalue = getattr(obj, name)
        if oldvalue != value:
            setattr(obj, name, value)
            if name not in odict:
                odict[name] = oldvalue
            if odict["update_fields"]:
                if name not in odict["update_fields"]:
                    odict["update_fields"].append(name)
            else:
                odict["update_fields"] = ["updated", name]

    @staticmethod
    def save_object(obj, always_update_timestamp=False):
        if obj not in threadLocal.atthelper:
            log.warn("save_object: Object not found in dictionary, not saving", object=str(obj), **obj.tologdict())
            return
        odict = AttHelpers.get_object_dict(obj)
        if odict["new"]:
            obj.save(always_update_timestamp=always_update_timestamp)
        elif odict["update_fields"]:
            # Prune out values that didn't change.  Iterate over a copy of the list.
            for field in list(odict["update_fields"]):
                if field != "updated" and getattr(obj, field) == odict[field]:
                    odict["update_fields"].remove(field)
                    log.debug("save_object: field %s did not change, not saving" % field)
            # "updated" field is always there
            if len(odict["update_fields"]) > 1:
                obj.save(update_fields=sorted(odict["update_fields"]), always_update_timestamp=always_update_timestamp)
        AttHelpers.delete_object_dict(obj)
