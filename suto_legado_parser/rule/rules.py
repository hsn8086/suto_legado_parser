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
@File       : rules.py

@Author     : hsn

@Date       : 2024/9/5 下午7:12
"""
import copy
import json
import re
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Any

import STPyV8
import jsonpath_ng
from bs4 import BeautifulSoup, element
from lxml import etree

from ..utils.js import JsUtil


class Rule(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self, text: str):
        ...

    @abstractmethod
    def compile(self, var: dict):
        ...

    @abstractmethod
    def get_text(self) -> str:
        ...

    def __repr__(self):
        rt = self.__class__.__name__ + "("
        for k, v in self.__dict__.items():
            rt += f"{k}={v},"
        rt += ")"
        return rt


# class JSoupRule(Rule):
#     def __init__(self, text: str):
#         self.text = text
#
#     def compile(self, var: dict):
#         tl = self.text.split("@")
#         tl = list(filter(lambda x: x, tl))
#         soup = BeautifulSoup(var["result"], "html.parser")
#         rt: BeautifulSoup = soup
#         if len(tl) >= 1:
#             _type, selector = tl[0].split(".", 1)
#             selector: str
#
#             # If the selector is a tag with no.
#             temp_sel = selector.rsplit(".", 1)
#             no = None
#             if len(temp_sel) >= 2 and temp_sel[-1].isdigit():
#                 selector = ''.join(temp_sel[:-1])
#                 no = int(temp_sel[-1])  # Get the no of the tag.
#
#             if _type == "class":
#                 rt: element.ResultSet = soup.find_all(class_=selector)
#             elif _type == "id":
#                 rt: element.ResultSet = soup.find_all(id=selector)
#             elif _type == "tag":
#                 rt: element.ResultSet = soup.select(selector.replace(".", ">"))
#             elif _type == "text":
#                 rt: str = soup.get_text()
#             elif _type == "children":
#                 rt: Iterable = soup.children  # todo: Uncompleted
#                 raise NotImplementedError("The children selector is not implemented.")
#             else:
#                 rt: element.ResultSet = soup.select(selector)
#
#             if no is not None:
#                 rt: element.Tag = rt[no]
#
#         rt: element.Tag | element.ResultSet | BeautifulSoup | str | Iterable
#
#         if len(tl) >= 2:
#             rt = rt.get(tl[1]) or getattr(rt, tl[1])
#
#         if isinstance(rt, element.ResultSet):
#             if len(rt) == 1:  # If there is only one tag in the ResultSet, return the tag.
#                 rt = rt[0]
#             if len(rt) >= 2:
#                 rt: str = json.dumps([str(i) for i in rt], ensure_ascii=False)
#         elif isinstance(rt, element.Tag):
#             rt: str = str(rt)
#
#         return rt
class JSoupRule(Rule):
    def __init__(self, text: str):
        self.text = text

    def get_text(self):
        return self.text

    def compile(self, var: dict):
        tl = self.text.split("@")
        tl = list(filter(lambda x: x, tl))
        soup = BeautifulSoup(var["result"], "html.parser")
        rt: BeautifulSoup = soup
        for i in tl:
            try:
                _type, selector = i.split(".", 1)
            except ValueError:
                _type = i
                selector = ""
            selector: str

            # If the selector is a tag with no.
            temp_sel = selector.rsplit(".", 1)
            no = None
            if len(temp_sel) >= 2 and temp_sel[-1].isdigit():
                selector = ''.join(temp_sel[:-1])
                no = int(temp_sel[-1])  # Get the no of the tag.

            if _type == "class":
                rt: element.ResultSet = rt.find_all(class_=selector)
            elif _type == "id":
                rt: element.ResultSet = rt.find_all(id=selector)
            elif _type == "tag":
                rt: element.ResultSet = rt.select(selector.replace(".", ">"))
            elif _type == "text":
                rt: str = rt.get_text()
            elif _type == "children":
                rt: Iterable = rt.children  # todo: Uncompleted
                raise NotImplementedError("The children selector is not implemented.")
            else:
                rt = rt.get(_type)
            if rt is None:
                raise

            if no is not None:
                rt: element.Tag = rt[no]

        rt: element.Tag | element.ResultSet | str | Iterable

        if isinstance(rt, element.ResultSet):
            if len(rt) == 1:  # If there is only one tag in the ResultSet, return the tag.
                rt = rt[0]
            if len(rt) >= 2:
                rt: str = json.dumps([str(i) for i in rt], ensure_ascii=False)
        elif isinstance(rt, element.Tag):
            rt: str = str(rt)

        return rt


@dataclass
class CssRule:
    text: str


class InnerRule(Rule):
    def __init__(self, text: str):
        self.text = text

    def get_text(self):
        return self.text

    def compile(self, var: dict):
        if self.text.startswith("$.") or self.text.startswith("$["):
            return JsonPath(self.text).compile(copy.deepcopy(var))  # todo: Uncompleted
        else:
            return str(JsRule(self.text).compile(copy.deepcopy(var)))


class XPathRule(Rule):
    def __init__(self, text: str):
        self.text = text

    def get_text(self):
        return self.text

    def compile(self, var: dict):
        html = etree.HTML(var["result"])
        rt = html.xpath("//" + self.text)

        rt_list = [str(i) for i in rt]

        if len(rt_list) == 1:
            rt = rt_list[0]
        if len(rt_list) >= 2:
            rt = json.dumps(rt_list, ensure_ascii=False)
        return rt


class JsRule(Rule):
    def __init__(self, text: str):
        self.text = text

    def get_text(self):
        return self.text

    def compile(self, var: dict):
        jsu = JsUtil(var)
        for k, v in var.items():
            setattr(jsu, k, v)

        with STPyV8.JSContext(jsu) as ctxt:
            for k in var:
                ctxt.eval(f"let {k} = this.{k};")

            ctxt.eval(f"let java = this;")
            if True:
                for i, line in enumerate(self.text.splitlines()):
                    print(f"{i + 1}\t| {line}")
                print(var)
            return ctxt.eval(self.text.strip())


class RegexRule(Rule):
    def __init__(self, *args):
        match len(args):
            case 1:
                raise NotImplementedError
            case 2:
                self.pattern = args[0]
                self.repl = args[1]
            case _:
                raise ValueError("Invalid RegexRule")

    def get_text(self):
        return f"##{self.pattern}##{self.repl}"

    def compile(self, var: dict):
        return re.sub(self.pattern, self.repl, var["result"])


class JsonPath(Rule):
    def __init__(self, text: str):
        self.json_path: str = ""
        self.rule: list[Rule] = []

        tl = text.split("##")
        match len(tl):
            case 1:
                self.json_path = text
            case 2:
                self.json_path = tl[0]
                self.rule = [RegexRule(tl[1], "")]
            case 3:
                self.json_path = tl[0]
                self.rule = [RegexRule(tl[1], tl[2])]
            case _:
                raise ValueError("Invalid JsonPath")

    def get_text(self):
        return self.json_path + "".join([i.get_text() for i in self.rule])

    def compile(self, var: dict):
        if isinstance(var["result"], str):
            j = json.loads(var["result"])
        else:
            j = var["result"]
        rt_dict = [match.value for match in jsonpath_ng.parse(f"$.{self.json_path}").find(j)]
        if len(rt_dict) == 0:
            return ""
        elif len(rt_dict) == 1:
            rt = rt_dict[0]
        else:
            rt = json.dumps(rt_dict, ensure_ascii=False)
        for i in self.rule:
            rt = i.compile({**var, "result": rt})

        return rt


class StrRule(Rule):
    def __init__(self, text: str = ''):
        self.rules: list[str | Any] = [text] if text else []

    def get_text(self):
        rt = ""
        for rule in self.rules:
            if isinstance(rule, str):
                rt += rule
            else:
                rt += rule.get_text()

    def compile(self, var: dict):
        rt = ""
        for i in self.rules:
            if isinstance(i, str):
                rt += i
            elif isinstance(i, InnerRule):
                rt += i.compile(var)
        return rt


class AndRule(Rule):
    def __init__(self, rules: list[Rule]):
        self.rules = rules

    def get_text(self):
        return '&&'.join([i.get_text() for i in self.rules])

    def compile(self, var: dict):
        rt = ""
        for i in self.rules:
            print(i.compile(var))
            rt += i.compile(var)
        return rt
