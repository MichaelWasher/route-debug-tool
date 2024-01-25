from collections import namedtuple

from kubernetes.stream import stream

from utils import *

PortMapping = namedtuple('PortMapping', ['service_port', 'target_port'])
CHECK_STATUS_CODE = False
service_name = "console"
service_namespace = "openshift-console"


def get_service_port_mapping(service):
    """

    Parameters
    ----------
    service V1Service

    Returns
    -------
    port_mapping list[]PortMapping
    """
    port_mapping = []
    for port_def in service.spec.ports:
        port_mapping.append(PortMapping(service_port=str(port_def.port), target_port=str(port_def.target_port)))

    return port_mapping


def curl_inside_cluster(debug_pod, service_ip, service_port):
    """

    Parameters
    ----------
    target_pod PodV1

    Returns
    -------
    List of Port numbers that are actively listening. If there is an issue, None is returned
    """
    # Run the script to output the listening ports (one per line)
    script = 'curl -s -o /dev/null -w "%{http_code}" ' + service_ip + ":" + service_port

    # Calling exec and waiting for response
    exec_command = [
        '/bin/sh',
        '-c', f"{script}"
    ]

    try:
        resp = stream(client.api.CoreV1Api().connect_get_namespaced_pod_exec,
                      debug_pod.metadata.name,
                      debug_pod.metadata.namespace,
                      command=exec_command,
                      stderr=True, stdin=False,
                      stdout=True, tty=False)
        logging.info("Response: " + resp)
        # Check if the `curl` request failed to get a layer7 response
        if resp == "000":
            return None
        else:
            return resp
    except client.exceptions.ApiException as e:
        logging.info(e)
        return None


def check_service(service, pod_ports):
    """

    Parameters
    ----------
    service V1Service
    pod_ports list[]int
    Returns
    -------

    """
    # Find all Pods and check the Pods


    # Find the complement of service ports and the expected container ports
    port_mapping_list = get_service_port_mapping(service)
    target_ports = [pm.target_port for pm in port_mapping_list]
    complement_ports = list(set(target_ports) - set(pod_ports))

    if len(complement_ports) > 0:
        logging.info(f"The following ports are defined in the Service but no Pod is listening: {', '.join(complement_ports)}")

    # Check the Service from inside the cluster:
    service_ip = service.spec.cluster_ip

    for port_mapping in port_mapping_list:
        service_port = port_mapping.service_port

        debug_pod = create_debug_pod()
        wait_for_ready(debug_pod)

        status_code = curl_inside_cluster(debug_pod, service_ip, service_port)

        if status_code is None:
            logging.info(f"Failed to check Service {service_name} on {service_ip}:{service_port}")

        if CHECK_STATUS_CODE:
            if 300 > status_code >= 200:
                logging.info(f"Service {service.metadata.name} request succeeded with status code: {status_code}")
            else:
                logging.info(f"Service {service.metadata.name} request failed with status_code: {status_code}")
