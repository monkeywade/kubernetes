#! /bin/bash

##################################################################################
# Filename   : detect_podport.sh
# Version    : 1.0.0
# Description: detect expose port for smoke test
# Author     : monkeywade
# History    : 2020-05-26 first create
##################################################################################


pod_list=`kubectl get po -l app |egrep "appserver|devcon|ddns|connector|sef|utility|ipc|smb|opdata" |awk '{print $1}'`
for pod in ${pod_list}
do
    echo $pod |awk -F "-" '{print $1}'
    kubectl exec $pod -- ss  -nplt |awk '{print $4"="$5"="$6}'
done
