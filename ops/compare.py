#! /usr/bin/python3

##################################################################################
# Filename   : compare.py
# Version    : 1.0.0
# Description: compare running deployment with all deployments
# Author     : monkeywade
# History    : 2020-04-30 first create
##################################################################################

import os

file_name=
cmd = "kubectl get pods -l app |grep Running"
get_pod = os.popen(cmd)
po_list = []

for item in get_pod.readlines():
    po_list.append(item.split("-")[0])
with open(file_name) as f:
    count = 0
    for line in f:
        mod_name = line.split("-")[1].lower()
        if mod_name in po_list:
            pass
        else:
            count += 1
            print(mod_name)
    print("\n" + str(count) + " modules haven't deployed" + "\n")
