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
@File       : network_util.py

@Author     : hsn

@Date       : 2024/9/5 下午6:48
"""
import httpx


# Add redirects support
def request(client: httpx.Client, url: str, method: str, body: str, decode: str,
            headers: dict | None = None, *,
            allow_redirects: bool = False) -> str:
    if headers is None:
        headers = {}

    resp = client.request(method, url, content=body, headers=headers)
    match resp.status_code:
        case 200:
            return resp.content.decode(decode)
        case 301 | 302 | 303 | 307 | 308:
            if allow_redirects:
                return request(client, resp.headers['location'], method, body, decode, allow_redirects=True)
            else:
                return resp.content.decode(decode)
        case _:
            return resp.content.decode(decode)
