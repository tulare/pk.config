# -*- encoding: utf-8 -*-

from setuptools import (
    setup,
    find_packages
)

with open('README.md') as f :
    readme = f.read()

with open('LICENSE') as f :
    license = f.read()

setup(
    name='pk.config',
    version='0.1.0',
    description='Configuration management for python project',
    long_description=readme,
    author='Tulare Regnus',
    author_email='tulare.paxgalactica@gmail.com',
    url='https://github.com/tulare/pk.config',
    license=license,
    packages=find_packages(exclude=('tests',))
)
