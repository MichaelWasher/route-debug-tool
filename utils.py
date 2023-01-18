""" This module is a general purpose place for reusable functions to perform tests in the Kuberenetes environment"""
import pdb

from kubernetes import client, config
from kubernetes.client import *
import time
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException

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
    created_pod= client.CoreV1Api().create_namespaced_pod(namespace, body=pod)
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
    client.CoreV1Api().create_namespace(name= name)

def wait_for_ready(pod):
    while True:
        resp = v1.read_namespaced_pod(name=pod.metadata.name, namespace=pod.metadata.namespace)
        if resp.status.phase != 'Pending':
            break
        time.sleep(1)
def get_listening_ports(target_pod):

    sniffer_pod = create_debug_pod(node_name=target_pod.spec.node_name)
    # Wait for Pod to be running
    wait_for_ready(sniffer_pod)

    # Run the script to exec netstat
    script = f"""
        function get_listening_ports () {{
            NS=$1
            POD=$2
        
            POD_ID=$( crictl pods --namespace=$NS --name=$POD -o json |  jq -r '.items[].id' )
            NS_PATH=$( crictl inspectp $POD_ID | jq -r '.info.runtimeSpec.linux.namespaces[] | select( .type=="network" ) | .path' )
            nsenter --net=$NS_PATH ss -lptun
        }}
        get_listening_ports_str=$(declare -f get_listening_ports)
        chroot /host /bin/sh -c "${{get_listening_ports_str}} ; get_listening_ports {target_pod.metadata.namespace} {target_pod.metadata.name}"
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
        pdb.set_trace()
    except client.exceptions.ApiException as e:
        print(e)
