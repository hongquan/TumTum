APP_ID = 'vn.hoabinh.quan.TumTum'
BRAND_NAME = APP_ID.split('.')[-1]
SHORT_NAME = BRAND_NAME.lower()
BACKEND_BASE_URL = 'https://69hes0gg2k.execute-api.ap-southeast-1.amazonaws.com/Prod/challenge/'
FPS = 6
BACKENDS = {
    'aws_demo': {
        'base_url': 'https://69hes0gg2k.execute-api.ap-southeast-1.amazonaws.com/Prod/challenge/',
        'start_url': 'start',
        'submit_frame_url': 'frames',
        'verify_url': 'verify'
    },
    'sst': {
        'base_url': 'http://localhost:8000',
        'start_url': 'start',
        'submit_frame_url': 'frames',
        'verify_url': 'verify'
    }
}
DEFAULT_SETTINGS = {
    'aws_demo': {
        'domain': '69hes0gg2k.execute-api.ap-southeast-1.amazonaws.com'
    },
    'sst': {
        'base_url': 'http://localhost:8000',
        'username': '',
        'password': '',
    }
}
