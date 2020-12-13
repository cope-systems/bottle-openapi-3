#!/usr/bin/env python
import os
from setuptools import setup


def _read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except IOError:
        return ''


REQUIREMENTS = [l for l in _read('requirements.txt').split('\n') if l and not l.startswith('#')]
VERSION = '0.1.0'

setup(
        name='bottle-openapi-3',
        version=VERSION,
        url='https://github.com/cope-systems/bottle-openapi-3',
        download_url='https://github.com/cope-systems/bottle-openapi-3/archive/v{0}.tar.gz'.format(VERSION),
        description='OpenAPI Integration for Bottle',
        long_description=_read("README.rst"),
        author='Robert Cope',
        author_email='robert@copesystems.com',
        license='MIT',
        platforms='any',
        packages=["bottle_openapi_3"],
        package_data={"bottle_openapi_3": ["*.png", "*.html", "*.html.st", "*.css", "*.js"]},
        install_requires=REQUIREMENTS,
        tests_require=REQUIREMENTS + ["tox", "webtest"],
        classifiers=[
            'Environment :: Web Environment',
            'Environment :: Plugins',
            'Framework :: Bottle',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
            'Topic :: Software Development :: Libraries :: Python Modules'
        ],
        include_package_data=True
)
