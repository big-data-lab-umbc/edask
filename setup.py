#!/usr/bin/env python

from distutils.core import setup

setup(name='edask',
      version='1.0',
      description='EDASK: Earth Data Analytic Services using the dasK / xarray toolkit',
      author='Thomas Maxwell',
      author_email='thomas.maxwell@nasa.gov',
      url='https://github.com/nasa-nccs-cds/edask.git',
      scripts=['bin/startup_scheduler', 'bin/startup_cluster.sh'],
      packages=['edask', 'edask.portal', 'edask.process', 'edask.workflow', 'edask.util', 'edask.collections', 'edask.data', 'edask.data.sources', 'edask.workflow.modules']
)
