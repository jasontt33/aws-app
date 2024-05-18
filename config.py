#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 23 16:39:59 2022

@author: rogert
"""

##############################################################
# Parameter store getter
# retrieves parameters to be used in application configuration
# NOT recommended for secrets, use secrets manager for those
##############################################################

import boto3
from botocore.exceptions import ClientError
from loginator import get_logger

logger = get_logger('app')

ssm = boto3.client('ssm', 'us-east-1')

def get_cognito_settings():
    response = ssm.get_parameters(
        Names=['/staging/aws-app'],WithDecryption=True
    )
    for parameter in response['Parameters']:
        return parameter['Value']

get_cognito_settings()

