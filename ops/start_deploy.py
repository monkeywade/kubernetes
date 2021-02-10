#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
This script is to start a deployment with big_version

Usage: python3 start_deploy.py <big_version> default | develop

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


class Deployment:
    def __init__(self):
        self.service_file = os.path.join(workdir, namespace, "version", "service.txt")
        self.image_file = os.path.join(workdir, namespace, "version", "images.list")
        self.image_old = os.path.join(workdir, namespace, "version", "images.old")
        self.temp_file_dir = os.path.join(workdir, namespace, "temp")
        self.temp_image_file = os.path.join(self.temp_file_dir, "image.list_" +
                                            time.strftime("%Y%m%d-%H%M%S", time.localtime()))
        logging.basicConfig(filename=os.path.join(workdir, namespace, "log/deploy.log"),
                            level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')

    @staticmethod
    def _update_basic_service(service_name, service_with_version):

        if namespace == "default":
            output = os.popen('ssh %s "./update_basic_service.sh %s"'
                               % (basic_service_host, service_with_version))

        elif namespace == "develop":
            if "MySQLUAT" in service_name:
                output = os.popen('kubectl exec -n develop mysql-0 -- /tmp/update/update_basic_service.sh %s'
                                   % service_with_version)
            elif "CassandraUAT" in service_name:
                output = os.popen('kubectl exec -n develop cassandra-0 -- /tmp/update/update_basic_service.sh %s'
                                   % service_with_version)
        logging.info("update %s, the output is %s" % (service_with_version, output.readlines()))

    @staticmethod
    def _create_configmap():
        """
        create configMap for update service, use shell script now
        :return:
        """
        if namespace == "default":
            os.system("./create.sh configmap")
        if namespace == "develop":
            os.system("./create_develop.sh configmap")
        logging.info("configMap create done")

    def _update_biz_service(self, image_new_dict):
        """
        make deployment for update service
        :return:
        """
        deploy_dir = os.path.join(workdir, namespace, "deployment")
        time_tag = time.strftime('%Y%m%d-%H%M%S', time.localtime(time.time()))
        deploy_dir_bak = os.path.join(self.temp_file_dir, "deployment-%s" % time_tag)

        if os.path.exists(deploy_dir):
            shutil.copytree(deploy_dir, deploy_dir_bak)
            logging.info("backup deployment to %s" % deploy_dir_bak)
        else:
            os.mkdir(deploy_dir)
            logging.info("mkdir %s successfully" % deploy_dir)

        logging.info("begin to make deployments for %s" % image_new_dict)
        for service_name, service_version in image_new_dict.items():

            if service_name in tomcat_service:
                template_file_dir = os.path.join(workdir, namespace, "template_tomcat")
            else:
                template_file_dir = os.path.join(workdir, namespace, "template_jar")

            template_file_name = env + "-xxxxx-" + service_name + ".yaml"  
            template_file = os.path.join(template_file_dir, template_file_name)
            deploy_file = os.path.join(deploy_dir, template_file_name)
            deploy_temp_file = os.path.join(deploy_dir, template_file_name + ".bak")

            with open(template_file, "r") as f1, open(deploy_temp_file, "w") as f2:
                for content in f1:
                    new_content = content.replace("VERSION_REPLACE", service_version)
                    f2.writelines(new_content)
            # copy on write
            os.rename(deploy_temp_file, deploy_file)
            logging.info("modify %s successfully" % deploy_file)

            # apply deployment yaml
            logging.info("deploying %s " % deploy_file)
            os.system("kubectl apply -f %s --record" % deploy_file)
            time.sleep(1)

    @staticmethod
    def _check_version(service_version):
        """
        check service_version

        :param service_version: must be x.x.x
        """
        reg = '^\d+\.\d+\.\d+$'
        if re.search(reg, service_version):
            return True
        else:
            return False

    def update_service_verison(self):
        """
        download service.txt file from s3 with bigversion,
        service.txt includes all services with newest versions,
        while image.list only includes the services we need to deploy,
        compare this 2 files, we'll get services with their newest version which we need to deploy
        :return: None
        """
        s3 = boto3.resource("s3")
        s3.Bucket(s3_bucket_name).download_file(bigversion, self.service_file)
        # backup image.list to temp_image_file and mv it to image.old
        shutil.copy(self.image_file, self.temp_image_file)
        os.rename(self.image_file, self.image_old)

        dict_tmp = {}
        with open(self.service_file) as f1, open(self.image_old) as f2, open(self.image_file + ".bak", "w") as f3:
            for line in f1:
                service_name = line.split("-")[0]
                dict_tmp[service_name] = line.strip()
            for line in f2:
                service_name = line.split("-")[1]
                if service_name in dict_tmp:
                    image_name = "cloud-" + dict_tmp[service_name] + "\n"
                    f3.write(image_name)
        # copy on write
        os.rename(self.image_file + ".bak", self.image_file)
        logging.info("create image.list successfully")

    def get_update_service(self):
        with open(self.image_file) as f1, open(self.image_old) as f2:
            biz_image_dict = {}
            image_old_list = f2.readlines()
            for line in f1: 
                # find the difference between image.list and image.old
                if line in image_old_list:
                    continue
                service_name = line.split("-")[1]
                service_version = line.strip().split("-")[2]
                if not self._check_version(service_version):
                    print("service_version: %s is illegal" % service_version)
                    sys.exit(1)
                if "UAT" in service_name:
                    self._update_basic_service(service_name, service_with_version=line.strip())
                else:
                    biz_image_dict[service_name] = service_version
        if biz_image_dict:
            self._create_configmap()
            self._update_biz_service(biz_image_dict)


def check_sysargv():
    """
    check system argument variables
    bigversion must start with "CN_BIZ", and namespace must be "default" or "develop"
    """
    try:
        if not sys.argv[2]:
            return False
        if sys.argv[1].startswith("CN_BIZ") and sys.argv[2] in ["default", "develop"]:
            return True
        else:
            return False

    except IndexError:
        return False


if __name__ == "__main__":
    if not check_sysargv():
        print(" Usage: %s CN_BIZ_x.x.x_xxx default | develop" % sys.argv[0])
        sys.exit(0)
    bigversion = "big_version/" + sys.argv[1]
    namespace = sys.argv[2]
    deployment = Deployment()
    deployment.update_service_verison()
    deployment.get_update_service()
