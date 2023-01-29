import json

from kubernetes import client, config
import pdb
import requests
import time
from utils import *
import argparse
from os import environ

APP_NAME="route-debug-tool"
VERSION="0.0.0"

# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config()
v1 = client.CoreV1Api()
api_client = v1.api_client

# Process args

# Route Specifics
route_name = "console"
route_namespace = "openshift-console"

# Dependents variables
pod_namespace = route_namespace
service_namespace = route_namespace

def parse_args():
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{VERSION} - network configuration debugging tool for OpenShift",
        prog=APP_NAME)

    # TODO incorporate the CLI tool for Kubernetes parsing
    parser.add_argument("--namespace", "-n", help="The OpenShift Namespace to review", default=environ.get(f"{APP_NAME.upper()}_NAMESPACE"))

    parser.add_argument("--route", "-r", help=f"The OpenShift Route to review.",
                        default=environ.get(f"{APP_NAME.upper()}_ROUTE"))

    parser.add_argument("--service", "-s", help=f"The OpenShift Service to review.",
                        default=environ.get(f"{APP_NAME.upper()}_ROUTE"))

    parser.add_argument("--version", action="store_true",
                        help="Get program version")

    return parser.parse_args()

def display_version():
    """ Display the current version of the applications"""
    print(description=f"{APP_NAME} v{VERSION} - network configuration debugging tool for OpenShift")


def perform_check_route(namespace, route_name):
    try:
        route, status, headers = client.CustomObjectsApi().get_namespaced_custom_object_with_http_info(
            group="route.openshift.io", version="v1", plural="routes", namespace=namespace, name=route_name)

    except client.exceptions.ApiException as e:
        print("Failed to get route definition. Please ensure the Route name provided and Namespace are correct.")
        print(e)
        exit(1)

    # Get backend pods from the Route definition
    # TODO: There can be multiple services defined here. Assuming there is only one defined `route.spec.alternateBackends`
    service_selector = route["spec"]["to"]
    if service_selector["kind"] != "Service":
        print(
            f"Unknown Route format. `.route.spec.to.kind` value of `{service_selector['kind']}` is unexpected. This should be of type Service")
        exit(1)

    # Find the Service
    service_name = service_selector["name"]
    service = v1.read_namespaced_service(name=service_name, namespace=namespace)

    # Find the associated Pods
    pod_selector = service.spec.selector
    pod_selector_str = ",".join([f"{k}={v}" for k, v in pod_selector.items()])
    pod_list = v1.list_namespaced_pod(namespace=namespace, label_selector=pod_selector_str)



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



def __main__():
    # Parse args
    args = parse_args()

    # Deal with Version and help
    if args.version:
        display_version()
        exit(0)

    # If route, check route, if service check service...>
    perform_check_route(route_name=args.route, namespace=args.namespace)

__main__()
