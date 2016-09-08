# encoding:utf-8

import json
import time
import logging
import httplib
import traceback

from django.conf import settings
from django.utils import timezone
from django.shortcuts import render
from django.http import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt

RETU_INFO_SUCCESS = 200
RETU_INFO_ERROR = 201

from kd_agent.logconfig import LOGGING
logging.config.dictConfig( LOGGING )


# 一个装饰器，将原函数返回的json封装成response对象
def return_http_json(func):
    def wrapper( *arg1,**arg2 ):
        try:
            retu_obj = func( *arg1,**arg2 )
            logging.info( 'execute func %s success' % (func) )
        except Exception as reason:
            retu_obj = generate_failure( str(reason) )
            logging.error( 'execute func %s failure : %s' % (func,str(reason)) )
            traceback.print_exc()

        obj = HttpResponse( json.dumps(retu_obj) )
        obj['Access-Control-Allow-Origin'] = '*'
        obj['Access-Control-Allow-Methods'] = 'GET,POST'
        obj['Access-Control-Allow-Headers'] = 'X-CSRFToken'
        obj['Content-Type'] = 'application/json'
        return obj
    return wrapper

def generate_retu_info( code,msg,**ext_info ):
    retu_data = { 'code':code,'msg':msg }
    for k in ext_info:
        retu_data[k] = ext_info[k]
    return retu_data

def generate_success(**ext_info):
    return generate_retu_info( RETU_INFO_SUCCESS,'',**ext_info )

def generate_failure( msg,**ext_info ):
    return generate_retu_info( RETU_INFO_ERROR,msg,**ext_info )

# 去掉时间字符串 2016-07-15T14:38:02Z 中的T、Z
def trans_time_str(time_str):
    return time_str[0:10] + ' ' + time_str[11:19]










