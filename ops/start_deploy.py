#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
This script is to start a deployment with big_version

Usage: python3 start_deploy_develop.py <big_version> default | develop

Options:
    None

Version: 1.1.0

"""

import os
import shutil
import sys
import time
import re
import boto3
import logging

env = ""
s3_bucket_name = ""
workdir = ""
tomcat_service = [""]
basic_service_host = ""

def create_image_list():
    """
    download service.txt file from s3 using bigversion,
    service.txt includes all services and their newest versions,
    while image.list includes the services we need to deploy,
    compare this 2 files, we'll get services with their newest version which we need to deploy
    :param bigversion: big_version from pubSystem
    :return: None
    """
    s3 = boto3.resource("s3")
    s3.Bucket(s3_bucket_name).download_file(bigversion, service_file)
    # backup image.list to temp_image_file and mv it to image.old
    shutil.copy(image_file, temp_image_file)
    os.rename(image_file, image_old)

    dict_tmp = {}
    with open(service_file) as f1, open(image_old) as f2, open(image_file + ".bak", "w") as f3:
        for line in f1:  
            service_name = line.split("-")[0]  
            if service_name in ["MySQL", "Cassandra"]:
                update_basic_service(service_name, service_with_version=line)
            dict_tmp[service_name] = line.strip()
        for line in f2:  
            service_name = line.split("-")[1] 
            if service_name in dict_tmp:
                image_name = "cloud-" + dict_tmp[service_name] + "\n" 
                f3.write(image_name)
    # copy on write
    os.rename(image_file + ".bak", image_file)
    logging.info("create image.list successfully")

def update_basic_service(service_name, service_with_version):

    try:
        if namespace == "default":
            os.system('ssh %s "./update/update_basic_service.sh %s"'
                      % (basic_service_host, service_with_version))

        if namespace == "develop":
            if service_name == "MySQL":
                os.system('kubectl exec -n develop mysql-0 -- /tmp/update/update_basic_service.sh %s'
                          % (service_with_version))
            elif service_name == "Cassandra":
                os.system('kubectl exec -n develop cassandra-0 -- /tmp/update/update_basic_service.sh %s'
                          % (service_with_version))
    except Exception as e:
        raise Exception("basic service: %s update failed\n%s" % (service_with_version, e))

def create_configMap():
    """
    create configMap for update service, use shell script now
    :return:
    """
    if namespace == "default":
        os.system("./create.sh configmap")
    if namespace == "develop":
        os.system("./create_develop.sh configmap")
    logging.info("configMap create done")

def create_yaml():
    """
    create deployment yaml for update service
    :return:
    """
    deploy_dir = os.path.join(workdir, namespace, "deployment")
    time_tag = time.strftime('%Y%m%d-%H%M%S', time.localtime(time.time()))
    deploy_dir_bak = os.path.join(temp_file_dir, "deployment-%s" % time_tag)

    if os.path.exists(deploy_dir):
        shutil.copytree(deploy_dir, deploy_dir_bak)
        logging.info("backup deployment to %s" % (deploy_dir_bak))
    else:
        os.mkdir(deploy_dir)

    with open(image_file) as f1, open(image_old) as f2:
        image_old_content = f2.readlines()
        for line in f1:
            # find the difference between image.list and image.old
            if line in image_old_content:
                continue
            service_name = line.split("-")[1]  
            service_version = line.strip("\n").split("-")[2]  
            template_file_name = env + "-cloud-" + service_name + ".yaml"  

            if not check_version(service_version):
                return "service_version: %s is illegal" % (service_version)

            if service_name in tomcat_service:
                template_file_dir = os.path.join(workdir, namespace, "template_tomcat")
            else:
                template_file_dir = os.path.join(workdir, namespace, "template_jar")

            template_file = os.path.join(template_file_dir, template_file_name)
            deploy_file = os.path.join(deploy_dir, template_file_name)
            deploy_temp_file = os.path.join(deploy_dir, template_file_name + ".bak")

            with open(template_file, "r") as f1, open(deploy_temp_file, "w") as f2:
                for content in f1:
                    new_content = content.replace("VERSION_REPLACE", service_version)
                    f2.writelines(new_content)
            # copy on write
            os.rename(deploy_temp_file, deploy_file)
            logging.info("modify %s successfully" % (deploy_file))

            # apply deployment yaml
            logging.info("deploying %s " % (deploy_file))
            os.system("kubectl apply -f %s --record" % (deploy_file))
            time.sleep(1)

def check_version(service_version):
    """
    check service_version

    :param service_version: must be x.x.x
    """
    reg = '^\d+\.\d+\.\d+$'
    if re.search(reg, service_version):
        return True
    else:
        return False

def check_sysargv():
    """
    check system argument variables
    bigversion must start with "xxx", and namespace must be "default" or "develop"
    """
    try:
        if sys.argv[1] and sys.argv[2]:
            if sys.argv[1].startswith("xxx") and sys.argv[2] in ["default", "develop"]:
                return True
            else:
                return False
        else:
            return False
    except IndexError:
        return False

if __name__ == "__main__":
    if not check_sysargv():
        print(" Usage: %s <bigversion> default | develop" % (sys.argv[0]))
        sys.exit(0)
    bigversion = "big_version/" + sys.argv[1]
    namespace = sys.argv[2]
    service_file = os.path.join(workdir, namespace, "version", "service.txt")
    image_file = os.path.join(workdir, namespace, "version", "images.list")
    image_old = os.path.join(workdir, namespace, "version", "images.old")
    temp_file_dir = os.path.join(workdir, namespace, "temp")
    temp_image_file = os.path.join(temp_file_dir, "image.list_" +
                                   time.strftime("%Y%m%d-%H%M%S", time.localtime()))
    logging.basicConfig(filename=os.path.join(workdir, namespace, "log/deploy.log"),
                        level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')

    create_image_list()
    create_configMap()
    create_yaml()
