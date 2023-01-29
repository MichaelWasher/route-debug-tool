""" This module is a general purpose place for reusable functions to perform tests in the Kuberenetes environment"""
import pdb

from kubernetes import client, config
from kubernetes.client import *
import time
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException
import requests
import json
import pdb
from collections import defaultdict


config.load_kube_config()
v1 = client.CoreV1Api()


# TODO: Add additional logging and fix logging to use a log library


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
    print(f"Created Pod: {created_pod.metadata.name}")
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


def get_listening_ports(target_pod):
    """

    Parameters
    ----------
    target_pod PodV1

    Returns
    -------
    List of Port numbers that are actively listening. If there is an issue, None is returned
    """
    sniffer_pod = create_debug_pod(node_name=target_pod.spec.node_name)
    # Wait for Pod to be running
    wait_for_ready(sniffer_pod)

    # Run the script to output the listening ports (one per line)
    script = f"""
        function get_listening_ports () {{
            NS=$1
            POD=$2
        
            POD_ID=$( crictl pods --namespace=$NS --name=$POD -o json |  jq -r '.items[].id' )
            NS_PATH=$( crictl inspectp $POD_ID | jq -r '.info.runtimeSpec.linux.namespaces[] | select( .type=="network" ) | .path' )
            nsenter --net=$NS_PATH ss -H -lptn
        }}
        get_listening_ports_str=$(declare -f get_listening_ports)
        func_output=$(chroot /host /bin/sh -c "${{get_listening_ports_str}} ; get_listening_ports {target_pod.metadata.namespace} {target_pod.metadata.name}")
        # Filter output
        echo $func_output | cut -d ":" -f 2 | cut -d " " -f 1 | sort -u
    """

    # Calling exec and waiting for response
    exec_command = [
        '/bin/sh',
        '-c', f"{script}"
    ]
    try:
        resp = stream(client.api.CoreV1Api().connect_get_namespaced_pod_exec,
                      sniffer_pod.metadata.name,
                      sniffer_pod.metadata.namespace,
                      command=exec_command,
                      stderr=True, stdin=False,
                      stdout=True, tty=False)
        print("Response: " + resp)
        return resp.splitlines(keepends=False)
    except client.exceptions.ApiException as e:
        print(e)
        return None


def check_route(route):
    '''

    Parameters
    ----------
    route V1Route

    Returns
    -------

    '''
    # Check the Route with response code checks
    route_domain = route["spec"]["host"]
    print(f"Performing check on {route_domain}")
    r = requests.get(url="https://" + route["spec"]["host"], verify=False)
    if 300 > r.status_code >= 200:
        print(f"Route request succeeded with status code: {r.status_code}")
    else:
        print(f"The Route request failed with status_code: {r.status_code}")


def check_service(service):
    """

    Parameters
    ----------
    service

    Returns
    -------

    """
    # Check the Service from inside the cluster:
    # TODO: Confirm the port is the same as the route destination
    service_ip = service.spec.cluster_ip
    # TODO: Check these ports against the Route ports defined
    for port in service.spec.ports:
        port_number = port.port
        pdb.set_trace()
        # TODO check this against HTTPS ports
        r = requests.get(url=f"https://{service_ip}:{port_number}", verify=False)
        if 300 > r.status_code >= 200:
            print(f"Service {service.metadata.name} request succeeded with status code: {r.status_code}")
        else:
            print(f"Service {service.metadata.name} request failed with status_code: {r.status_code}")


def check_pods(pod_list):
    """

    Parameters
    ----------
    pod_list

    Returns
    -------

    """
    # TOOD: Should really take in a pod_name as the gatherer pod
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
    """

    Returns
    -------

    """
    # kgp -n openshift-kube-apiserver -l app=openshift-kube-apiserver
    ns = "openshift-kube-apiserver"
    label_selector = "app=openshift-kube-apiserver"

    pod_list = v1.list_namespaced_pod(namespace=ns, label_selector=label_selector)

    pod_ips = [pod.status.pod_ip for pod in pod_list.items]
    return pod_ips

def check_apiserver_loadbalancer(api_client, retries = 30):
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
