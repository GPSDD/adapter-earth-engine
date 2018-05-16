from adapterearthengine.utils.files import BASE_DIR

SETTINGS = {
    'logging': {
        'level': 'DEBUG'
    },
    'service': {
        'name': 'Earth Engine Adapter',
        'uri': 'http://mymachine:5700',
        'port': 5700
    },
    'gee': {
        'service_account': 'api-highways@gpsdd-198018.iam.gserviceaccount.com',
        'privatekey_file': BASE_DIR + '/privatekey.pem'
    }
}
