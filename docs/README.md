# AT&T Workflow Driver Service

This service implements the ONU and Subscriber management logic required by AT&T.
It's also a good start if you need to implement different logic to suit your use case.

> NOTE: This service depends on models contained in the R-CORD and OLT Services, so make sure that the `rcord-synchronizer` and `volt-synchronzier` are running

## Models

This service is composed of the following models:

- `AttWorkflowDriverServiceInstance`. This model holds various state associated with the state machine for validating a subscriber's ONU.
    - `serial_number`. Serial number of ONU.
    - `authentication_state`. [`AWAITING` | `STARTED` | `REQUESTED` | `APPROVED` | `DENIED`]. Current authentication state.
    - `of_dpid`. OLT Openflow ID.
    - `uni_port_id`. ONU UNI Port ID.
    - `onu_state`. [`AWAITING` | `ENABLED` | `DISABLED`]. State of the ONU.
    - `status_message`. Status text of current state machine state.
    - `dhcp_state`. [`AWAITING` | `DHCPDISCOVER` | `DHCPACK` | `DHCPREQUEST`]. Current DHCP state.
    - `ip_address`. Subscriber ip address.
    - `mac_address`. Subscriber mac address.
    - `oper_onu_status`. [`AWAITING` | `ENABLED` | `DISABLED`]. ONU operational state.
- `AttWorkflowDriverWhiteListEntry`. This model holds a whitelist authorizing an ONU with a specific serial number to be connected to a specific PON Port on a specific OLT.
    - `owner`. Relation to the AttWorkflowDriverService that owns this whitelist entry.
    - `serial_number`. Serial number of ONU.
    - `pon_port_id`. Pon port identifier.
    - `device_id`. OLT device identifier.

## Example Tosca - Create a whitelist entry

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
imports:
  - custom_types/attworkflowdriverwhitelistentry.yaml
  - custom_types/attworkflowdriverservice.yaml
description: Create an entry in the whitelist
topology_template:
  node_templates:

    service#att:
      type: tosca.nodes.AttWorkflowDriverService
      properties:
        name: att-workflow-driver
        must-exist: true

    whitelist:
      type: tosca.nodes.AttWorkflowDriverWhiteListEntry
      properties:
        serial_number: BRCM22222222
        pon_port_id: 536870912
        device_id: of:000000000a5a0072
      requirements:
        - owner:
            node: service#att
            relationship: tosca.relationships.BelongsToOne
```

## Integration with other Services

This service integrates closely with the `R-CORD` and `vOLT` services, directly manipulating models (`RCORDSubscriber`, `ONUDevice`) in those services.

## Synchronizer Workflows

This synchronizer implements only event_steps and model_policies. It's job is to listen for events and execute a state machine associated with those events. Service Instances are created automatically when ONU events are received. As the state machine changes various states for authentication, etc., those changes will be propagated to the appropriate objects in the `R-CORD` and `vOLT` services.

The state machine is described below.

### Service Instances State Machine

| Topic                   | Event                            | Actions                                                   | ONU State    | Subscriber State     | Message                                                  |
|-------------------------|----------------------------------|-----------------------------------------------------------|--------------|----------------------|----------------------------------------------------------|
| `onu.events`            | `status: activated`              | Validate against whitelist (successful)                   | enabled      | awaiting-auth        | ONU has been validated                                   |
| `onu.events`            | `status: activated`              | Validate against whitelist (failed, missing)              | disabled     | awaiting-auth        | ONU not found in whitelist                               |
| `onu.events`            | `status: activated`              | Validate against whitelist (failed, location)             | disabled     | awaiting-auth        | ONU activated in wrong location                           |
| `onu.events`            | `status: disabled`               | Mark ONU as disabled and revoke subscriber authentication | disabled     | awaiting-auth        | ONU has been disabled, revoked subscriber authentication |
| `authentication.events` | `authenticationState: STARTED`   | Update subscriber status                                  | enabled      | awaiting-auth        | Authentication started                                   |
| `authentication.events` | `authenticationState: REQUESTED` | Update subscriber status                                  | enabled      | awaiting-auth        | Authentication requested                                 |
| `authentication.events` | `authenticationState: APPROVED`  | Update subscriber status                                  | enabled      | enabled              | Authentication succeded                                  |
| `authentication.events` | `authenticationState: DENIED`    | Update subscriber status                                  | enabled      | auth-failed          | Authentication denied                                    |
| `dhcp.events`           | --                               | Update subscriber ip and mac address                      | enabled      | enabled              | DHCP information added

### Model Policy: AttWorkflowDriverServiceInstancePolicy

This model policy is responsible for reacting to state changes that are caused by various event steps, implementing the state machine described above.

### Event Step: SubscriberAuthEventStep

Listens on `authentication.events` and updates the `authentication_state` fields of `AttWorkflowDriverServiceInstance`.

### Event Step: SubscriberDhcpEventStep

Listens on `dhcp.events` and updates the `dhcp_state`, `ip_address`, and `mac_address` fields of `AttWorkflowDriverServiceInstance`.

### Event Step: ONUEventStep

Listens on `onu.events` and updates the `onu_state` of `AttWorkflowDriverServiceInstance`. Also resets `authentication_state` when an ONU is disabled. Automatically creates `AttWorkflowDriverServiceInstance` as necessary.


## Events format

This events are generated by various applications running on top of ONOS and published on a Kafka bus.
Here is the structure of the events and their topics.

### onu.events

```json
{
  "timestamp": "2018-09-11T01:00:49.506Z",
  "status": "activated", // or disabled
  "serialNumber": "ALPHe3d1cfde", // ONU serial number
  "portNumber": "16", // uni port
  "deviceId": "of:000000000a5a0072" // OLT OpenFlow Id
}
```

### authentication.events

```json
{
  "timestamp": "2018-09-11T00:41:47.483Z",
  "deviceId": "of:000000000a5a0072", // OLT OpenFlow Id
  "portNumber": "16", // uni port
  "serialNumber": "ALPHe3d1cfde", // ONU serial number
  "authenticationState": "STARTED" // REQUESTED, APPROVED, DENIED
}
```

### dhcp.events

```json
{
  "deviceId" : "of:000000000a5a0072",
  "portNumber" : "16",
  "macAddress" : "90:e2:ba:82:fa:81",
  "ipAddress" : "10.11.1.1"
  "serialNumber": "ALPHe3d1cfde", // ONU serial number
}
```

