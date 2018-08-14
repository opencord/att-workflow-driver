# AT&T Workflow Driver 

This service is intended to be an example implementation of a service that integrates XOS with an external OSS system.
As the name suggests this service will be very welcoming and validate any ONU that is connected to the system.

Peace and Love

> NOTE: This service depends on RCORDSubscriber and ONUDevice so make sure that the `rcord-synchronizer` and `volt-synchronzier` are running

## How to install this service

Make sure you have `xos-core`, `rcord-lite` and `kafka` running.

To install from master:

```bash
helm install -n att-workflow xos-services/att-workflow-driver/
```

To install from the local `docker` daemon in minikube:

```bash
helm install -n att-workflow xos-services/att-workflow-driver/ -f examples/image-tag-candidate.yaml -f examples/imagePullPolicy-IfNotPresent.yaml
```

## Configure this service

You can use this TOSCA to add entries to the ONU whitelist:

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
        olt_logical_device_id: of:000000000a5a0072
      requirements:
        - owner:
            node: service#att
            relationship: tosca.relationships.BelongsToOne
```
