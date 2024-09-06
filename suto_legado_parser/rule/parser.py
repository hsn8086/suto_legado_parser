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
@File       : rule.py

@Author     : hsn

@Date       : 2024/9/4 下午5:14
"""
import logging
from typing import Iterable, Generator, Any, Callable

from pydantic import BaseModel

from .rules import Rule, JSoupRule, CssRule, InnerRule, XPathRule, JsRule, RegexRule, JsonPath, StrRule, AndRule, OrRule


class Locker:
    def __init__(self):
        self.locker: str = ''
        self.count: int = 0

    def set_locker(self, name: str):
        self.locker: str = name
        self.count += 1

    def release_locker(self):
        assert self.count > 0
        self.count -= 1
        if self.count == 0:
            self.locker = ''

    def is_locked(self, except_name: str | None = None):
        return self.locker and except_name != self.locker


class ESStrut(BaseModel):
    class_: Callable
    start: str | list | set
    end: str | list | set | None
    keep_end: bool = False


class EncompassingSplitter:
    def __init__(self, rule: str):
        self.rule = rule
        self.locker = Locker()
        self.struts: list[ESStrut] = []

    def add_strut(self, _class: object, start: str | list | set, end: str | list | set | None, *, keep_end=False):
        '''
        add a strut to the rule.
        :param _class: The class of the rule.
        :param start: The start of the struts.
        :param end: The end of the struts. If it is None, the strut will end when the text ends.
        :param keep_end: Keep the end of the struts or not.
        :return:
        '''
        # Transform the start and end to list.
        if (not isinstance(start, Iterable)) or isinstance(start, str):
            start = [start]
        if (not isinstance(end, Iterable)) or isinstance(end, str):
            end = [end]

        self.struts.append(
            ESStrut(
                class_=_class,
                start=start,
                end=end,
                keep_end=keep_end
            )
        )

    def split(
            self,
            text: str
    ) -> (Generator[
        tuple[str, None] | tuple[str, Any],
        Any,
        None
    ]):
        """
        Split the text by the struts.
        example:
            If the strut is InnerRule and start is "{{" and the end is "}}", the text is "{{hello}}world{{world}}".
            When the text is "{{",lock.
            And when the text is "}}", release the lock and return the text between "{{" and "}}" by InnerRule.
        :param text:
        :return:
        """
        for ess in self.struts:  # Get the strut.
            _class = ess.class_
            start = ess.start
            end = ess.end
            keep_end = ess.keep_end

            # If the strut is not locked.
            if self.locker.is_locked(_class.__name__):
                continue

            # Process the start of the strut.
            if text in start:
                # If the text is the start of the strut, lock the strut.
                self.locker.set_locker(_class.__name__)
                yield '', None
                text = ''
                continue

            # Process the end of the strut.
            for e in end:
                if e is None:  # None means the strut will end when the text ends.
                    continue
                if text.endswith(e):  # If the text is the end of the strut.
                    if _class.__name__ == self.locker.locker:  # If the strut is locked.
                        self.locker.release_locker()  # Release the lock.
                        if keep_end:
                            yield text[-len(e):], _class(text[:-len(e)])
                            text = text[-len(e):]
                        else:
                            yield '', _class(text[:-len(e)])
                            text = ''
                        continue
            yield text, None

    def end(self, text: str):
        for ess in self.struts:
            _class = ess.class_
            if self.locker.locker and not self.locker.is_locked(_class.__name__):
                return _class(text)
        else:
            return text

def logic_rule(rule: Rule) -> Rule:
    """
    Parse the logic rule.
    :param rule: The rule.
    :return: The rule object.
    """
    if len(split_obj := rule.get_text().split("&&")) >= 2:
        return AndRule(*[rule.__class__(s) for s in split_obj])
    elif len(split_obj := rule.get_text().split("||")) >= 2:
        return OrRule(*[rule.__class__(s) for s in split_obj])
    else:
        return rule
def _split_rule_raw(rule: str) -> Generator[str, Any, None]:
    es = EncompassingSplitter(rule)
    es.add_strut(JsonPath, '$.', {'@get:', '@put:', '@js:', '@css:', '@xpath', '<js>', '<css>', '<xpath>'},
                 keep_end=True)
    es.add_strut(JsonPath, '$[', {'@get:', '@put:', '@js:', '@css:', '@xpath', '<js>', '<css>', '<xpath>'},
                 keep_end=True)
    es.add_strut(RegexRule, [f'${num}' for num in range(10)], {'@js:', '@css:', '@xpath', '<js>', '<css>', '<xpath>'},
                 keep_end=True)
    es.add_strut(JsRule, '<js>', '</js>')
    es.add_strut(CssRule, '<css>', '</css>')
    es.add_strut(InnerRule, '{{', '}}')
    es.add_strut(JsRule, '@js:', None)
    es.add_strut(CssRule, '@css:', None)
    es.add_strut(XPathRule, ['@xpath:', '@Xpath:', '@XPath:', '@XPATH:'], None)
    es.add_strut(XPathRule, '//', None)

    control_char = {'<', '@', '{'}

    rt_str = ''
    for i, char in enumerate(rule):
        rt_str += char

        for rt_str, obj in es.split(rt_str):
            obj: Rule
            if obj:
                if isinstance(obj, Rule):
                    yield logic_rule(obj)
                else:
                    yield obj
                continue

        if char in control_char and rule[i - 1] not in control_char and not es.locker.is_locked():
            if rt := rt_str[:-1]:
                yield rt
            rt_str = char
            continue

    obj = es.end(rt_str)
    if isinstance(obj, Rule):
        yield logic_rule(obj)
    else:
        yield obj


def is_alpha(text: str):
    for s in text:
        if not (0 <= ord(s) <= 126):
            return False
    return True


def _compile(temp_str: StrRule):  # todo
    for rule in temp_str.rules:
        if not isinstance(rule, str):
            return temp_str
    else:
        from suto_legado_parser.utils.text import classify_string
        type_ = classify_string(''.join(temp_str.rules))
        match type_:
            case "jsonpath":
                return JsonPath(''.join(temp_str.rules))
            case "jsoup":
                return JSoupRule(''.join(temp_str.rules))
            case "xpath":
                return XPathRule(''.join(temp_str.rules))
            case "string":
                return temp_str
    return temp_str


def split_rule(rules: str) -> Generator[Rule, Any, None]:
    """
    Split the rule.
    :param rules:
    :return:
    """
    # Because the _split_rule_raw function will return the InnerRule object,
    # so the temp_str is used to store the string rules.
    temp_str = StrRule()
    for rule in _split_rule_raw(rules):  # Split the rule.
        if isinstance(rule, str) or isinstance(rule, InnerRule):
            temp_str.rules.append(rule)
        else:
            if temp_str.rules:
                yield _compile(temp_str)
            temp_str = StrRule()  # Stop the temp_str.
            yield rule

    if temp_str.rules:  # If the temp_str is not empty, compile it.
        if temp_str.rules:
            yield _compile(temp_str)
