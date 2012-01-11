from distutils.core import setup, Extension

extension = Extension('stringutils', sources = ['stringutils.cpp'])

setup (name = 'stringutils',
       version = '0.1',
       description = 'stringutils package',
       ext_modules = [extension])