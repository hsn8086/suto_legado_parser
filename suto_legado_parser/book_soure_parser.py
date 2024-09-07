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
import logging
from typing import Generator
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from suto_legado_parser.rule.compile import rule_compile
from suto_legado_parser.utils.network import request


class BookInfo(BaseModel):
    name: str = "Unknown"
    author: str = "Unknown"
    word_count: int = 0
    book_url: str = "https://example.com"
    cover_url: str = "https://example.com"
    intro: str = "Nothing"
    kind: str = "Unknown"
    last_chapter: str = "Unknown"


class BookDetail(BookInfo):
    toc_url: str = "https://example.com"


class ProcessedUrl(BaseModel):
    url: str
    decode: str = 'utf-8'
    method: str = 'get'
    body: str = ''
    headers: dict = {}


def url_process(url: str) -> ProcessedUrl:
    # Process the options
    # example:
    #   https://example.com, {"encode": "utf-8", "method": "post", "body": "key={{key}}"}
    options = {}
    cut = url.find(",")  # Find the cut point
    if cut != -1:
        options_json: str = url[cut + 1:]  # Extract the options
        url = url[:cut]  # Cut the options

        # The function of next sentence is similar as json.loads(options_json)
        options = eval(options_json.replace("true", "True").replace("false", "False"))  # Parse the options
        # Explanation:
        # The json of the options should be like this:
        #   {"encode": "utf-8", "method": "post", "body": "key={{key}}"}
        # But sometimes it may not be a json and like the dict of the python:
        #   {'encode': 'utf-8', 'method': 'post', 'body': 'key={{key}}'}
        # So we use eval to parse it

    decode = options.get("decode", 'utf-8')
    method = options.get("method", 'get')
    body = options.get("body", '')
    headers = options.get("headers", {})
    return ProcessedUrl(url=url, decode=decode, method=method, body=body, headers=headers)


def word_count_process(word_count: str | int) -> int:
    if isinstance(word_count, int):
        return word_count
    rep_dict = {"亿": "00000000", "万": "0000", "千": "000", "百": "00", "十": "0", "零": "0", "一": "1", "二": "2",
                "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "壹": "1", "贰": "2",
                "叁": "3", "肆": "4", "伍": "5", "陆": "6", "柒": "7", "捌": "8", "玖": "9",
                "k": "000", "m": "000000", "g": "000000000", "w": "0000", "K": "000", "M": "000000", "G": "000000000",
                "W": "0000"}

    for key, value in rep_dict.items():
        word_count = word_count.replace(key, value)
    return int(''.join(filter(lambda x: x.isalnum(), word_count)))


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
        self.rule_book_info = self.j.get("ruleBookInfo")
        self.client = httpx.AsyncClient(base_url=self.base_url)
        self.logger = logging.getLogger(self.__class__.__name__)

    async def search(self, title: str) -> Generator[BookInfo, None, None]:
        self.logger.info(f"Searching for {title}")
        var = {"_book_source": self.j,
               "key": quote(title),
               "page": 1}  # Define the var #todo: page

        compiled_url: str = rule_compile(self.search_url, var)  # Compile the url
        self.logger.debug(f"Compiled url: {compiled_url}")

        p_url = url_process(compiled_url)
        self.logger.debug(f"Processed url: {p_url}")

        search_result = await request(self.client, **(p_url.dict()), allow_redirects=True)
        self.logger.debug(f"Search result: {search_result}")
        # `rule_compile` will return a string of list in this case.
        books = json.loads(
            rule_compile(self.rule_search.get("bookList"), {"_book_source": self.j, "result": search_result.strip()},
                         allow_str_rule=False))
        self.logger.debug(f"Books: {books}")

        for book in books:
            try:
                author = rule_compile(self.rule_search.get("author"), {"result": book}, allow_str_rule=False)
                name = rule_compile(self.rule_search.get("name"), {"result": book}, allow_str_rule=False)
                word_count = rule_compile(self.rule_search.get("wordCount"), {"result": book}, allow_str_rule=False,
                                          default="0", callback=word_count_process)
                book_url = rule_compile(self.rule_search.get("bookUrl"), {"result": book})
                cover_url = rule_compile(self.rule_search.get("coverUrl"), {"result": book}, allow_str_rule=False)
                intro = rule_compile(self.rule_search.get("intro"), {"result": book}, allow_str_rule=False,
                                     default="No description")
                kind = rule_compile(self.rule_search.get("kind"), {"result": book})
                last_chapter = rule_compile(self.rule_search.get("lastChapter"), {"result": book})
                self.logger.debug(
                    f"Book: name: {name}, author: {author}, word_count: {word_count}, book_url: {book_url}, "
                    f"cover_url: {cover_url}, intro: {intro}, kind: {kind}, last_chapter: {last_chapter}")
                yield BookInfo(name=name,
                               author=author,
                               word_count=word_count,
                               book_url=book_url,
                               cover_url=cover_url,
                               intro=intro,
                               kind=kind,
                               last_chapter=last_chapter)
            except Exception as e:
                self.logger.exception(e)
                continue

    async def get_detail(self, book_url: str):
        var = {"_book_source": self.j}
        self.logger.info(f"Getting detail of {book_url}")

        p_url = url_process(book_url)
        self.logger.debug(f"Processed url: {p_url}")

        raw_content = await request(self.client, **(p_url.dict()), allow_redirects=True)
        self.logger.debug(f"Raw content: {raw_content}")

        init = rule_compile(self.rule_book_info.get("init"), {**var, "result": raw_content}, allow_str_rule=False,
                            default=raw_content)
        self.logger.debug(f"Init: {init}")

        name = rule_compile(self.rule_book_info.get("name"), {**var, "result": init})
        author = rule_compile(self.rule_book_info.get("author"), {**var, "result": init})
        cover_url = rule_compile(self.rule_book_info.get("coverUrl"), {**var, "result": init})
        intro = rule_compile(self.rule_book_info.get("intro"), {**var, "result": init})
        kind = rule_compile(self.rule_book_info.get("kind"), {**var, "result": init})
        last_chapter = rule_compile(self.rule_book_info.get("lastChapter"), {**var, "result": init})
        toc_url = rule_compile(self.rule_book_info.get("tocUrl"), {**var, "result": init})
        word_count = rule_compile(self.rule_book_info.get("wordCount"), {**var, "result": init}, default="0",
                                  callback=word_count_process)
        return BookDetail(name=name,
                          author=author,
                          word_count=word_count,
                          book_url=book_url,
                          cover_url=cover_url,
                          intro=intro,
                          kind=kind,
                          last_chapter=last_chapter,
                          toc_url=toc_url)

    async def get_book(self, book_url: str):
        self.logger.debug((await self.client.get(book_url)).content)
