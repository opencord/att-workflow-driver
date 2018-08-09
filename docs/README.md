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
