from django.dispatch import Signal
from django.utils import timezone
try:
    from status_app.dispatch import dispatch
    from status_app.models import RawEvent
except ImportError:
    pass


rest_request_passfail = Signal(providing_args=[
    'url', 'success', 'hostname', 'service_name'])


def rest_request_passfail_receiver(sender, **kwargs):
    dispatch('%s_request_passfail' % kwargs.get('service_name'),
             RawEvent.PASS_FAIL,
             timezone.now(),
             kwargs.get('success', False),
             kwargs.get('url'),
             kwargs.get('hostname'))


def get_signal():
    return rest_request_passfail
