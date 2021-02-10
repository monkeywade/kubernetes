#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
This script is to run a http server, and receive information for deployment

Options:
    None
    
Version: 1.2.0
"""

import os
import time
from datetime import datetime
import flask
from flask import request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

server = flask.Flask(__name__)
@server.route('/bigversion', methods=['get', 'post'])

def get_bigversion_from_pub():
    """
    receive "bigversion", "email", "type", "update_time" from front-end users
    """
    if request.method != "POST":
        server.logger.error("[ERROR] - method error, expect POST but others")
        return "method not allowd", 403

    # get params with json format, type dict
    params = request.json
    try:
        bigversion = params.get('bigversion')
        email = params.get('email')
        type = params.get('type')
        update_time = params.get('update_time')
        check_result = check_params(bigversion, email, type, update_time)
        if not check_result[0]:
            return check_result[1:]

        # write "bigversion" and "update_time" into release_info.txt
        with open("release_info.txt", "r+") as f:
            # if "update_time" has been in release_info.txt, then break
            for line in f:
                if update_time in line:
                    server.logger.warning("[WARNING] - find duplicate update_time in release_info.txt")
                    return jsonify({"msg": "A task has been scheduled at %s with bigversion %s" %
                                           (update_time, bigversion)}), 403
                f.write(bigversion + " " + update_time + "\n")
                server.logger.info("[INFO] - receive update massage: bigversion:%s at %s, send email to %s\n" %
                                   (bigversion, update_time, email))
        # use BackgroundScheduler to run task at update_time
        schedule_task(bigversion, update_time)
        server.logger.info("[INFO] - scheduleTask successfully")
        return jsonify({"code": 200, "msg": "message sent successfully, update will be run at %s" % update_time})

    except Exception as e:
        server.logger.error("[ERROR] - http server internal error, the exception is %s" % e)

def check_params(bigversion, email, type, update_time):

    if not bigversion:
        server.logger.error("[ERROR] - bigversion not found")
        return False, "bigversion not found", 501
    if not email:
        server.logger.error("[ERROR] - email not found")
        return False, "email not found", 501
    if not type:
        server.logger.error("[ERROR] - type not found")
        return False, "type not found", 501
    if type != "uat":
        server.logger.warning("[WARNING] - type error, expect value uat")
        return False, "message sent successfully but type not match", 403
    if not update_time:
        server.logger.error("[ERROR] - update_time not found")
        return False, "update_time not found", 501
    if time.mktime(time.strptime(update_time, '%Y-%m-%d %H:%M:%S')) < time.time():
        return False, "update_time is older than the current time", 403
    if str(bigversion).startswith("CN_BIZ"):
        return True, ""
    else:
        return False, "bigversion must start with 'CN_BIZ'"

def scheduleTask(bigversion, update_time):
    scheduler = BackgroundScheduler()
    scheduler.add_job(runTask, 'date', run_date=update_time, args=[bigversion])
    scheduler.start()

def runTask(bigversion):
    os.popen("python3 ./start_deploy.py %s default" % bigversion)
    os.popen("python3 ./start_deploy.py %s develop" % bigversion)

if __name__ == '__main__':
    server.run(debug=True, port=30009, host='0.0.0.0')
