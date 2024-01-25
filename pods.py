""" This module provides helper functions related specifically to the networking of Kubernetes Pods """

from http.client import HTTPConnection

from kubernetes.stream import portforward
from kubernetes.stream.ws_client import PortForward

from utils import *

CHECK_STATUS_CODES = False


class ForwardedKubernetesHTTPConnection(HTTPConnection):

    def __init__(self, forwarding: PortForward, port: int):
        super().__init__("127.0.0.1", port)
        self.sock = forwarding.socket(port)

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass


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
        logging.info("Response: " + resp)
        return resp.splitlines(keepends=False)
    except client.exceptions.ApiException as e:
        logging.info(e)
        return None


def get_container_ports(pod):
    """

    Parameters
    ----------
    pod PodV1

    Returns
    -------
    container_ports list[]int
    """
    # Get defined Ports
    container_ports = []
    for container in pod.spec.containers:
        container_ports.extend([str(port.container_port) for port in container.ports])

    return container_ports


def check_container_ports_with_listening(container_ports, listening_ports):
    """

    Parameters
    ----------
    pod PodV1

    Returns
    -------
    complement_ports list[]int (ports which are defined in the Pod but not listening)
    """
    complement_ports = list(set(container_ports) - set(listening_ports))
    return complement_ports


def port_forward_check(pod, remote_port):
    """

    Parameters
    ----------
    pod PodV1
    remote_port int

    Returns
    -------
    response
    """
    # Testing Port Forwarding in Kuberentes
    pf = portforward(
        v1.connect_get_namespaced_pod_portforward,
        pod.metadata.name,
        pod.metadata.namespace,
        ports=remote_port
    )

    conn = ForwardedKubernetesHTTPConnection(pf, int(remote_port))
    conn.request("GET", "/my/url")  # will fail for other methods
    resp = conn.getresponse()
    return resp


def check_pod(pod):
    """

    Parameters
    ----------
    pod

    Returns
    -------

    """
    # Check the Ports are defined and listened
    container_ports = get_container_ports(pod)
    pod_name = pod.metadata.name
    logging.info(f"Pod '{pod_name}' is configured with ports: {', '.join(container_ports)}")

    listening_ports = get_listening_ports(pod)
    logging.info(f"Pod '{pod_name}' is listening to ports: {', '.join(listening_ports)}")

    complement_ports = check_container_ports_with_listening(container_ports, listening_ports)
    if len(complement_ports) > 0:
        logging.info(f"The following ports are defined but there is not application listening: {', '.join(complement_ports)}")

    # Check the ports (assuming TCP) are responding to HTTP responses. Ignoring UDP and HTTPS (TODO filter)
    for remote_port in container_ports:
        resp = port_forward_check(pod, remote_port)
        if CHECK_STATUS_CODES and (resp.status < 200 or resp.status > 300):
            logging.info(
                f"Error with port {remote_port} for pod {pod.metadata.name}. Expected 2XX status code but received {str(resp.status)}")

    return
