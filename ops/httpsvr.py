#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
This script is to run a http server, and receive information for deployment

Options:
    None

Version: 1.2.0
"""

import time
import threading
import flask
from flask import request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from start_deploy import Deployment
from k8s_api import KubernetesApi
from template_render import render_template

DEPLOY_NAMESPACE = ["default", "develop"]

server = flask.Flask(__name__)


@server.route('/template_render', methods=['post'])
def get_render_info_from_user():
    params = request.json
    server.logger.info("[INFO] - get params from user\n%s" % params)
    kuboard_layer = params.get("kuboard_layer")
    service_type = params.get("service_type")
    service_name = params.get("service_name")
    namespace = params.get("namespace")
    container_port = params.get("container_port")
    node_port = params.get("node_port")
    msg = render_template(kuboard_layer, service_type, service_name, namespace, container_port, node_port)
    return jsonify({"msg": msg})


@server.route('/mainland/aws/uat/deploy', methods=['get'])
def get_deployment_status():
    """
    return deployment status
    :return: "success" or "fail"
    """
    params = request.values
    try:
        namespace = params.get('namespace')
        if not namespace:
            namespace = "default"
        k8s_api = KubernetesApi(namespace)
        unavailable_replicas_list = k8s_api.get_unavailable_replicas()
        if unavailable_replicas_list:
            server.logger.warning("unavailable replicas found. Info: %s" % unavailable_replicas_list)
            data = {
                "env": "test-uat",
                "namespace": namespace,
                "status": "fail",
                "msg": "unavailable replicas found: %s" % unavailable_replicas_list
            }
        else:
            data = {
                "env": "test-uat",
                "namespace": namespace,
                "status": "success",
            }
        return jsonify(data)

    except AttributeError:
        return "params not found", 501
    except Exception as e:
        server.logger.error("[ERROR] - http server internal error, the exception is %s" % e)


@server.route('/mainland/aws/uat/deploy', methods=['post'])
def get_bigversion_from_pub():
    """
    receive "bigversion", "email", "env", "update_time" from front-end users
    """
    if request.method != "POST":
        server.logger.error("[ERROR] - method error, expect POST but others")
        return "method not allowd", 403

    # get params with json format, type dict
    params = request.json
    """
    :param str bigversion: bigversion from release system
    :param str email: 
    :param str env: to distinguish different enviroment
    :param datetime update_time: time to run a update task, like "2020-9-2 15:30:00"
    """
    try:
        bigversion = params.get('bigversion')
        email = params.get('email')
        env = params.get('type')
        update_time = params.get('update_time')
        check_result = check_params(bigversion, email, env, update_time)
        if not check_result[0]:
            return check_result[1:]

        # write "bigversion" and "update_time" into release_info.txt
        with open("release_info.txt", "r+") as f:
            # if "update_time" has been in release_info.txt, then break
            for line in f:
                if update_time in line:
                    server.logger.warning("[WARNING] - find duplicate update_time in release_info.txt")
                    data = {
                        "msg": "A task has been scheduled at %s with bigversion %s" % (update_time, bigversion)
                    }
                    return jsonify(data), 403
            f.write(bigversion + " " + update_time + "\n")
            server.logger.info("[INFO] - receive update massage: bigversion:%s at %s, send email to %s\n" %
                               (bigversion, update_time, email))
        # run task at update_time
        schedule_task(bigversion, update_time)
        server.logger.info("[INFO] - scheduleTask successfully")
        data = {
            "code": 200,
            "msg": "message sent successfully, update will be run at %s" % update_time
        }
        return jsonify(data)

    except AttributeError:
        return "params not found", 501
    except Exception as e:
        server.logger.error("[ERROR] - http server internal error, the exception is %s" % e)


def check_params(bigversion, email, env, update_time):
    if not bigversion:
        server.logger.error("[ERROR] - bigversion not found")
        return False, "bigversion not found", 501
    if not email:
        server.logger.error("[ERROR] - email not found")
        return False, "email not found", 501
    if not env:
        server.logger.error("[ERROR] - type not found")
        return False, "type not found", 501
    if env != "uat":
        server.logger.warning("[WARNING] - type error, expect value uat")
        return False, "message sent successfully but type not match", 403
    if not update_time:
        server.logger.error("[ERROR] - update_time not found")
        return False, "update_time not found", 501
    if time.mktime(time.strptime(update_time, '%Y-%m-%d %H:%M:%S')) < time.time():
        return False, "update_time is older than the current time", 403



def schedule_task(bigversion, update_time):
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_task, 'date', run_date=update_time, args=[bigversion])
    scheduler.start()


def run_task(bigversion):
    threads = []
    for namespace in DEPLOY_NAMESPACE:
        deployment = Deployment(namespace, bigversion)
        deployment.update_service_verison()
        t = threading.Thread(target=deployment.update_service)
        threads.append(t)
        t.start()
    for thread in threads:
        thread.join()


if __name__ == '__main__':
    server.run(debug=True, port=30009, host='0.0.0.0')
