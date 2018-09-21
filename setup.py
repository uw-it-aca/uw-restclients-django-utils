import os
from setuptools import setup

README = """
See the README on `GitHub
<https://github.com/uw-it-aca/uw-restclients-django-utils>`_.
"""

# The VERSION file is created by travis-ci, based on the tag name
version_path = 'rc_django/VERSION'
VERSION = open(os.path.join(os.path.dirname(__file__), version_path)).read()
VERSION = VERSION.replace("\n", "")

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

url = "https://github.com/uw-it-aca/uw-restclients-django-utils"
setup(
    name='UW-RestClients-Django-Utils',
    version=VERSION,
    packages=['rc_django'],
    author="UW-IT AXDD",
    author_email="aca-it@uw.edu",
    include_package_data=True,
    install_requires=[
        'Django>2.1,<3.0',
        'UW-RestClients-Core>1.0,<2.0',
        'django-userservice>3.1,<4.0',
        'python-binary-memcached',
        'python-dateutil',
    ],
    license='Apache License, Version 2.0',
    description=('UW-RestClients-Django-Utils'),
    long_description=README,
    url=url,
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
    ],
)
