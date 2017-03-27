from django.dispatch import Signal
from django.utils import timezone
try:
    from status_app.dispatch import dispatch
    from status_app.models import RawEvent
except ImportError:
    pass


rest_request = Signal(providing_args=[
    'url', 'request_time', 'hostname', 'service_name'])


def rest_request_receiver(sender, **kwargs):
    dispatch('%s_request_interval' % kwargs.get('service_name'),
             RawEvent.INTERVAL,
             timezone.now(),
             kwargs.get('request_time'),
             kwargs.get('url'),
             kwargs.get('hostname'))


def get_signal():
    return rest_request
