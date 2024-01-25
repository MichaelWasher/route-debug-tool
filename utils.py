""" This module is a general purpose place for reusable functions to perform tests in the Kuberenetes environment"""

import json
import logging
import time
from collections import defaultdict

import requests
from kubernetes import client, config
from kubernetes.client import *

config.load_kube_config()
v1 = client.CoreV1Api()


DEBUG_POD = None


def create_debug_pod(name="debug-pod", namespace="openshift-console", image="quay.io/mwasher/fedora", node_name=None):
    """

    Parameters
    ----------
    name
    namespace
    image
    node_name

    Returns
    -------
    V1Pod created
    """
    global DEBUG_POD
    if DEBUG_POD != None:
        return DEBUG_POD

    # TODO: Perform as a signleton
    metadata = V1ObjectMeta(
        generate_name=f"{name}-",
        namespace=namespace
    )
    container = V1Container(
        image=image,
        name="debug-container",
        command=["sleep", "inf"],
        security_context=V1SecurityContext(privileged=True, run_as_user=0, run_as_group=0),
        volume_mounts=[V1VolumeMount(mount_path="/host", name="host")]
    )
    pod_spec = V1PodSpec(
        containers=[container],
        node_name=node_name,
        volumes=[V1Volume(
            name="host",
            host_path=V1HostPathVolumeSource(path="/", type="Directory")
        )]
    )

    pod = client.V1Pod(
        metadata=metadata,
        spec=pod_spec
    )
    created_pod = client.CoreV1Api().create_namespaced_pod(namespace, body=pod)
    logging.info(f"Created Pod: {created_pod.metadata.name}")

    # Store Singleton
    DEBUG_POD = created_pod

    return created_pod


def create_debug_namespace(name):
    '''

    Parameters
    ----------
    name

    Returns
    -------
    namespace
    '''
    # TODO dynamically create the name of the namespace
    client.CoreV1Api().create_namespace(name=name)


def wait_for_ready(pod):
    while True:
        resp = v1.read_namespaced_pod(name=pod.metadata.name, namespace=pod.metadata.namespace)
        if resp.status.phase != 'Pending':
            break
        time.sleep(1)


def http_check_route(route):
    '''

    Parameters
    ----------
    route V1Route

    Returns
    -------

    '''
    # Check the Route with response code checks
    route_domain = route["spec"]["host"]
    logging.info(f"Performing check on {route_domain}")
    r = requests.get(url="https://" + route["spec"]["host"], verify=False)
    if 300 > r.status_code >= 200:
        logging.info(f"Route request succeeded with status code: {r.status_code}")
    else:
        logging.info(f"The Route request failed with status_code: {r.status_code}")


def remote_request_get(gatherer_pod, url, params=None, **kwargs):
    # RSH INTO THE POD
    # perform curl
    # Serialise the response and return
    #
    pass


def get_router_pods():
    """

    Returns
    -------

    """
    # TODO Get the router Pods that are used to host the route
    # .route.status.routerName
    # oc get pods -n openshift-ingress-operator
    #      --selector=ingresscontroller.operator.openshift.io/deployment-ingresscontroller=${router_name}

    # From there we can get perform RSH and assume that Curl and Python are present
    pass


def get_apiserver_serveraddress(api_client):
    """

    Parameters
    ----------
    api_client

    Returns
    -------

    """
    resp, status_code, headers = api_client.call_api('/api', 'GET', auth_settings=['BearerToken'], response_type='json',
                                                     _preload_content=False)
    api_resp = json.loads(resp.data.decode('utf-8'))
    api_ip_addresses = [address_tuple["serverAddress"] for address_tuple in api_resp["serverAddressByClientCIDRs"]]
    return api_ip_addresses


# get apiservers
def get_apiservers_ips():
    """‰

    Returns
    -------

    """
    # kgp -n openshift-kube-apiserver -l app=openshift-kube-apiserver
    ns = "openshift-kube-apiserver"
    label_selector = "app=openshift-kube-apiserver"

    pod_list = v1.list_namespaced_pod(namespace=ns, label_selector=label_selector)

    pod_ips = [pod.status.pod_ip for pod in pod_list.items]
    return pod_ips


def s(api_client, retries=30):
    """

    Parameters
    ----------
    api_client

    Returns
    -------

    """
    apiserver_ips = defaultdict(lambda: 0)

    expected_ips = get_apiservers_ips()
    num_of_apiservers = len(expected_ips)

    for i in range(retries):
        for ip in get_apiserver_serveraddress(api_client):
            apiserver_ips[ip] += 1

    if len(apiserver_ips.keys()) < num_of_apiservers:
        raise Exception("Not all expected APIServers were seen in the collections. This may indicate sticky sessions")

    ## If half of the expected requests didn't make it to the
    ## Assume there are sticky sessions.
    for k, v in num_of_apiservers:
        if v < ((retries / num_of_apiservers) * 0.5):
            raise Exception(
                f"APIServers is heavily uneven. Expected {retries / num_of_apiservers} , got {v}")

    return
