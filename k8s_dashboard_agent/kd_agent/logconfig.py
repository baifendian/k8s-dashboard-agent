import os

cur_dir = os.path.dirname(os.path.abspath(__file__))

LOGGING = { 
    'version': 1, 
    'disable_existing_loggers': True, 
    'filters': { 
        'require_debug_false': { 
            '()': 'django.utils.log.RequireDebugFalse' 
        } 
    }, 
    'formatters': { 
        'complete': { 
            'format': '[%(levelname)s %(asctime)s @ %(process)d] (%(pathname)s/%(funcName)s:%(lineno)d) - %(message)s' 
        }, 
        'online': { 
            'format': '[%(levelname)s %(asctime)s @ %(process)d] - %(message)s' 
        } 
    }, 
    'handlers': { 
        'file': { 
            'level':'INFO', 
            'class':'logging.FileHandler', 
            'formatter': 'complete', 
            'filename' : os.path.join(cur_dir, 'logs/k8sagent.log').replace('{}','/') 
        }, 
    }, 
    'loggers': { 
        '': { 
            'handlers':['file'], 
            'propagate': False, 
            'level':'DEBUG', 
        } 
    }
}