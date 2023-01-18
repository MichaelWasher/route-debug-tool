from kubernetes import client, config
import pdb
import requests
import time
from utils import *
# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config()

# Route Specifics
route_name = "console"
route_namespace = "openshift-console"

# Dependents variables
pod_namespace=route_namespace
service_namespace=route_namespace

v1 = client.CoreV1Api()

# Get the Route definition
# routes = client.CustomObjectsApi().list_cluster_custom_object(group="route.openshift.io", version="v1", plural="routes")["items"

try:
    route, status, headers = client.CustomObjectsApi().get_namespaced_custom_object_with_http_info(group="route.openshift.io", version="v1", plural="routes", namespace=route_namespace, name=route_name)
    
except client.exceptions.ApiException as e:
    print("Failed to get route definition. Please ensure the Route name provided and Namespace are correct.")
    print(e)
    exit(1)
    
# Get backend pods from the Route definition
# TODO: There can be multiple services defined here. Assuming there is only one defined
service_selector = route["spec"]["to"]
if service_selector["kind"] != "Service":
    print(f"Unknown Route format. `.route.spec.to.kind` value of `{service_selector['kind']}` is unexpected. This should be of type Service")
    exit(1)

# Find the Service
service_name = service_selector["name"]
service = v1.read_namespaced_service(name=service_name, namespace=service_namespace)
pdb.set_trace()

# Find the associated Pods
pod_selector = service.spec.selector
pod_selector_str = ",".join([f"{k}={v}" for k,v in pod_selector.items()])
pod_list = v1.list_namespaced_pod(namespace=service_namespace,label_selector=pod_selector_str)

# Perform Checks
# Check the Route with response code checks
route_domain = route["spec"]["host"]
print(f"Performing check on {route_domain}")
r = requests.get(url=route["spec"]["host"], verify=False)
if 300 > r.status_code >= 200:
    print(f"Route request succeeded with status code: {r.status_code}")
else:
    print(f"The Route request failed with status_code: {r.status_code}")

# Check the Service from inside the cluster:
service_ip = service.spec.clusterIP
# TODO: Check these ports against the Route ports defined
for port in service.spec.ports:
    r = requests.get(url=f"{service_ip}:{port}", verify=False)
    if 300 > r.status_code >= 200:
        print(f"Route request succeeded with status code: {r.status_code}")
    else:
        print(f"The Route request failed with status_code: {r.status_code}")

# Create a Namespace for Tests
debug_namespace = create_debug_namespace()

# Create a debug Pod with Alpine
debug_pod = create_debug_pod(namespace=debug_namespace.metadata.name)

# Wait for the pod to start
while True:
    resp = v1.read_namespaced_pod(name=debug_pod.metadata.name, namespace=debug_namespace.metadata.name)
    if resp.status.phase != 'Pending':
        break
    time.sleep(1)

# - Check if all Pods are listening on the correct Ports

#

# Check if all
# v1.get_namespaced
# for i in ret.items:
#     print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
# Test Cases
# route_name = "console"
# route_namespace = "openshift-console"
# route_name = "console4"
