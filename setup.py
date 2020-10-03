# -*- coding: utf-8 -*-
"""
Created on Sat Oct  3 08:30:57 2020

@author: nanashi
"""

from distutils.core import setup, Extension

ss_cotton_lz00 = Extension('ss_cotton_2_translation_tools.ss_cotton_lz00',
                    sources = ['ss_cotton_2_translation_tools/ss_cotton_lz00.c'])

setup (name = 'ss_cotton_2_translation_tools',
       version = '0.1',
       description = 'Sega Saturn Cotton 2 translation tools',
       packages=['ss_cotton_2_translation_tools'],
       ext_modules = [ss_cotton_lz00])