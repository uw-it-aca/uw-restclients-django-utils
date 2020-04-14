from django.conf import settings

enable_logging = getattr(settings, 'ENABLE_MEMCACHE_LOGGING', None)


def log_err(logger, msg):
    if enable_logging:
        logger.error(msg)


def log_info(logger, msg):
    if enable_logging:
        logger.info(msg)
