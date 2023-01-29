#!/bin/bash

APP_NAME="route-tool"

echo "To use this script, source the script and run the available functions to configure your testing environment."
echo "The following functions are available:"
echo "- configure_console_route"

function console_route(){
  export "ROUTE_TOOL_ROUTE"="console"
  export "ROUTE_TOOL_NAMESPACE"="openshift-console"
}