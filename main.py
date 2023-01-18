from kubernetes import client, config
import pdb
import requests
import time
from utils import *

# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config()
v1 = client.CoreV1Api()

# Route Specifics
route_name = "console"
route_namespace = "openshift-console"

# Dependents variables
pod_namespace = route_namespace
service_namespace = route_namespace

# Get the Route definition
# routes = client.CustomObjectsApi().list_cluster_custom_object(group="route.openshift.io", version="v1", plural="routes")["items"

try:
    route, status, headers = client.CustomObjectsApi().get_namespaced_custom_object_with_http_info(
        group="route.openshift.io", version="v1", plural="routes", namespace=route_namespace, name=route_name)

except client.exceptions.ApiException as e:
    print("Failed to get route definition. Please ensure the Route name provided and Namespace are correct.")
    print(e)
    exit(1)

# Get backend pods from the Route definition
# TODO: There can be multiple services defined here. Assuming there is only one defined
service_selector = route["spec"]["to"]
if service_selector["kind"] != "Service":
    print(
        f"Unknown Route format. `.route.spec.to.kind` value of `{service_selector['kind']}` is unexpected. This should be of type Service")
    exit(1)

# Find the Service
service_name = service_selector["name"]
service = v1.read_namespaced_service(name=service_name, namespace=service_namespace)

# Find the associated Pods
pod_selector = service.spec.selector
pod_selector_str = ",".join([f"{k}={v}" for k, v in pod_selector.items()])
pod_list = v1.list_namespaced_pod(namespace=service_namespace, label_selector=pod_selector_str)



# Create a Namespace for Tests
debug_namespace = create_debug_namespace()

# Perform Checks
check_route(route)
check_service(service)
check_pods(pod_list)

# - Check if all Pods are listening on the correct Ports
for pod in pod_list:
    listening_ports = get_listening_ports(pod)
    print(f"Pod '{pod}' is listening to {', '.join(listening_ports)}")

#
