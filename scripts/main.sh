#!/bin/bash

# Overview Plan
# Get Route
# Get Backend Services associated withthe Route
# Get Backend Pods assocaited with the Services
# Setup options



# This requires a minimum of Bash 4.x to complete
# exported
APPLICATION_NAME="route-debug-tool"

# local
namespace="$1"
route="$2"
# --

if [[ "${route}" == "" ]] || [["${namespace}" == ""]]; then
    echo "No OpenShift Route name was provided. Please provide a Route name and Namespace to continue."
    echo "${APPLICATION_NAME} <namespace> <name>"
    exit 1
elif [["${namespace}" == ""]]; then
    echo "No OpenShift Namespace name was provided. Please provide a Route name and Namespace to continue."
    echo "${APPLICATION_NAME} <namespace> <name>"
    exit 1
else
    echo "Using provided options:"
    echo "Route: ${route}"
    echo "Namespace: ${namespace}"
fi

# Confirm Route exists and there is only one
route_count=`oc get route -n $namespace $route -o name | wc -l`

if [[ $route_count -ne "1" ]]; then
  echo "Unable to locate the Route referenced. Please ensure the Route provided exists."
  exit 1
fi

# Get Backend Services associated with Route:
kind=`oc get route console -o jsonpath='{.spec.to.kind}'`
service_name=`oc get route console -o jsonpath='{.spec.to.name}'`
service_ip=`oc get service $service_name -o jsonpath='{.spec.clusterIP}'`

# Get ServiceSelector
selector=`oc get service $service_name -o json | jq -rc '.spec.selector | to_entries[] | [.key, .value] | join("=")' | tr '\n' ',' `
selector="${selector::-1}"

# Get Backend Pods associated with the Service
pods=(`oc get pods -n $namespace --selector=${selector} -o name | cut -d "/" -f 2`)




# 1) Collect a copy of the failing curl request. Run this from a local machine:
# ~~~
# URL=https://privacyportal.solutions.com.sa/
# curl -kvv $URL
# ~~~

# 2) Provide the output from the instructions in the link below. This will confirm the application is listening on the Pod ports correctly: 
#    https://access.redhat.com/solutions/6983011


# 3) Test access between the Routers and the OpenShift Pod. Please remember to replace the `<pod-name>` place holder with the current name of the `gateway` Pod:
# ~~~
# POD_NAME=<pod-name>
# PORT_NUMBER=8080

# POD_IP=`oc get pods $POD_NAME -o jsonpath='{.status.podIPs[0].ip}'`
# ROUTER_PODS=(`oc get pods -n openshift-ingress -l "ingresscontroller.operator.openshift.io/deployment-ingresscontroller=default" -o name`)
# for tmp in $ROUTER_PODS ; do 
#   ROUTER_POD=`echo $tmp | cut -d "/" -f 2`
#   echo "Performing tests from $ROUTER_POD to $POD_IP"

#   oc rsh -n openshift-ingress -c router "${ROUTER_POD}" curl -kvv "http://${POD_IP}:${PORT_NUMBER}"
#   oc rsh -n openshift-ingress -c router "${ROUTER_POD}" curl -kvv "https://${POD_IP}:${PORT_NUMBER}"
# done
# ~~~

# 4) Test access between the Routers and the OpenShift Service
# ~~~
# SERVICE_NAME=gateway
# PORT_NUMBER=8080

# SERVICE_IP=`oc get svc $SERVICE_NAME -o jsonpath='{.spec.clusterIP}'`
# ROUTER_PODS=(`oc get pods -n openshift-ingress -l "ingresscontroller.operator.openshift.io/deployment-ingresscontroller=default" -o name`)
# for tmp in $ROUTER_PODS ; do 

#   ROUTER_POD=`echo $tmp | cut -d "/" -f 2`
#   echo "Performing tests from $ROUTER_POD to $SERVICE_IP"

#   oc rsh -n openshift-ingress -c router "${ROUTER_POD}" curl -kvv "http://${SERVICE_IP}:${PORT_NUMBER}"
#   oc rsh -n openshift-ingress -c router "${ROUTER_POD}" curl -kvv "https://${SERVICE_IP}:${PORT_NUMBER}"
# done
# ~~~