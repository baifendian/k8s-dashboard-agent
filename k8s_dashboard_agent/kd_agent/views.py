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


class Logger():
    def debug( self,disStr ):
        print 'debug',disStr
    def info( self,disStr ):
        print 'info',disStr
    def warning( self,disStr ):
        print 'warning',disStr
    def error( self,disStr ):
        print 'error',disStr

kd_logger = Logger()

class settings:
    K8S_IP = '172.24.3.150'
    K8S_PORT = 8080


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
            kd_logger.error( s )
            return generate_failure( s )

        if resp.status == 200:
            s = resp.read()
            kd_logger.debug( 'get k8s data response : %s' % s )
            return generate_success( data = json.loads(s) )
        else:
            s = 'get k8s data status is not 200 : %s' % resp.status
            kd_logger.error( s )
            return generate_failure( s )
    except Exception, e:
        s = "get k8s data occured exception : %s" % str(e)
        kd_logger.error(s)
        return generate_failure( s )

def restore_k8s_path(p):
    return p.replace('/k8s','')

def trans_obj_to_easy_dis(obj_info):
    return json.dumps(obj_info, indent=1).split('\n')


@csrf_exempt
@return_http_json
def get_pod_list(request,namespace):
    kd_logger.info( 'call get_pod_list request.path : %s , namespace : %s' % (request.path,namespace) )
    pod_detail_info = get_k8s_data( restore_k8s_path(request.path) )
    if pod_detail_info['code'] == RETU_INFO_ERROR:
        kd_logger.error( 'call get_pod_list query k8s data error : %s' % pod_detail_info['msg'] )
        return generate_failure( pod_detail_info['msg'] )

    retu_data = []
    for item in pod_detail_info['data']['items']:
        record = {}
        retu_data.append(record)
        record['Name'] = item['metadata']['name']
        record['CreationTime'] = trans_time_str(item['metadata']['creationTimestamp'])
        record['Node'] = item['spec']['nodeName']
        record['DetailInfo'] = trans_obj_to_easy_dis(item)

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
                statusArr.append( cItem['state'][ cItem['state'].keys()[0] ]['reason'] )   
            record['Status'] = '{ %s }' % str(',').join( set(statusArr) )

        restartCountArr = []
        for cItem in containerStatuses:
            restartCountArr.append( cItem['restartCount'] )
        record['Restarts'] = sum(restartCountArr)
    
    kd_logger.debug( 'call get_pod_list query k8s data : %s' % retu_data )
    kd_logger.info( 'call get_pod_list query k8s data successful' )
    return generate_success( data = retu_data )

@csrf_exempt
@return_http_json
def get_service_list(request,namespace):
    kd_logger.info( 'call get_service_list request.path : %s , namespace : %s' % (request.path,namespace) )
    service_detail_info = get_k8s_data( restore_k8s_path(request.path) )
    if service_detail_info['code'] == RETU_INFO_ERROR:
        kd_logger.error( 'call get_service_list query k8s data error : %s' % service_detail_info['msg'] )
        return generate_failure( service_detail_info['msg'] )

    retu_data = []
    for item in service_detail_info['data']['items']:
        record = {}
        retu_data.append(record) 

        record['Name'] = item['metadata']['name']
        record['ClusterIP'] = item['spec']['clusterIP']
        record['ExternalIP'] = '<None-IP>'      #TODO:mini的测试暂时没有这个东西，这里暂时填充 <none-IP>
        record['CreationTime'] = trans_time_str( item['metadata']['creationTimestamp'] )
        record['DetailInfo'] = trans_obj_to_easy_dis(item)

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

    kd_logger.debug( 'call get_service_list query k8s data : %s' % retu_data )
    kd_logger.info( 'call get_service_list query k8s data successful' )
    return generate_success( data = retu_data )

@csrf_exempt
@return_http_json
def get_rc_list(request,namespace):
    kd_logger.info( 'call get_rc_list request.path : %s , namespace : %s' % (request.path,namespace) )
    rc_detail_info = get_k8s_data( restore_k8s_path(request.path) )
    if rc_detail_info['code'] == RETU_INFO_ERROR:
        kd_logger.error( 'call get_rc_list query k8s data error : %s' % rc_detail_info['msg'] )
        return generate_failure( rc_detail_info['msg'] )

    retu_data = []
    for item in rc_detail_info['data']['items']:
        record = {}
        retu_data.append(record) 

        record['Name'] = item['metadata']['name']
        record['Desired'] = item['spec']['replicas']
        record['Current'] = item['status']['replicas']      #TODO:Current暂时这样取值
        record['CreationTime'] = trans_time_str( item['metadata']['creationTimestamp'] )
        record['DetailInfo'] = trans_obj_to_easy_dis(item)

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
    
    kd_logger.debug( 'call get_rc_list query k8s data : %s' % retu_data )
    kd_logger.info( 'call get_rc_list query k8s data successful' )
    return generate_success( data = retu_data )

