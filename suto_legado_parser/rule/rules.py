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
import logging
import re
from abc import ABCMeta, abstractmethod
from typing import Any, Generator

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
def flatten(list_: list):
    for el in list_:
        if isinstance(el, list):
            yield from flatten(el)
        else:
            yield el


class JSoupRule(Rule):
    def __init__(self, text: str):
        self.text: str = text

    def get_text(self):
        return self.text

    def compile(self, var: dict) -> str:
        # Check RegEx
        regex_rule: RegexRule | None = None
        if "##" in self.text:
            self.text, regex = self.text.split("##", 1)
            regex_rule = RegexRule(regex)

        soup: BeautifulSoup = BeautifulSoup(var["result"], "html.parser")
        results: list[BeautifulSoup | element.Tag | str] = [soup]

        split_rule: Generator[str, None, None] = filter(lambda x: x, self.text.split("@"))
        for rule in split_rule:
            results = list(self._apply_rule_multi(results, rule))

        assert isinstance(results, list)
        result = self._process_result_list(results)

        if regex_rule is not None:
            result = regex_rule.compile({**var, "result": result})

        return result

    def _apply_rule_multi(self, rt: list[BeautifulSoup | element.Tag], rule: str) -> Generator:
        for i in rt:
            yield from self._apply_rule(i, rule)

    def _get_tag_from_text(self, rt: BeautifulSoup | element.Tag, text: str) -> element.Tag | None:
        for i in rt.find_all():
            i: element.Tag
            for child in i.childGenerator():
                if isinstance(child, element.Tag):
                    if res := self._get_tag_from_text(child, text):
                        return res

            if i.get_text() == text:
                return i
        else:
            return None

    def _apply_rule(self, rt: BeautifulSoup | element.Tag, rule: str) -> list[BeautifulSoup | element.Tag | str]:
        assert isinstance(rt, (BeautifulSoup, element.Tag))
        no: int | None = None
        if rule.startswith("[") and rule.endswith("]"):
            _type, selector = "css", rule
        else:
            _type, selector = self._parse_rule(rule)
            _type = _type or "class"
            selector, no = self._extract_no(selector)

        match _type:
            case "class":
                rt = rt.select(f".{selector.strip()}")
            case "id":
                rt = rt.select(f"[id={selector}]")
            case "tag":
                rt = self._select_tag(rt, selector)
            case "text" | "textNodes":
                if selector:
                    rt = self._get_tag_from_text(rt, selector)
                    if rt is None:
                        raise ValueError("No result found.")
                else:
                    rt = rt.get_text()
            case "children":
                raise NotImplementedError("The children selector is not implemented.")
            case "css":
                rt = rt.select(selector.strip())
            case _:
                rt = rt.get(_type) or rt.select(_type)

        if rt is None:
            raise ValueError("No result found.")
        # if isinstance(rt, list) and len(rt) == 1 and no is None:
        #     rt = rt[0]

        if no is not None:
            rt = rt[no]

        return self._2list(rt)

    @staticmethod
    def _2list(rt) -> list:
        if isinstance(rt, list):
            return rt
        return [rt]

    @staticmethod
    def _parse_rule(rule: str) -> tuple[str, str]:
        parts = rule.split(".", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        elif len(parts) == 1 and ">" in parts[0]:
            return "tag", parts[0]
        return parts[0], ""

    @staticmethod
    def _extract_no(selector: str) -> tuple[str, int | None]:
        temp_sel = selector.rsplit(".", 1)
        if len(temp_sel) >= 2 and temp_sel[-1].isdigit():
            return ''.join(temp_sel[:-1]), int(temp_sel[-1])
        return selector, None

    @staticmethod
    def _select_tag(rt: element.Tag | BeautifulSoup, selector: str) -> list:
        for i in flatten([rt]):
            return i.select(selector.replace(".", " "))

    @staticmethod
    def _process_result_list(rt: list) -> str:
        assert len(rt) > 0
        match len(rt):
            case 1:
                if isinstance(rt[0], element.Tag):
                    return str(rt[0])
                return rt[0]
            case _:
                return json.dumps([str(i) for i in rt], ensure_ascii=False)


# class JSoupRule(Rule):
#     def __init__(self, text: str):
#         self.text = text
#
#     def get_text(self):
#         return self.text
#
#     def compile(self, var: dict) -> str:
#         # Check RegEx
#         regex_rule = None
#         if self.text.find("##") != -1:
#             self.text, regex = self.text.split("##", 1)
#             regex_rule = RegexRule(regex)
#
#         spilt_rule = self.text.split("@")
#         spilt_rule = list(filter(lambda x: x, spilt_rule))
#         soup = BeautifulSoup(var["result"], "html.parser")
#         rt: BeautifulSoup = soup
#         for i in spilt_rule:
#             no = None
#             if i.startswith("[") and i.endswith("]"):
#                 _type = "css"
#                 selector = i
#             else:
#                 try:
#                     _type, selector = i.split(".", 1)
#                 except ValueError:
#                     _type = i
#                     selector = ""
#                 selector: str
#
#                 # If the selector is a tag with no.
#                 temp_sel = selector.rsplit(".", 1)
#
#                 if len(temp_sel) >= 2 and temp_sel[-1].isdigit():
#                     selector = ''.join(temp_sel[:-1])
#                     no = int(temp_sel[-1])  # Get the no of the tag.
#             match _type:
#                 case "class":
#                     rt: element.ResultSet = rt.find_all(class_=selector.strip().replace(" ","."))
#                 case "id":
#                     rt: element.ResultSet = rt.find_all(id=selector)
#                 case "tag":
#                     if isinstance(rt, list):
#                         rt_list = []
#                         for j in rt:
#                             rt_list.extend(j.select(selector.replace(".", ">")))
#                         rt: list = rt_list
#                     else:
#                         rt: element.ResultSet = rt.select(selector.replace(".", ">"))
#                 case "text":
#                     rt: str = rt.get_text()
#                 case "children":
#                     rt: Iterable = rt.children  # todo: Uncompleted
#                     raise NotImplementedError("The children selector is not implemented.")
#                 case "css":
#                     rt: element.ResultSet = rt.select(selector.strip())
#                 case _:
#                     rt = rt.get(_type)
#
#             if rt is None:
#                 raise
#             if isinstance(rt, list):
#                 if len(rt) == 1 and no is None:  # If there is only one tag in the ResultSet, return the tag.
#                     rt = rt[0]
#             if no is not None:
#                 rt: element.Tag = rt[no]
#
#         rt: element.Tag | list | str | Iterable
#
#         if isinstance(rt, list):
#             if len(rt) == 1:  # If there is only one tag in the ResultSet, return the tag.
#                 rt = rt[0]
#             if len(rt) >= 2:
#                 rt: str = json.dumps([str(i) for i in rt], ensure_ascii=False)
#         elif isinstance(rt, element.Tag):
#             rt: str = str(rt)
#         if regex_rule:
#             rt: str = regex_rule.compile({**var, "result": rt})
#         return rt
# class JSoupRule(Rule):
#     def __init__(self, text: str):
#         self.text = text
#
#     def get_text(self):
#         return self.text
#
#     def compile(self, var: dict) -> str:
#         # Check RegEx
#         regex_rule = None
#         if self.text.find("##") != -1:
#             self.text, regex = self.text.split("##", 1)
#             regex_rule = RegexRule(regex)
#
#         spilt_rule = self.text.split("@")
#         spilt_rule = list(filter(lambda x: x, spilt_rule))
#
#         soup = BeautifulSoup(var["result"], "html.parser")
#         rt: BeautifulSoup = soup
#         print(spilt_rule)
#         for i in spilt_rule:
#             print(i)
#             rt=rt.select("."+i)
#             print("rt",rt)
#         if isinstance(rt, list):
#             if len(rt) == 1:  # If there is only one tag in the ResultSet, return the tag.
#                 rt = rt[0]
#             if len(rt) >= 2:
#                 rt: str = json.dumps([str(i) for i in rt], ensure_ascii=False)
#         elif isinstance(rt, element.Tag):
#             rt: str = str(rt)
#         if regex_rule:
#             rt: str = regex_rule.compile({**var, "result": rt})
#         return rt
class CssRule(Rule):
    def __init__(self, text: str):
        self.text = text

    def get_text(self) -> str:
        return self.text

    def compile(self, var: dict):
        soup = BeautifulSoup(var["result"], "html.parser")
        rt: element.ResultSet = soup.select(self.text)
        rt_list = [str(i) for i in rt]
        if len(rt_list) == 0:
            raise ValueError("No result found.")
        if len(rt_list) == 1:
            rt = str(rt_list[0])
        if len(rt_list) >= 2:
            rt = json.dumps(rt_list, ensure_ascii=False)
        return rt


class InnerRule(Rule):
    def __init__(self, text: str):
        self.text = text

    def get_text(self):
        return self.text

    def compile(self, var: dict):
        if self.text.startswith("$.") or self.text.startswith("$["):
            return str(JsonPath(self.text).compile(copy.deepcopy(var)))  # todo: Uncompleted
        else:
            return str(JsRule(self.text).compile(copy.deepcopy(var)))


class XPathRule(Rule):
    def __init__(self, text: str):
        self.text = text

    def get_text(self):
        return self.text

    def compile(self, var: dict):
        regex_rule = None
        if self.text.find("##") != -1:
            self.text, regex = self.text.split("##", 1)
            regex_rule = RegexRule(regex)
        html = etree.HTML(var["result"])
        rt = html.xpath("//" + self.text)

        rt_list = [str(i) for i in rt]
        if len(rt_list) == 0:
            raise ValueError("No result found.")
        if len(rt_list) == 1:
            rt = str(rt_list[0])
        if len(rt_list) >= 2:
            rt = json.dumps(rt_list, ensure_ascii=False)
        if regex_rule:
            rt = regex_rule.compile({**var, "result": rt})
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
                if not k.startswith("_"):
                    ctxt.eval(f"let {k} = this.{k};")
            ctxt.eval("let source = this.source;")
            ctxt.eval("let java = this;")
            if True:
                logger = logging.getLogger("JsRule")
                for i, line in enumerate(self.text.splitlines()):
                    logger.debug(f"{i + 1}\t| {line}")
                logger.debug(var)
            return ctxt.eval(self.text.strip())


class RegexRule(Rule):
    def __init__(self, *args):
        match len(args):
            case 1:
                if args[0].find("##") != -1:
                    self.pattern, self.repl = args[0].split("##", 1)
                else:
                    self.pattern = args[0]
                    self.repl = ""
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
        if not self.json_path.startswith("$."):
            self.json_path = "$." + self.json_path

    def get_text(self):
        return self.json_path + "".join([i.get_text() for i in self.rule])

    def compile(self, var: dict):
        if isinstance(var["result"], str):
            j = json.loads(var["result"])
        else:
            j = var["result"]
        rt_dict = [match.value for match in jsonpath_ng.parse(self.json_path).find(j)]
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
    def __init__(self, *rules: Rule):
        self.rules = rules

    def get_text(self):
        return '&&'.join([i.get_text() for i in self.rules])

    def compile(self, var: dict):
        rt = ""
        for i in self.rules:
            rt += i.compile(var)
        return rt


class OrRule(Rule):
    def __init__(self, *rules: Rule):
        self.rules = rules

    def get_text(self):
        return '||'.join([i.get_text() for i in self.rules])

    def compile(self, var: dict):
        logger = logging.getLogger("OrRule")
        for rule in self.rules:
            try:
                logger.debug(f"Trying rule: {rule}")
                if rt := rule.compile(var):
                    return rt
            except Exception as e:
                logger.debug(e)
                pass
        raise ValueError("No rule matched.")
