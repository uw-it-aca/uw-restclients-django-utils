from django.conf import settings

enable_logging = getattr(settings, 'CACHE_ENABLE_LOGGING', None)


def log_err(logger, msg):
    if enable_logging:
        logger.error(msg)
