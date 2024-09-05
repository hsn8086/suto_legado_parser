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
@File       : book_soure_parser.py

@Author     : hsn

@Date       : 2024/9/4 下午6:20
"""
import json
from typing import Generator
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from suto_legado_parser.utils.network import request
from suto_legado_parser.rule.compile import rule_compile


class BookInfo(BaseModel):
    name: str = "Unknown"
    author: str = "Unknown"
    word_count: int = 0
    book_url: str = "https://example.com"
    cover_url: str = "https://example.com"
    intro: str = "Nothing"
    kind: str = "Unknown"
    last_chapter: str = "Unknown"


class Parser:
    """
    The parser of the book source.
    """

    def __init__(self, source_json: dict):
        self.j = source_json
        raw_burl: str = self.j.get("bookSourceUrl")
        if point := raw_burl.find("#") != -1:
            raw_burl = raw_burl[:point]
        self.base_url: str = raw_burl
        self.search_url = self.j.get("searchUrl")
        self.rule_search = self.j.get("ruleSearch")
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def search(self, title: str) -> Generator[BookInfo, None, None]:

        var = {"key": quote(title), "page": 1}  # Define the var #todo: page
        compiled_url: str = rule_compile(self.search_url, var)  # Compile the url

        # Process the options
        # example:
        #   https://example.com, {"encode": "utf-8", "method": "post", "body": "key={{key}}"}
        options = {}
        cut = compiled_url.find(",")  # Find the cut point
        if cut != -1:
            options_json: str = compiled_url[cut + 1:]  # Extract the options
            compiled_url = compiled_url[:cut]  # Cut the options

            # The function of next sentence is similar as json.loads(options_json)
            options = eval(options_json)  # Parse the options
            # Explanation:
            # The json of the options should be like this:
            #   {"encode": "utf-8", "method": "post", "body": "key={{key}}"}
            # But sometimes it may not be a json and like the dict of the python:
            #   {'encode': 'utf-8', 'method': 'post', 'body': 'key={{key}}'}
            # So we use eval to parse it

        decode = options.get("decode", 'utf-8')
        method = options.get("method", 'get')
        body = options.get("body", '')

        search_result = await request(self.client, compiled_url, method, body, decode, allow_redirects=True)

        # `rule_compile` will return a string of list in this case.
        books = json.loads(
            rule_compile(self.rule_search.get("bookList"), {"result": search_result.strip()}, allow_str_rule=False))

        for book in books:
            author = rule_compile(self.rule_search.get("author"), {"result": book}, allow_str_rule=False)
            name = rule_compile(self.rule_search.get("name"), {"result": book}, allow_str_rule=False)
            word_count = rule_compile(self.rule_search.get("wordCount"), {"result": book}, allow_str_rule=False,default="0")
            book_url = rule_compile(self.rule_search.get("bookUrl"), {"result": book})
            cover_url = rule_compile(self.rule_search.get("coverUrl"), {"result": book}, allow_str_rule=False)
            intro = rule_compile(self.rule_search.get("intro"), {"result": book}, allow_str_rule=False)
            kind = rule_compile(self.rule_search.get("kind"), {"result": book})
            last_chapter = rule_compile(self.rule_search.get("lastChapter"), {"result": book})

            yield BookInfo(name=name,
                           author=author,
                           word_count=int(''.join(filter(lambda x: x.isalnum(), word_count))),  # Extract the number
                           book_url=book_url,
                           cover_url=cover_url,
                           intro=intro,
                           kind=kind,
                           last_chapter=last_chapter)
