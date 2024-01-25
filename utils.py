""" This module is a general purpose place for reusable functions to perform tests in the Kuberenetes environment"""

import json
import logging
import time
from collections import defaultdict
from http.client import HTTPConnection

import requests
from kubernetes import client, config
from kubernetes.client import *
from kubernetes.stream.ws_client import PortForward

config.load_kube_config()
v1 = client.CoreV1Api()

debug_pods = {}


class ForwardedKubernetesHTTPConnection(HTTPConnection):

    def __init__(self, forwarding: PortForward, port: int):
        super().__init__("127.0.0.1", port)
        self.sock = forwarding.socket(port)

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass


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
    global debug_pods

    if len(debug_pods) > 0 and node_name is None:
        return list(debug_pods.values())[0]

    if debug_pods.get(node_name):
        return debug_pods.get(node_name)

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
    logging.debug(f"Created Pod: {created_pod.metadata.name}")

    # Store Singleton per node
    debug_pods[node_name] = created_pod

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