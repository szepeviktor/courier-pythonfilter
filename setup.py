#!/usr/bin/python

import glob
import os
import sys
from distutils.core import setup



def enum_filters():
    filters = glob.glob(os.path.join( 'filters', '*.py' ))
    argi = 0
    while argi < len(sys.argv):
        if sys.argv[argi] == '--without-filter':
            # Save the excluded filter arg, and delete both args from argv
            exclude = sys.argv[argi+1]
            del sys.argv[argi:argi+2]
            try:
                del filters[ filters.index(os.path.join('filters',exclude)) ]
            except:
                print exclude, 'not found in filters'
        else:
            argi = argi + 1
    return filters



setup(name="courier-pythonfilter",
      version="0.4",
      description="Python filtering architecture for the Courier MTA.",
      author="Gordon Messmer",
      author_email="gordon@dragonsdawn.net",
      url="http://www.dragonsdawn.net/~gordon/courier-patches/courier-pythonfilter/",
      license="GPL",
      scripts=['pythonfilter'],
      packages=['courier'],
      data_files=[('lib/pythonfilter', enum_filters())]
     )
