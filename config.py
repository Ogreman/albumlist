import os


class Config(object):
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')
    REDIS_QUEUE_KEY = 'deferred_queue'
    APP_TOKENS = [
        token for key, token in os.environ.items()
        if key.startswith('APP_TOKEN')
    ]
    SLACK_OAUTH_TOKEN = os.environ.get('SLACK_OAUTH_TOKEN')
    LIST_NAME = os.environ.get('LIST_NAME', 'Albumlist')
    SLACK_MAX_ATTACHMENTS = int(os.environ.get('SLACK_MAX_ATTACHMENTS', 100))
    ALBUMLISTBOT_URL = os.environ.get('ALBUMLISTBOT_URL')


class ProductionConfig(Config):
    DEBUG = False
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')


class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = False
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True
    CACHE_TYPE = "simple"


class TestingConfig(Config):
    TESTING = True
