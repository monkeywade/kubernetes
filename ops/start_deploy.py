#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
This script is to start a deployment with big_version

Options:
    None

Version: 1.2.0
"""

import os
import shutil
import sys
import time
import re
import tarfile
import boto3
import logging
import logging.config
import requests
from k8s_api import KubernetesApi
import settings


class Deployment:
    def __init__(self, namespace, bigversion):
        self.namespace = namespace
        self.bigversion = bigversion
        self.service_file = os.path.join(settings.WORK_DIR, self.namespace, "version", "service.txt")
        self.image_file = os.path.join(settings.WORK_DIR, self.namespace, "version", "images.list")
        self.image_old = os.path.join(settings.WORK_DIR, self.namespace, "version", "images.old")
        self.basic_service_dir = os.path.join(settings.WORK_DIR, self.namespace, "basic_service")
        self.temp_file_dir = os.path.join(settings.WORK_DIR, self.namespace, "temp")
        self.temp_image_file = os.path.join(self.temp_file_dir, "image.list_" +
                                            time.strftime("%Y%m%d-%H%M%S", time.localtime()))
        logging.config.dictConfig(settings.LOGGER)
        self.logger = logging.getLogger(self.namespace)

    def update_service_verison(self):
        """
        download service.txt file from s3 with bigversion,
        service.txt includes all services with newest versions,
        while image.list only includes the services we need to deploy,
        compare this 2 files, we'll get services with their newest version which we need to deploy
        :return: None
        """
        obj_key = "big_version/" + self.bigversion
        status = self._download_file_from_s3(obj_key, self.service_file)
        if not status:
            self.logger.error("create image.list fail, file not found in s3")
            return

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
        self.logger.info("create image.list success")

    def update_service(self):
        with open(self.image_file) as f1, open(self.image_old) as f2:
            biz_image_dict = {}
            image_old_list = f2.readlines()
            for line in f1:
                # find the difference between image.list and image.old
                if line in image_old_list:
                    continue
                service_with_version = line.strip()
                service_name = service_with_version.split("-")[1]
                service_version = service_with_version.split("-")[2]  # eg: 3.19.0
                if not self._check_version(service_version):
                    self.logger.error("service_version: %s is illegal" % service_version)
                    continue
                if "UAT" in service_name:
                    self._update_basic_service(service_name, service_version)
                else:
                    biz_image_dict[service_name] = service_version
        if biz_image_dict:
            self._create_configmap()
            self._update_biz_service(biz_image_dict)

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

    def _download_file_from_s3(self, object_key, destfile):
        s3 = boto3.resource("s3")
        try:
            s3.Bucket(settings.S3_BUCKET).download_file(object_key, destfile)
            return True
        except Exception as e:
            self.logger.exception("Object Not Found. Exception:", e)
            return False

    def _update_basic_service(self, service_name, service_version):
        # make deploy dir if not exists
        update_service_path = os.path.join(self.basic_service_dir, service_name)
        if not os.path.exists(update_service_path):
            os.makedirs(update_service_path)
            self.logger.info("mkdir %s success" % update_service_path)

        # download update package from s3
        tag_region = "CN" if settings.DEPLOY_ENV == "mainland" else "EN"
        obj_prefix = '%s/%s-%s-%s-' % (service_name, service_name, tag_region, service_version)
        client = boto3.client('s3')
        response = client.list_objects(Bucket=settings.S3_BUCKET,
                                       Prefix=obj_prefix, )
        obj_key = response.get('Contents')[0].get('Key')
        if not obj_key:
            self.logger.error("%s update failed, can not find s3 object." % service_name)
            return

        update_file = os.path.join(self.basic_service_dir, obj_key)
        # untar dir path
        update_file_path = os.path.join(update_service_path, service_version)
        status = self._download_file_from_s3(obj_key, update_file)
        if not status:
            self.logger.error("update %s-%s error, file not found" % (service_name, service_version))
            return

        # untar and execute update.sql
        self._untar(update_file, update_file_path)
        update_host = settings.BASIC_SVC_HOST_MAP.get(self.namespace)
        if "MySQL" in service_name:
            output = os.system(
                "cd %s; mysql -uuser -ppassword -h%s < update.sql;" % (update_file_path, update_host))
        elif "Cassandra" in service_name:
            output = os.system("cd %s; cqlsh %s -f update_*assandra.cql;" % (update_file_path, update_host))
        else:
            output = 0
        if output == 0:
            self.logger.info("update %s-%s success" % (service_name, service_version))
        else:
            self.logger.error("update %s-%s error" % (service_name, service_version))

    def _create_configmap(self):
        """
        create configMap for update service, use shell script now
        :return:
        """
        if self.namespace == "default":
            os.system("./create.sh configmap")
        if self.namespace == "develop":
            os.system("./create_develop.sh configmap")
        self.logger.info("configMap create done")

    def _update_biz_service(self, image_new_dict):
        """
        make deployment for update service
        :return:
        """
        # backup deployment files
        deploy_dir = self._backup_deploy_file()

        self.logger.info("begin to make deployments for %s" % image_new_dict)
        for service_name, service_version in image_new_dict.items():

            if service_name in settings.TOMCAT_SVC:
                template_file_dir = os.path.join(settings.WORK_DIR, self.namespace, "template_tomcat")
            else:
                template_file_dir = os.path.join(settings.WORK_DIR, self.namespace, "template_jar")

            template_file_name = settings.DEPLOY_ENV + "-cloud-" + service_name + ".yaml"
            template_file = os.path.join(template_file_dir, template_file_name)
            deploy_file = os.path.join(deploy_dir, template_file_name)
            deploy_temp_file = os.path.join(deploy_dir, template_file_name + ".bak")

            with open(template_file, "r") as f1, open(deploy_temp_file, "w") as f2:
                for content in f1:
                    new_content = content.replace("VERSION_REPLACE", service_version)
                    f2.writelines(new_content)
            # copy on write
            os.rename(deploy_temp_file, deploy_file)
            self.logger.info("modify %s success" % deploy_file)

            # apply deployment yaml
            output = os.system("kubectl apply -f %s --record" % deploy_file)
            self.logger.info("deploying %s " % deploy_file)
            if output:
                self.logger.error("%s:%s update failed" % (service_name, service_version))
            time.sleep(20)

    def _backup_deploy_file(self):
        deploy_file_dir = os.path.join(settings.WORK_DIR, self.namespace, "deployment")
        if os.path.exists(deploy_file_dir):
            time_tag = time.strftime('%Y%m%d-%H%M%S', time.localtime(time.time()))
            deploy_file_dir_bak = os.path.join(settings.WORK_DIR, self.namespace, "temp", "deployment-%s" % time_tag)
            shutil.copytree(deploy_file_dir, deploy_file_dir_bak)
            self.logger.info("backup %s to %s" % (deploy_file_dir, deploy_file_dir_bak))
        else:
            os.makedirs(deploy_file_dir)
            self.logger.info("mkdir %s success" % deploy_file_dir)
        return deploy_file_dir

    def _untar(self, tar_name, target_dir):
        """
        decompression the file, support tar tar.gz tar.bz2
        Args:
            tar_name (str): source tar file path, eg: /home/ubuntu/source.tar.gz
            target_dir (str): target dir path, eg: /home/ubuntu/temp
        """
        try:
            t = tarfile.open(tar_name)
            t.extractall(path=target_dir)
        except Exception as e:
            error_msg = 'Decompression file: %s failed' % tar_name
            self.logger.exception(error_msg, e)
