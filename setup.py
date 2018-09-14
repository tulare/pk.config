# -*- encoding: utf-8 -*-

from setuptools import setup, find_packages

# Get version without import module
exec(compile(open('pk/config/version.py').read(),
             'pk/config/version.py', 'exec'))

install_requires = [
    # List your project dependencies here.
    # For more details, see:
    # https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-dependencies
]

with open('README.md') as f :
    readme = f.read()

with open('LICENSE') as f :
    license = f.read()

setup(
    name='pk.config',
    version=__version__,
    description='Configuration management for python project',
    long_description=readme,
    author='Tulare Regnus',
    author_email='tulare.paxgalactica@gmail.com',
    url='https://github.com/tulare/pk.config',
    license=license,
    packages=find_packages(exclude=('tests',)),
    namespace_packages=['pk'],
    zip_safe=False,
    install_requires=install_requires
)
