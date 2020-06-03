#! /bin/bash

##################################################################################
# Filename   : create_yml.sh
# Version    : 1.3.0
# Description: create .yaml for appservice
# Author     : monkeywade
# History    : 2020-04-26 first create
#              2020-04-29 second modify (add configMap from change,txt)
#              2020-05-06 third modify (make a distinguish bewteen tomcat and jar)
##################################################################################

#set -eux

#Shell env
workdir=""
tomcat_dir=""
jar_dir=""
configMap_dir=""

registry=""
tomcat_app=""

shell_log=""
ctime=$(date "+%Y-%m-%d-%H-%M")

function create_dirs(){

    if [[ -d ${tomcat_dir} ]]; then
        mv ${tomcat_dir} ${tomcat_dir}_${ctime}
        mkdir -p ${tomcat_dir}
    else
        mkdir -p ${tomcat_dir}
    fi

    if [[ -d ${jar_dir} ]]; then
        mv ${jar_dir} ${jar_dir}_${ctime}
        mkdir -p ${jar_dir}
    else
        mkdir -p ${jar_dir}
    fi

    if [[ ! -d ${workdir}/log ]]; then
        mkdir -p ${workdir}/log
        if [[ ! -f ${shell_log} ]]; then
            touch ${shell_log}
        fi
    fi

}

function shell_log(){

  log_info=$*
  echo "${ctime} |DEBUG : ${log_info}" >> ${shell_log}

}

# start main function
# create yaml from images.list
function create_yaml(){

    for module in `cat ${workdir}/version/images.list`
    do

        module_name_lowercase=$(echo ${module} |awk  -F "-" '{print $1"-"$2":"$3}'|tr '[A-Z]' '[a-z]')
        img_name=${registry}/mainland-${module_name_lowercase}
        shell_log "image name is ${img_name}"
        service_name=$(echo ${module} |awk  -F "-" '{print $2}')
        service_name_lowercase=$(echo ${service_name} |tr '[A-Z]' '[a-z]')
        shell_log "service name is ${service_name}"
        shell_log "service name lowercase is ${service_name_lowercase}"

# notice the difference bewteen tomcat and jar
        if [[ ${tomcat_app} =~ ${service_name} ]];then
            file_name="${workdir}/app_tomcat/mainland-cloud-$service_name.yaml"
            cp ${workdir}/demo/mainland-cloud-tomcat.demo ${file_name}
            shell_log "copy tomcat_app ${file_name} succeeded"
            sed -i "s#cloud-passthrough/tomcat#cloud-${service_name}/tomcat#g" ${file_name}

        else
            file_name="${workdir}/temp/mainland-cloud-${service_name}.yaml"
            cp ${workdir}/demo/mainland-cloud-passthrough.demo ${file_name}
            shell_log "copy jar_app ${file_name} succeeded"
        fi

# replace module name
        sed -i "/^.*image:.*$/c \        image:\ ${img_name}" ${file_name}
        sed -i "s/mainland-cloud-passthrough/${service_name_lowercase}/g" ${file_name}
        sed -i "s#cloud-passthrough/cloud-passthrough-4.1.3#cloud-${service_name}/${module}#g" ${file_name}
        sed -i "s/passthrough.sys.properties/${service_name}.sys.properties/" ${file_name}
        sed -i "s/passthrough/${service_name_lowercase}/g" ${file_name}

# deviceBasic and sms are special, they have 2 volumeMounts
        if [[ x${service_name} == xdeviceBasic ]]; then
            sed -i "/subPath:/a\        - name: ca\n          mountPath: \/root\/cloud\/cloud-ca" ${file_name}
            sed -i "/          name: devicebasic/a\      - name: ca\n        secret:\n          secretName: devicebasic" ${file_name}
            shell_log "modify ${file_name} succeeded"
        fi

        if [[ x${service_name} == xsms ]]; then
            sed -i "/subPath:/a\        - name: config-smskey\n          mountPath: \/home\/cloud\/cloud-${service_name}\/${module}\/conf\/key.json\n          subPath: smskey.sys.properties" ${file_name}
            sed -i "/          name: sms/a\      - name: config-smskey\n        configMap:\n          name: smskey" ${file_name}
            shell_log "modify ${file_name} succeeded"
        fi

            shell_log "create ${file_name} succeeded"
done

}

# create configMap from ${workdir}/configMap
function create_configMap(){

    for module in `cat ${workdir}/version/images.list`
    do

        service_name=$(echo ${module} |awk  -F "-" '{print $2}')
        service_name_lowercase=$(echo ${service_name} |tr '[A-Z]' '[a-z]')
        shell_log "create_configMap:service name is ${service_name}"
        shell_log "create_configMap:service name lowercase is ${service_name_lowercase}"
        file_name_cm=${configMap_dir}/${service_name}.sys.properties
        shell_log "configMap file name is ${file_name_cm}"

# delete configMap existed
        kubectl get cm ${service_name_lowercase} >>/dev/null
        if [[ $? -eq 0 ]];then
            kubectl delete cm ${service_name_lowercase}
            kubectl create cm ${service_name_lowercase} --from-file=${file_name_cm}

        else
            kubectl create cm ${service_name_lowercase} --from-file=${file_name_cm}
        fi
        shell_log "configMap ${service_name_lowercase} modified"

# sms is special, it has 2 configMap
        if [[ x${service_name} == xsms ]]; then
            kubectl get cm smskey >>/dev/null
            if [[ $? -eq 0 ]];then
                kubectl delete cm smskey
                kubectl create cm smskey --from-file=${workdir}/configMap/smskey.sys.properties
            fi
            shell_log "2 sms configMap created"
        fi
done

}


usage(){
  echo "Usage: $0 all | yaml | configmap"
}

main(){
    DEPLOY_TYPE=$1
    case $DEPLOY_TYPE in
        all)
           create_dirs
           create_yaml;
           create_configMap
           ;;
        yaml)
           create_dirs
           create_yaml;
           ;;
        configmap)
           create_configMap
           ;;
         *)
           usage;
    esac
}

main $1
