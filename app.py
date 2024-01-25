import argparse
from os import environ

# Disable warnings from unverified TLS server certificates
import urllib3

from pods import check_pod
from services import check_service
from utils import *

# NOTE: Ignore TLS verify warnings as it's commonplace to have self-signed certificates with OpenShift
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# App Configuration
APP_NAME = "route-debug-tool"
VERSION = "0.0.0"

# Setup Kubernetes Library
config.load_kube_config()
v1 = client.CoreV1Api()
api_client = v1.api_client


# Process args
def parse_args():
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{VERSION} - network configuration debugging tool for OpenShift",
        prog=APP_NAME)

    # TODO incorporate the CLI tool for Kubernetes value parsing
    parser.add_argument("--namespace", "-n", help="The OpenShift Namespace",
                        default=environ.get(f"{APP_NAME.upper()}_NAMESPACE"))

    parser.add_argument("--route", "-r", help=f"The OpenShift Route to inspect",
                        default=environ.get(f"{APP_NAME.upper()}_ROUTE"))

    parser.add_argument("--service", "-s", help=f"The OpenShift Service to inspect",
                        default=environ.get(f"{APP_NAME.upper()}_SERVICE"))

    parser.add_argument("--pod", "-p", help=f"The OpenShift Pod to inspect",
                        default=environ.get(f"{APP_NAME.upper()}_POD"))

    parser.add_argument("--log-level",
                        help=f"Set log level of app. Available options are 'critical', 'error', 'info', 'debug'",
                        default=environ.get(f"{APP_NAME.upper()}_LOG_LEVEL"))

    parser.add_argument("--version", action="store_true",
                        help="Get program version")

    args = parser.parse_args()

    # Set defaults if missing:
    if not args.namespace:
        args.namespace = "default"

    if not args.log_level:
        args.log_level = "info"

    return parser, args


def configure_logging(log_level):
    logging.basicConfig()
    log_level = log_level.lower()

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
    print(f"{APP_NAME} v{VERSION} - network configuration debugging tool for OpenShift")


def perform_check_pod(name: str, namespace: str) -> None:
    pods = v1.list_namespaced_pod(namespace=namespace).items
    pod = list(filter(lambda x: x.metadata.name == name, pods))

    if len(pod) == 0:
        logging.fatal(f"Failed to locate Pod. Pod {name} does not exist in Namespace {namespace}")
        exit(1)

    if len(pod) > 1:
        logging.fatal(f"Too many Pods found named {name}. Pods MUST have unique names.")
        logging.fatal(f"Failed for Pod {name} in Namespace {namespace}")
        exit(1)

    pod = pod[0]
    check_pod(pod)


def perform_check_service(name: str, namespace: str) -> None:
    services = v1.list_namespaced_service(namespace=namespace).items
    services = list(filter(lambda x: x.metadata.name == name, services))

    if len(services) == 0:
        logging.fatal(f"Failed to locate Service. Service {name} does not exist in Namespace {namespace}")
        exit(1)

    if len(services) > 1:
        logging.fatal(f"Too many Services found named {name}. Services MUST have unique names.")
        logging.fatal(f"Failed for Service {name} in Namespace {namespace}")
        exit(1)

    service = services[0]

    label_selector = ",".join([f"{k}={v}" for k, v in service.spec.selector.items()])
    pod_list = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

    if len(pod_list.items) < 1:
        logging.fatal(f"No Pods found backing Service {name}")
        logging.fatal(f"Ensure Pods match the Service labelselector and EndPoint objects exist")
        logging.fatal(f"oc get -n {namespace} endpoints && oc get pods -n {namespace} --selector={label_selector}")
        exit(1)

    pod_ports = set()
    for pod in pod_list.items:
        pod_ports.update(check_pod(pod))

    check_service(service, list(pod_ports))


def __main__():
    # Parse args
    parser, args = parse_args()
    configure_logging(args.log_level)

    # Deal with Version and help
    if args.version:
        display_version()
        exit(0)

    logging.debug(f"Using Namespace {args.namespace}")

    if args.pod:
        logging.debug(f"Performing checks against Pod {args.pod}")
        perform_check_pod(name=args.pod, namespace=args.namespace)

    elif args.service:
        logging.debug(f"Performing checks against Service {args.service}")
        perform_check_service(name=args.service, namespace=args.namespace)

    elif args.route:
        logging.info("ERROR: This function has not been implemented yet.")

    else:
        print("No object was provided to inspect.")
        parser.print_help()


__main__()
