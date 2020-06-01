#! /bin/bash

##################################################################################
# Filename   : create_yml.sh
# Version    : 1.1.0
# Description: create .yaml for appservice
# Author     : monkeywade
# History    : 2020-04-26 first create
#              2020-04-29 second modify (add configMap from change,txt)
#              2020-05-06 third modify (make a distinguish bewteen tomcat and jar)
##################################################################################

#set -eux
#for cm in `kubectl get cm |grep -v NAME |grep -v redis |awk '{print $1}'`;do kubectl delete cm $cm;done

workdir=
registry=
tomcat_app="appserver......."

for module in `cat ${workdir}/images.list`
do
    module_name_lowercase=$(echo ${module} |awk  -F "-" '{print $1"-"$2":"$3}'|tr '[A-Z]' '[a-z]')
    img_name=${registry}/mainland-${module_name_lowercase}
#    echo "image name is ${img_name}"
    service_name=$(echo ${module} |awk  -F "-" '{print $2}')
    service_name_lowercase=$(echo ${service_name} |tr '[A-Z]' '[a-z]')
#    echo "service name is ${service_name}"

# create yaml from images.list
# notice the difference bewteen tomcat and jar
    if [[ ${tomcat_app} =~ ${service_name} ]];then
        file_name="${workdir}/app_tomcat/mainland-cloud-$service_name.yaml"
        echo "file name is ${file_name}"
        cp ${workdir}/app_tomcat/mainland-cloud-passthrough.demo ${file_name}
        sed -i "s#cloud-passthrough/tomcat#cloud-${service_name}/tomcat#g" ${file_name}
    else
        file_name="${workdir}/temp/mainland-cloud-${service_name}.yaml"
        echo "file name is ${file_name}"
        cp ${workdir}/mainland-cloud-passthrough.demo ${file_name}
    fi
# replace module name
        sed -i "/^.*image:.*$/c \        image:\ ${img_name}" ${file_name}
        sed -i "s/mainland-cloud-passthrough/${service_name_lowercase}/g" ${file_name}
        sed -i "s#cloud-passthrough/cloud-passthrough-4.1.3#cloud-${service_name}/${module}#g" ${file_name}
        sed -i "s/passthrough.sys.properties/${service_name}.sys.properties/" ${file_name}
        sed -i "s/passthrough/${service_name_lowercase}/g" ${file_name}

# create configMap from ${workdir}/configMap
    file_name_cm=${workdir}/configMap/${service_name}.sys.properties
#    echo "configMap file name is ${file_name_cm}"
    kubectl create cm ${service_name_lowercase} --from-file=${file_name_cm}
# sms is special, it has 2 configMap
    if [ x${service_name} == xsms ]; then
        kubectl create cm smskey --from-file=${workdir}/configMap/smskey.sys.properties
        sed -i "a#subPath:#\        - name: config-smskey\n          mountPath: /home/cloud/cloud-${service_name}/${module}/conf/key.json\n          subPath: smskey.sys.properties" ${file_name}
        sed -i "a#          name: sms#\      - name: config-smskey\n        configMap:\n          name: smskey" ${file_name}
    fi
done
