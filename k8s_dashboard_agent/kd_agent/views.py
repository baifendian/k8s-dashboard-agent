# encoding:utf-8

import json
import time
import logging
import httplib

from django.conf import settings
from django.utils import timezone
from django.shortcuts import render
from django.conf import settings
from django.http import *
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from kd_agent.logconfig import LOGGING



logging.config.dictConfig( LOGGING )


# 一个装饰器，将原函数返回的json封装成response对象
def return_http_json(func):
    def wrapper( *arg1,**arg2 ):
        d = func( *arg1,**arg2 )
        obj = HttpResponse( json.dumps(d) )
        obj['Access-Control-Allow-Origin'] = '*'
        return obj
    return wrapper

def generate_retu_info( code,msg,**ext_info ):
    retu_data = { 'code':code,'msg':msg }
    for k in ext_info:
        retu_data[k] = ext_info[k]
    return retu_data

def generate_success(**ext_info):
    return generate_retu_info( 1,'',**ext_info )

def generate_failure( msg,**ext_info ):
    return generate_retu_info( 0,msg,**ext_info )

# 根据原生的API获取k8s的数据
def get_k8s_data(url,params = {},timeout = 10 ):
    resp = None
    try:
        con = httplib.HTTPConnection(settings.K8S_IP, settings.K8S_PORT, timeout=timeout)
        con.request('GET', url, json.dumps(params, ensure_ascii=False))
        resp = con.getresponse()
    except Exception, e:
        logging.error("query k8s data occured exception : %s", str(e))
            
    jo = None
    if resp and resp.status == 200:
        s = resp.read()
        logging.debug("k8s response : %s", s)
        try:
	        jo = json.loads(s)
        except Exception, e:
            logging.error("k8s response not json")
        return jo

@csrf_exempt
@return_http_json
def get_pod_list(request,namespace):
    pod_detail_info = get_k8s_data( request.path )
    if pod_detail_info == None:
        return generate_failure()

    retu_data = []
    for item in pod_detail_info['items']:
        d = {}
        d['Name'] = item['metadata']['name']
        
        d['Ready'] = 'None'
        d['Status'] = 'None'
        d['Restarts'] = 'None'
      
        d['CreationTime'] = item['metadata']['creationTimestamp']
        d['Node'] = item['spec']['nodeName']
        retu_data.append(d)

    return generate_success( data = retu_data )


