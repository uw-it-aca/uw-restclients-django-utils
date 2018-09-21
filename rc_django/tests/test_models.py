from unittest import skipIf
from django.test import TestCase
from django.conf import settings


has_rc_django = False
try:
    settings.INSTALLED_APPS.index('rc_django')
    has_rc_django = True
except Exception:
    pass


@skipIf(has_rc_django, "Need to test w/o the app_label")
class ModelTest(TestCase):

    def test_load_works(self):
        from rc_django.models import CacheEntryTimed
        self.assertTrue(True, "Didn't raise exception on import")

        from rc_django.models import CacheEntry
        self.assertTrue(True, "Didn't raise exception on import")
