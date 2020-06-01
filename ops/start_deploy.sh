#! /bin/bash

##################################################################################
# Filename   : start_deploy.sh
# Version    : 1.0.0
# Description: start deployment of all appservice
# Author     : monkeywade
# History    : 2020-04-28 first create
##################################################################################



workdir=
tomcat_app=
count=0
# start app from images.list in order
for module in `cat ${workdir}/images.list`
do
    service_name=$(echo ${module} |awk  -F "-" '{print $2}')
#  service_name_lowercase=$(echo ${service_name} |tr '[A-Z]' '[a-z]')
    if [[ ${tomcat_app} =~ ${service_name} ]];then
        file_name="${workdir}/app_tomcat/mainland-cloud-$service_name.yaml"
    else
        file_name="${workdir}/temp/mainland-cloud-${service_name}.yaml"
    fi
    ((count++))
    echo "-------${count}.starting $service_name from ${file_name##*-}-------"
    kubectl apply -f ${file_name}
    sleep 10
done
