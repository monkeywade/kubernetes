#! /bin/bash

##################################################################################
# Filename   : stop_deploy.sh
# Version    : 1.0.0
# Description: stop deployment of all appservice
# Author     : monkeywade
# History    : 2020-04-28 first create
##################################################################################

while getopts ":au" opt;
do
    case ${opt} in
        a)
# stop all deployments
            dp_list=`cat /home/ubuntu/cloud/images.list |awk -F "-" '{print $2}'`
            ;;
        u)
# stop unhealthy deployments
            dp_list=`kubectl get po -l app|grep -v NAME|grep -v Running|awk -F "-" '{print $1}'`
            ;;
        \?)
            echo "unknown argument, -a|-u is required"
            exit 1
            ;;
    esac
done


for service in ${dp_list[*]}
do
    service_name_lowercase=${service,,}
    echo "----stopping ${service_name_lowercase}----"
    kubectl delete deployments.apps ${service_name_lowercase}
done
