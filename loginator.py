#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 23 17:09:43 2022

@author: jasont
"""

import logging
##################################
# This is a util logger used by all python 
# files in this code base. 
# Simply import this python funtion in your 
# other python files
# from loginator import get_logger
#
#
#
###################################
def get_logger(name):
    log_format = '%(asctime)s  %(name)8s  %(levelname)5s  %(message)s'
    logging.basicConfig(level=logging.DEBUG,
                        format=log_format,
                        filename='aws_web_tools.log',
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter(log_format))
    logging.getLogger(name).addHandler(console)
    return logging.getLogger(name)
