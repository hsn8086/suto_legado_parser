#!/usr/bin/env python
# -*- coding: UTF-8 -*-

#  Copyright (C) 2024. Suto-Commune
#  _
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#  _
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  _
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
@File       : text.py

@Author     : hsn

@Date       : 2024/9/5 下午7:11
"""
import re


def classify_string(input_string):
    # Define regex patterns
    jsoup_pattern = re.compile(r'^[a-zA-Z0-9\.\#\[\]\=\:\@\s\^\(\)\|\u4e00-\u9fa5\\\*\-]+$')
    jsonpath_pattern = re.compile(r'^\$.*')
    xpath_pattern = re.compile(r'^//.*')

    # Check if the string matches jsoup selector pattern
    if jsoup_pattern.match(input_string):
        return 'jsoup'

    # Check if the string matches jsonpath pattern
    elif jsonpath_pattern.match(input_string):
        return 'jsonpath'

    # Check if the string matches xpath pattern
    elif xpath_pattern.match(input_string.strip()):
        return 'xpath'

    # Otherwise, classify as a regular string
    else:
        return 'string'
