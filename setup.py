# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in customer_portal_cv/__init__.py
from customer_portal_cv import __version__ as version

setup(
	name='customer_portal_cv',
	version=version,
	description='CapitalVia Customer Portal',
	author='CapitalVia',
	author_email='nick9822@gmail.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
