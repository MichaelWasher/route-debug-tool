#!/bin/bash

function get_listening_ports_n () {
    NS=$1
    POD=$2

    POD_ID=$( crictl pods --namespace=$NS --name=$POD -o json |  jq -r '.items[].id' )
    NS_PATH=$( crictl inspectp $POD_ID | jq -r '.info.runtimeSpec.linux.namespaces[] | select( .type=="network" ) | .path' )
    nsenter --net=$NS_PATH ss -lptun
}

function get_listening_ports() {
  NS=$1
  POD=$2

  NODE=$( oc get pod $POD -n $NS -o jsonpath='{.spec.nodeName}' )
  oc debug node/$NODE -- chroot /host sh -c "$(declare -f get_listening_ports_n); get_listening_ports_n $NS $POD"
}