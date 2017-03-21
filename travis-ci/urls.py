from django.conf.urls import include, url


urlpatterns = [
    url(r'^', include('rc_django.urls')),
]
