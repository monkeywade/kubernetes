#!/usr/bin/env python
# -*- coding:utf-8 -*-

from typing import List


class DataCenter:
    def __init__(self, env=None, dc=None, apollo_env=None):
        self.env = env
        self.dc = dc
        self.apollo_env = apollo_env

    @staticmethod
    def get_dcs(env_2dc_2apollo_env) -> List:
        dcs = []
        for env in env_2dc_2apollo_env:
            for dc in env_2dc_2apollo_env[env]:
                dcs.append(DataCenter(env, dc, env_2dc_2apollo_env[env][dc]))
        return dcs

    def __str__(self):
        return 'DataCenter<env=%s,dc=%s>' % (self.env, self.dc)


MAINLAND_ENV_2DC_2APOLLO_ENV = {
    'ci-uat': {
        'region-1': 'ci_uat'
    },
    'rd-uat': {
        'region-1': 'rd_uat'
    },
    'ci-prd': {
        'region-1': 'ci_prd'
    },
    'pre-prd': {
        'region-1': 'pre_prd'
    },
    'prd': {
        'region-1': 'prd'
    },
}

GLOBAL_ENV_2DC_2APOLLO_ENV = {
    'ci-uat': {
        'region-1': 'ci_uat'
    },
    'rd-uat': {
        'region-1': 'rd_uat'
    },
    'ci-prd': {
        'region-1': 'ci_prd'
    },
    'pre-prd': {
        'region-1': 'pre_prd_region1',
        'region-2': 'pre_prd_region2',
        'region-3': 'pre_prd_region3',
    },
    'prd': {
        'region-1': 'prd_region1',
        'region-2': 'prd_region2',
        'region-3': 'prd_region3',
    },
}

MAINLAND_DCS = DataCenter.get_dcs(MAINLAND_ENV_2DC_2APOLLO_ENV)
GLOBAL_DCS = DataCenter.get_dcs(GLOBAL_ENV_2DC_2APOLLO_ENV)
