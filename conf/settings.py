
INSTALLED_APPS += [
    'userservice',
    'rc_django'
]

MIDDLEWARE += [
    'userservice.user.UserServiceMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
    },
]
