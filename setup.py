#!/usr/bin/python

from distutils.core import setup

setup(name="courier-pythonfilter",
      version="0.1",
      description="Python filtering architecture for the Courier MTA.",
      author="Gordon Messmer",
      author_email="gordon@dragonsdawn.net",
      url="http://www.dragonsdawn.net/~gordon/courier-patches/courier-pythonfilter/",
      scripts=['pythonfilter'],
      packages=['courier'],
      data_files=[('lib/pythonfilter', ['filters/dialback.py',
                                        'filters/ratelimit.py'])]
     )