@csrf_exempt
@return_http_json
def get_ingress_list(request,namespace):
    kd_logger.info( 'call get_ingress_list request.path : %s , namespace : %s' % (request.path,namespace) )
    ingress_detail_info = get_k8s_data( restore_k8s_path(request.path) )
    if ingress_detail_info['code'] == RETU_INFO_ERROR:
        kd_logger.error( 'call get_ingress_list query k8s data error : %s' % ingress_detail_info['msg'] )
        return generate_failure( ingress_detail_info['msg'] )

    retu_data = []
    for item in ingress_detail_info['data']['items']:
        record = {}
        retu_data.append(record)
        record['Name'] = item['metadata']['name']

        try:    
            record['Ingress'] = []
            for ing in item['status']['loadBalancer']['ingress']:
                record['Ingress'].append( ing['ip'] )
        except: 
            record['Ingress'] = '<None>'

        try:    record['Rules'] = get_ingress_detail_host_info( item['spec']['rules'] )
        except: record['Rules'] = []
         
        record['CreationTime'] = trans_time_str(item['metadata']['creationTimestamp'])
        record['DetailInfo'] = trans_obj_to_easy_dis(item)
    
    kd_logger.debug( 'call get_ingress_list query k8s data : %s' % retu_data )
    kd_logger.info( 'call get_ingress_list query k8s data successful' )
    return generate_success( data = retu_data )




#####################################################################################################
# 以下是新增的代码
#####################################################################################################


def get_overview_k8s_pod_info(namespace):
    retu_data = { 'count':0, 'total':0 }
    url = '/api/v1/namespaces/%s/pods' % namespace
    pod_detail_info = get_k8s_data( url )
    if pod_detail_info['code'] == RETU_INFO_ERROR:
        kd_logger.error( 'call get_overview_k8s_pod_info query k8s pod data error : %s' % pod_detail_info['msg'] )
    else:
        count = 0
        total = 0
        for item in pod_detail_info['data']['items']:
            containerStatuses = item['status']['containerStatuses']
            total += len(containerStatuses)
            for cItem in containerStatuses:
                if cItem['state'].get( 'running' ) != None:
                    count += 1
        retu_data['count'] = count
        retu_data['total'] = total
    return retu_data

def get_overview_k8s_service_info(namespace):
    retu_data = { 'count':0  }
    url = '/api/v1/namespaces/%s/services' % namespace
    service_detail_info = get_k8s_data( url )
    if service_detail_info['code'] == RETU_INFO_ERROR:
        kd_logger.error( 'call get_overview_k8s_service_info query k8s service data error : %s' % service_detail_info['msg'] )
    else:
        retu_data['count'] = len(service_detail_info['data']['items'])
    return retu_data

def get_overview_k8s_rc_info(namespace):
    retu_data = { 'count':0, 'total':0 }
    url = '/api/v1/namespaces/%s/replicationcontrollers' % namespace
    rc_detail_info = get_k8s_data( url )
    if rc_detail_info['code'] == RETU_INFO_ERROR:
        kd_logger.error( 'call get_overview_k8s_rc_info query k8s rc data error : %s' % rc_detail_info['msg'] )
    else:
        total = 0
        count = 0
        for item in rc_detail_info['data']['items']:
            total += item['spec']['replicas']
            count += item['status']['replicas']
        retu_data['count'] = count
        retu_data['total'] = total
    return retu_data

# node要从influxdb中获取数量，但是当前无法获取，因此该函数的实现暂时先搁置。
def get_overview_k8s_node_info(namespace):
    retu_data = { 'count':0 }
    return retu_data

@csrf_exempt
@return_http_json
def get_k8soverview_info(request,namespace):
    retu_data = {
        'pod': get_overview_k8s_pod_info(namespace) ,
        'rc': get_overview_k8s_rc_info(namespace),
        'service': get_overview_k8s_service_info(namespace),
        'node': get_overview_k8s_node_info(namespace)
    }
    kd_logger.info( 'call get_overview_k8s_rc_info query k8s overview info : %s' % retu_data )
    return generate_success( data=retu_data )
