import argparse
import logging
from os import environ

# Disable warnings from unverified TLS server certificates
import urllib3

from pods import check_pod
from services import check_service
from utils import *

# Configure the logging  stack
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

APP_NAME = "route-debug-tool"
VERSION = "0.0.0"

# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config()
v1 = client.CoreV1Api()
api_client = v1.api_client


# Process args
def parse_args():
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{VERSION} - network configuration debugging tool for OpenShift",
        prog=APP_NAME)

    # TODO incorporate the CLI tool for Kubernetes parsing
    parser.add_argument("--namespace", "-n", help="The OpenShift Namespace to review",
                        default=environ.get(f"{APP_NAME.upper()}_NAMESPACE"))

    parser.add_argument("--route", "-r", help=f"The OpenShift Route to review.",
                        default=environ.get(f"{APP_NAME.upper()}_ROUTE"))

    parser.add_argument("--service", "-s", help=f"The OpenShift Service to review.",
                        default=environ.get(f"{APP_NAME.upper()}_SERVICE"))

    parser.add_argument("--pod", "-p", help=f"The OpenShift Service to review.",
                        default=environ.get(f"{APP_NAME.upper()}_POD"))

    parser.add_argument("--log-level",
                        help=f"Set log level of app. Available options are 'critical', 'error', 'info', 'debug'.",
                        default=environ.get(f"{APP_NAME.upper()}_LOG_LEVEL"))

    parser.add_argument("--version", action="store_true",
                        help="Get program version")

    args = parser.parse_args()

    # Set defaults if missing:
    if not args.namespace:
        args.namespace = "default"

    return args


def configure_logging(log_level):
    logging.basicConfig()
    log_level = log_level.toLower()

    match log_level:
        case "debug":
            logging.getLogger().setLevel(logging.DEBUG)
        case "info":
            logging.getLogger().setLevel(logging.INFO)
        case "error":
            logging.getLogger().setLevel(logging.ERROR)
        case "warning":
            logging.getLogger().setLevel(logging.WARNING)
        case _:
            logging.getLogger().setLevel(logging.INFO)


def display_version():
    """ Display the current version of the applications"""
    logging.info(description=f"{APP_NAME} v{VERSION} - network configuration debugging tool for OpenShift")


# def perform_check_route(namespace, route_name):
#     try:
#         route, status, headers = client.CustomObjectsApi().get_namespaced_custom_object_with_http_info(
#             group="route.openshift.io", version="v1", plural="routes", namespace=namespace, name=route_name)
#
#     except client.exceptions.ApiException as e:
#         print("Failed to get route definition. Please ensure the Route name provided and Namespace are correct.")
#         print(e)
#         exit(1)
#
#     # Get backend pods from the Route definition
#     service_selectors = []
#     pod_list = []
#     service_list = []
#
#     service_selectors.append(route["spec"]["to"])
#
#     alternateBackends = route["spec"].get("alternateBackends")
#     if alternateBackends != None:
#         service_selectors.extend()
#
#     # Iterate all services
#     for service_selector in service_selectors:
#
#         if service_selector["kind"] != "Service":
#             print(
#                 f"Unknown Route format. `.route.spec.to.kind` value of `{service_selector['kind']}` is unexpected. This should be of type Service")
#             exit(1)
#
#         # Find the Service
#         service_name = service_selector["name"]
#         service = v1.read_namespaced_service(name=service_name, namespace=namespace)
#         service_list.append(service)
#
#         # Find the associated Pods
#         pod_selector = service.spec.selector
#         pod_selector_str = ",".join([f"{k}={v}" for k, v in pod_selector.items()])
#         pdb.set_trace()
#         pod_list.extend(v1.list_namespaced_pod(namespace=namespace, label_selector=pod_selector_str).items)
#
#     # Create a Namespace for Tests
#     # debug_namespace = create_debug_namespace()
#
#     pdb.set_trace()
#     # Perform Checks
#     http_check_route(route)
#
#     # Get Route expected ports
#     route_target_port = route["spec"].get("port").get("targetPort")
#     if type(route_target_port) != int:
#         # lookup port -> svc.spec.ports[*].name == target_port
#         ports = list(filter(lambda port: port.name == route_target_port, service.spec.ports))
#         if len(ports) < 1:
#             raise f"Unable to locate targetPort in {service.metadata.name}."
#         route_target_port = ports[0]
#
#     for service in service_list:
#         check_service(service)
#
#     # for pod in pod_list:
#     #     check_pod(pod)


def perform_check_pod(name, namespace):
    pods = v1.list_namespaced_pod(namespace=namespace).items
    pod = list(filter(lambda x: x.metadata.name == name, pods))

    if len(pod) != 1:
        logging.info("There has been an issue with selecting the Pod.")

    pod = pod[0]
    check_pod(pod)

    # Get the Expected Ports from the Pod and confirm these match the netstat output


def perform_check_service(name: str, namespace: str) -> None:
    services = v1.list_namespaced_service(namespace=namespace).items
    service = list(filter(lambda x: x.metadata.name == name, services))

    # TODO Fix:
    pod_ports = ["8443"]

    if len(service) != 1:
        logging.info("There has been an issue with selecting the Service.")

    service = services[0]
    check_service(service, pod_ports)

    # Get the Expected Ports from the Pod and confirm these match the netstat output


def __main__():
    # Parse args
    args = parse_args()
    configure_logging()

    # Deal with Version and help
    if args.version:
        display_version()
        exit(0)

    logging.info(f"Using the Namespace {args.namespace}")

    if args.pod:
        logging.info(f"Performing checks against Pod {args.pod}")
        perform_check_pod(name=args.pod, namespace=args.namespace)

    if args.service:
        logging.info(f"Performing checks against Service {args.service}")
        perform_check_service(name=args.service, namespace=args.namespace)

    if args.route:
        logging.info(f"Performing checks against Route {args.route}")
        # perform_check_route(pod_name=args.route, namespace=args.namespace)


__main__()
