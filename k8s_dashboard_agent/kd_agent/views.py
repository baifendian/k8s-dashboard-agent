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


#####################################################################################################
# 以下是新增的代码
#####################################################################################################


import urllib
import time
from kd_agent.influxdbquerystrmanager import InfluxDBQueryStrManager as ISM

def get_influxdb_data(sql_str,db = settings.INFLUXDB_DATABASE,epoch='s',timeout = 10 ):
    params = { 'q':sql_str, 'db':db, 'epoch':epoch }
    url_str = '/query?%s' % urllib.urlencode( params ) 
    resp = None
    try:
        con = httplib.HTTPConnection(settings.INFLUXDB_IP, settings.INFLUXDB_PORT, timeout=10)
        con.request('GET',url_str)
        resp = con.getresponse()
        if not resp:
            s = 'get inluxdb data resp is not valid : %s' % resp
            return generate_failure( s )

        if resp.status == 200:
            s = resp.read()
            return generate_success( data = json.loads(s) )
        else:
            s = 'get inluxdb data status is not 200 : %s' % resp.status
            return generate_failure( s )
    except Exception, e:
        s = "get inluxdb data occured exception : %s" % str(e)
        return generate_failure( s )

def filter_valid_data( influxdb_data_dict ):
    try:
        columns = influxdb_data_dict['results'][0]['series'][0]['columns']
        series_values = influxdb_data_dict['results'][0]['series'][0]['values']

        retu_data = []
        for item in series_values:
            # item是一个list，item[0]为时间戳，item[1]为value
            if item[1] != None:
                retu_data.append( item )
        return generate_success( data=retu_data )
    except Exception as reason:
        return generate_failure( str(reason) )


def trans_struct_to_easy_dis( filter_data_dict ):
    def map_timestamp_to_localtime( time_stamp ):
        return time.strftime( '%Y-%m-%d %H:%M:%S',time.localtime( time_stamp ) )    
    d = ISM.get_measurement_disname_dict()

    retu_data = {
        'series':[],
        'xaxis':[]
    }

    time_points = set()
    for measurement,data_arr in filter_data_dict.items():
        series_obj = {
            'legend':d[measurement],
            'data':[]
        }
        for item in data_arr:
            time_points.add( item[0] )
            series_obj['data'].append( item[1] )        
        retu_data['series'].append(series_obj)
    
    time_points = list(time_points)
    time_points.sort()
    retu_data['xaxis'] = map( map_timestamp_to_localtime,time_points )
    return retu_data


def execute_clusterinfo_request( sql_str_dict ):
    retu_obj = {}
    for m,sql in sql_str_dict.items():        
        # 获取influxdb原生数据
        retu_data = get_influxdb_data(sql_str=sql)
        if retu_data['code'] != RETU_INFO_SUCCESS:
            return generate_failure( retu_data['msg'] )

        # 对获取到的influx数据进行筛选，只保留有用的数据
        retu_data = filter_valid_data(retu_data['data'])
        if retu_data['code'] != RETU_INFO_SUCCESS:
            return generate_failure( retu_data['msg'] )

        retu_obj[m] = retu_data['data']

    return generate_success( data=trans_struct_to_easy_dis(retu_obj) )


def generate_time_range( minutes ):
    time_end = int(time.time())
    time_start = time_end - int(minutes)*60
    return { 
        'time_start':'%ss' % time_start,
        'time_end':'%ss' % time_end,
    }

@csrf_exempt
@return_http_json
def get_cluster_cpu_info(request,namespace,minutes):
    measurements = [ ISM.M_CPU_USAGE,ISM.M_CPU_LIMIT,ISM.M_CPU_REQUEST ]
    time_range = generate_time_range( minutes )
    sql_str_dict = {}
    for m in measurements:
        sql_str_dict[m] = ISM.format_query_str( 
                                measurement=m,
                                time_start=time_range['time_start'],
                                time_end=time_range['time_end'],
                                type=ISM.T_NODE )
    return execute_clusterinfo_request( sql_str_dict )

@csrf_exempt
@return_http_json
def get_cluster_memory_info(request,namespace,minutes):
    measurements = [ ISM.M_MEMORY_USAGE,ISM.M_MEMORY_WORKINGSET,ISM.M_MEMORY_LIMIT,ISM.M_MEMORY_REQUEST ]
    time_range = generate_time_range( minutes )
    sql_str_dict = {}
    for m in measurements:
        sql_str_dict[m] = ISM.format_query_str( 
                                measurement=m,
                                time_start=time_range['time_start'],
                                time_end=time_range['time_end'],
                                type=ISM.T_NODE )
    return execute_clusterinfo_request( sql_str_dict )


@csrf_exempt
@return_http_json
def get_cluster_network_info(request,namespace,minutes):
    measurements = [ ISM.M_NETWORK_TRANSMIT,ISM.M_NETWORK_RECEIVE ]
    time_range = generate_time_range( minutes )
    sql_str_dict = {}
    for m in measurements:
        sql_str_dict[m] = ISM.format_query_str( 
                                measurement=m,
                                time_start=time_range['time_start'],
                                time_end=time_range['time_end'],
                                type=ISM.T_POD )
    return execute_clusterinfo_request( sql_str_dict )


@csrf_exempt
@return_http_json
def get_cluster_filesystem_info(request,namespace,minutes):
    measurements = [ ISM.M_FILESYSTEM_USAGE,ISM.M_FILESYSTEM_LIMIT ]
    time_range = generate_time_range( minutes )
    sql_str_dict = {}
    for m in measurements:
        sql_str_dict[m] = ISM.format_query_str( 
                                measurement=m,
                                time_start=time_range['time_start'],
                                time_end=time_range['time_end'],
                                type=ISM.T_NODE )
    return execute_clusterinfo_request( sql_str_dict )

