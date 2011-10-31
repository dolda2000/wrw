#!/usr/bin/python

from distutils.core import setup, Extension

setup(name = "wrw",
      version = "0.1",
      description = "Simple WSGI request wrapper library",
      author = "Fredrik Tolf",
      author_email = "fredrik@dolda2000.com",
      packages = ["wrw"],
      package_data = {"wrw": ["makolib/*.mako"]},
      license = "GPL-3")
