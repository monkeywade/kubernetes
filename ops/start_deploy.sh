#! /bin/bash

##################################################################################
# Filename   : start_deploy.sh
# Version    : 1.1.0
# Description: start deployment of all appservice
# Author     : monkeywade
# History    : 2020-04-28 first create
#              2020-06-03 second modify add update judgement
##################################################################################


workdir=""
tomcat_app=""
appbasic=""
count=0

# start app from images.list in order
function deploy(){

    for module in `cat ${workdir}/version/images.list`
    do
        service_name=$(echo ${module} |awk  -F "-" '{print $2}')

        if [[ ${tomcat_app} =~ ${service_name} ]];then
            file_name="${workdir}/app_tomcat/mainland-cloud-$service_name.yaml"
        else
            file_name="${workdir}/app_jar/mainland-cloud-${service_name}.yaml"
        fi

        cmd=$(kubectl apply -f ${file_name} --record)
        
        if [[ ${cmd} =~ unchanged ]];then
            sleep 1
        else
            ((count++))
            echo "-------${count}.updating $service_name from ${file_name##*-}-------"
            if [[ ${appbasic} =~ ${service_name} ]];then
                sleep 30
            else
                sleep 10
            fi
        fi
    done
}

main(){
        deploy
}

main
