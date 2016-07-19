# encoding:utf-8

import json
import time
import logging
import httplib
import traceback

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
        try:
            retu_obj = func( *arg1,**arg2 )
            logging.info( 'execute func %s success' % (func) )
        except Exception as reason:
            retu_obj = generate_failure( str(reason) )
            logging.error( 'execute func %s failure : %s' % (func,str(reason)) )

        obj = HttpResponse( json.dumps(retu_obj) )
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

# 去掉时间字符串 2016-07-15T14:38:02Z 中的T、Z
def trans_time_str(time_str):
    return time_str[0:10] + ' ' + time_str[11:19]

# 根据原生的API获取k8s的数据
def get_k8s_data(url,params = {},timeout = 10 ):
    resp = None
    try:
        con = httplib.HTTPConnection(settings.K8S_IP, settings.K8S_PORT, timeout=timeout)
        con.request('GET', url, json.dumps(params, ensure_ascii=False))
        resp = con.getresponse()
        if not resp:
            s = 'get k8s data resp is not valid : %s' % resp
            logging.error( s )
            return generate_failure( s )

        if resp.status == 200:
            s = resp.read()
            logging.debug( 'get k8s data response : %s' % s )
            return generate_success( data = json.loads(s) )
        else:
            s = 'get k8s data status is not 200 : %s' % resp.status
            logging.error( s )
            return generate_failure( s )
    except Exception, e:
        s = "get k8s data occured exception : %s" % str(e)
        logging.error(s)
        return generate_failure( s )
    

@csrf_exempt
@return_http_json
def get_pod_list(request,namespace):
    logging.info( 'call get_pod_list request.path : %s , namespace : %s' % (request.path,namespace) )
    pod_detail_info = get_k8s_data( request.path )
    if pod_detail_info['code'] == 0:
        logging.error( 'call get_pod_list query k8s data error : %s' % pod_detail_info['msg'] )
        return generate_failure( pod_detail_info['msg'] )

    retu_data = []
    for item in pod_detail_info['data']['items']:
        record = {}
        retu_data.append(record)
        record['Name'] = item['metadata']['name']
        record['CreationTime'] = trans_time_str(item['metadata']['creationTimestamp'])
        record['Node'] = item['spec']['nodeName']

        containerStatuses = item['status']['containerStatuses']
        total = len(containerStatuses)
        running = 0
        for cItem in containerStatuses:
            if cItem['state'].get( 'running' ) != None:
                running += 1
        record['Ready'] = '%s / %s' % ( running,total )

        if total == running:
            record['Status'] = 'Running'
        else:
            #TODO:此处需要测试
            statusArr = []
            for cItem in containerStatuses:
                statusArr.append( cItem['state']['waiting']['reason'] )   
            record['Status'] = '{ %s }' % str(',').join( set(statusArr) )

        restartCountArr = []
        for cItem in containerStatuses:
            restartCountArr.append( cItem['restartCount'] )
        record['Restarts'] = sum(restartCountArr)
    
    logging.debug( 'call get_pod_list query k8s data : %s' % retu_data )
    logging.info( 'call get_pod_list query k8s data successful' )
    return generate_success( data = retu_data )


@csrf_exempt
@return_http_json
def get_service_list(request,namespace):
    logging.info( 'call get_service_list request.path : %s , namespace : %s' % (request.path,namespace) )
    service_detail_info = get_k8s_data( request.path )
    if service_detail_info['code'] == 0:
        logging.error( 'call get_service_list query k8s data error : %s' % service_detail_info['msg'] )
        return generate_failure( service_detail_info['msg'] )

    retu_data = []
    for item in service_detail_info['data']['items']:
        record = {}
        retu_data.append(record) 

        record['Name'] = item['metadata']['name']
        record['ClusterIP'] = item['spec']['clusterIP']
        record['ExternalIP'] = '<None-IP>'      #TODO:mini的测试暂时没有这个东西，这里暂时填充 <none-IP>
        record['CreationTime'] = trans_time_str( item['metadata']['creationTimestamp'] )
        
        ports_info_arr = []
        for cItem in item['spec']['ports']:
            ports_info_arr.append( '%s/%s' % ( cItem['port'],cItem['protocol'] ) )
        record['Ports'] = str(',').join(ports_info_arr)

        if not item['spec'].get('selector'):
            record['Selector'] = '<None>'
        else:
            selector_info_arr = []
            for k,v in item['spec']['selector'].iteritems():
                selector_info_arr.append( '%s=%s' % (k,v) )
            record['Selector'] = str(',').join( selector_info_arr )

    logging.debug( 'call get_service_list query k8s data : %s' % retu_data )
    logging.info( 'call get_service_list query k8s data successful' )
    return generate_success( data = retu_data )


@csrf_exempt
@return_http_json
def get_rc_list(request,namespace):
    logging.info( 'call get_rc_list request.path : %s , namespace : %s' % (request.path,namespace) )
    rc_detail_info = get_k8s_data( request.path )
    if rc_detail_info['code'] == 0:
        logging.error( 'call get_rc_list query k8s data error : %s' % rc_detail_info['msg'] )
        return generate_failure( rc_detail_info['msg'] )

    retu_data = []
    for item in rc_detail_info['data']['items']:
        record = {}
        retu_data.append(record) 

        record['Name'] = item['metadata']['name']
        record['Desired'] = item['spec']['replicas']
        record['Current'] = item['status']['replicas']      #TODO:Current暂时这样取值
        record['CreationTime'] = trans_time_str( item['metadata']['creationTimestamp'] )
        
        container_arr = []
        image_arr = []
        for cItem in item['spec']['template']['spec']['containers']:
            container_arr.append( cItem['name'] )
            image_arr.append( cItem['image'] )
        record['Containers'] = str(',').join( container_arr )
        record['Images'] = str(',').join( image_arr )
        
        if not item['spec'].get('selector'):
            record['Selector'] = '<None>'
        else:
            selector_info_arr = []
            for k,v in item['spec']['selector'].iteritems():
                selector_info_arr.append( '%s=%s' % (k,v) )
            record['Selector'] = str(',').join( selector_info_arr )
    
    logging.debug( 'call get_rc_list query k8s data : %s' % retu_data )
    logging.info( 'call get_rc_list query k8s data successful' )
    return generate_success( data = retu_data )




