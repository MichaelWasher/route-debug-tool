FROM docker.io/alpine:latest

# Requires tools include netstat, Curl, kubectl and oc
RUN apk add net-tools curl bash
COPY ./scripts /scripts

ENTRYPOINT ["sleep", "inf"]