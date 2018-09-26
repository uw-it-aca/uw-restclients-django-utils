from django.urls import include, re_path


urlpatterns = [
    re_path(r'^', include('rc_django.urls')),
]
