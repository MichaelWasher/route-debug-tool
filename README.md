# Route Debug Tool
A tool to check the current network configuration of OpenShift Routes, Services and Pods.

This tool inspects the Pod definitions of an application and ensures the application is listening on the expected ports.

After checking the Pods, Service objects are compared with their associated Pods.

TODO: After checking the Services, Route objects are compared with their associated Service -> Pods.

NOTE: This currently assumes the application is used TCP ports with HTTP endpoints.


``` bash
usage: route-debug-tool [-h] [--namespace NAMESPACE] [--route ROUTE] [--service SERVICE] [--pod POD] [--log-level LOG_LEVEL] [--version]

route-debug-tool v0.0.0 - network configuration debugging tool for OpenShift

options:
  -h, --help            show this help message and exit
  --namespace NAMESPACE, -n NAMESPACE
                        The OpenShift Namespace
  --route ROUTE, -r ROUTE
                        The OpenShift Route to inspect
  --service SERVICE, -s SERVICE
                        The OpenShift Service to inspect
  --pod POD, -p POD     The OpenShift Pod to inspect
  --log-level LOG_LEVEL
                        Set log level of app. Available options are 'critical', 'error', 'info', 'debug'
  --version             Get program version
```