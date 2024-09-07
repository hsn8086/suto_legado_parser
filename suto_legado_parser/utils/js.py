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
@File       : java.py

@Author     : hsn

@Date       : 2024/9/4 下午10:19
"""
import base64
import hashlib
from datetime import datetime

import STPyV8
from httpx import Client


class Source(STPyV8.JSClass):
    def __init__(self, var: dict):
        self.var = var

    def getKey(self):
        print(self.var)
        return self.var['_book_source']['bookSourceUrl']


class JsUtil(STPyV8.JSClass):
    def __init__(self, var: dict):
        self.var = var
        self.source = Source(var)

    def put(self, key: str, value: str):
        self.var[key] = value
    def get(self, *args):
        if len(args) == 1:
            return self.var[args[0]]
        elif len(args) == 2:
            raise NotImplementedError
    @staticmethod
    def ajax(urlStr: str):
        client = Client()
        rt = client.get(urlStr.strip()).text
        return rt

    @staticmethod
    def ajaxAll(urlList: list):
        client = Client()
        return [client.get(url).text for url in urlList]

    @staticmethod
    def base64Decode(_str: str):
        return base64.b64decode(_str).decode()

    @staticmethod
    def base64Encode(_str: str):
        return base64.b64encode(_str.encode()).decode()

    @staticmethod
    def md5Encode(_str: str):
        return hashlib.md5(_str.encode()).hexdigest()

    @staticmethod
    def timeFormat(_time: str | int | float):
        if isinstance(_time, int | float):
            return datetime.fromtimestamp(_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(_time, str):
            return datetime.strptime(_time, '%Y-%m-%d %H:%M:%S').timestamp()

    def getString(self, ruleStr: str, isUrl: bool = False) -> str:
        assert not isUrl  # todo:Unimplemented
        return self.var['result'][ruleStr]
