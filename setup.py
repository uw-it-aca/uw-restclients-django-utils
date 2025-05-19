import os
from setuptools import setup

README = """
See the README on `GitHub
<https://github.com/uw-it-aca/uw-restclients-django-utils>`_.
"""

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
    author="UW-IT Student & Educational Technology Services",
    author_email="aca-it@uw.edu",
    include_package_data=True,
    install_requires=[
        'django>3.2,<6',
        'uw-restclients-core',
        'django-userservice',
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
    ],
)
