#! /bin/bash

##################################################################################
# Filename   : create_yml.sh
# Version    : 1.3.0
# Description: create .yaml for appservice
# Author     : monkeywade
# History    : 2020-04-26 first create
#              2020-04-29 second modify (add configMap from change,txt)
#              2020-05-06 third modify (make a distinguish bewteen tomcat and jar)
#              2020-06-12 forth modify (download newest configuration from s3)
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

function shell_log(){

    if [[ ! -d ${log_dir} ]]; then
        mkdir -p ${log_dir}
    fi
    log_info=$*
    echo "${ctime} |DEBUG : ${log_info}" >> ${shell_log}

}

# start main function
# create yaml from images.list
function create_yaml(){

    if [[ -d ${tomcat_dir} ]]; then
        mv ${tomcat_dir} ${temp_dir}/app_tomcat_${ctime}
        mkdir -p ${tomcat_dir}
    else
        mkdir -p ${tomcat_dir}
    fi

    if [[ -d ${jar_dir} ]]; then
        mv ${jar_dir} ${temp_dir}/jar_dir_${ctime}
        mkdir -p ${jar_dir}
    else
        mkdir -p ${jar_dir}
    fi




    for module in `cat ${workdir}/version/images.list`
    do

        module_name_lowercase=$(echo ${module} |awk  -F "-" '{print $1"-"$2":"$3}'|tr '[A-Z]' '[a-z]')
        img_name=${registry}/mainland-${module_name_lowercase}
        shell_log "image name is ${img_name}"
        service_name=$(echo ${module} |awk  -F "-" '{print $2}')
        service_name_lowercase=${service_name,,}
        shell_log "service name is ${service_name}"
        shell_log "service name lowercase is ${service_name_lowercase}"

# notice the difference bewteen tomcat and jar
        if [[ ${tomcat_app} =~ ${service_name} ]];then
            file_name="${tomcat_dir}/mainland-cloud-$service_name.yaml"
            cp ${workdir}/demo/mainland-cloud-tomcat.demo ${file_name}
            shell_log "copy tomcat_app ${file_name} succeeded"
            sed -i "s#cloud-passthrough/tomcat#cloud-${service_name}/tomcat#g" ${file_name}

        else
            file_name="${jar_dir}/mainland-cloud-${service_name}.yaml"
            cp ${workdir}/demo/mainland-cloud-passthrough.demo ${file_name}
            shell_log "copy jar_app ${file_name} succeeded"
        fi

# replace module name
        sed -i "/^.*image:.*$/c \        image:\ ${img_name}" ${file_name}
        sed -i "s/mainland-cloud-passthrough/${service_name_lowercase}/g" ${file_name}
        sed -i "s#cloud-passthrough/cloud-passthrough-4.1.3#cloud-${service_name}/${module}#g" ${file_name}
        sed -i "s/passthrough.sys.properties/${service_name}.sys.properties/" ${file_name}
        sed -i "s/passthrough/${service_name_lowercase}/g" ${file_name}

        shell_log "create ${file_name} succeeded"

    done

}

# create configMap from ${workdir}/configMap
function create_configMap(){

    if [[ -d ${configMap_dir} ]]; then
        mv ${configMap_dir} ${temp_dir}/configMap_${ctime}
        mkdir -p ${configMap_dir}
    else
        mkdir -p ${configMap_dir}
    fi

    for module in `cat ${workdir}/version/images.list`
    do

        version_num=$(echo ${module} |awk  -F "-" '{print $3}')
        service_name=$(echo ${module} |awk  -F "-" '{print $2}')
        service_name_lowercase=${service_name,,}
        file_name_cm=${configMap_dir}/${service_name}.sys.properties
        aws s3 cp s3://${service_name}/config/${version_num}/sys.properties ${file_name_cm} >/dev/null 2>&1

        if [[ $? -eq 0 ]];then
            aws s3 cp s3://${service_name}/config/${version_num}/sys.properties.uat ${file_name_cm} >/dev/null 2>&1
            if [[ $? -eq 0 ]];then
                shell_log "download sys.properties.uat from s3://${service_name}/config/${version_num} to ${file_name_cm}"
            else
            shell_log "download sys.properties from s3://${service_name}/config/${version_num} to ${file_name_cm}"
            fi

# modify basicsvc configuration from sys.properties
#^^^^^

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
#            if [[ x${service_name} == xsms ]]; then
#                kubectl get cm smskey >>/dev/null
#                if [[ $? -eq 0 ]];then
#                    kubectl delete cm smskey
#                    kubectl create cm smskey --from-file=${workdir}/configMap/smskey.sys.properties
#                fi
#                shell_log "2 sms configMap created"
#            fi

        else
            shell_log "${service_name}-${version_num} configuration not found"
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
           create_yaml;
           create_configMap
           ;;
        yaml)
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
