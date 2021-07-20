#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
get data from cluster with kubernetes python api

Version: 1.0.0
"""


from kubernetes import client, config


class KubernetesApi:
    def __init__(self, namespace):
        config.kube_config.load_kube_config(config_file="~/.kube/config")
        # 获取API的CoreV1Api版本对象
        self.core_api = client.CoreV1Api()  # namespace,pod,service,pv,pvc
        self.apps_api = client.AppsV1Api()  # deployment
        self.namespace = namespace

    def get_unavailable_replicas(self):
        """
        get unavailable replicas of deployment
        :return:
        """
        ret = self.apps_api.list_namespaced_deployment(self.namespace)
        unavailable_replicas_list = []
        for item in ret.items:
            if item.status.unavailable_replicas:
                service_name = item.metadata.name
                unavailable_replicas = item.status.unavailable_replicas
                data_info = {
                    "namespace": self.namespace,
                    "service_name": service_name,
                    "unavailable_replicas": unavailable_replicas
                }
                unavailable_replicas_list.append(data_info)
        return unavailable_replicas_list

    def get_service_info(self, service_name):
        ret = self.core_api.read_namespaced_service_status(service_name, self.namespace)
        cluster_ip = ret.spec.cluster_ip
        ports = ret.spec.ports
        service_type = ret.spec.type
        session_affinity = ret.spec.session_affinity
        info = {
            "cluster_ip": cluster_ip,
            "ports": ports,
            "service_type": service_type,
            "session_affinity": session_affinity,
        }
        return info
