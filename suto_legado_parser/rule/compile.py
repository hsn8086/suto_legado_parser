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
@File       : rule_compile.py

@Author     : hsn

@Date       : 2024/9/4 下午6:21
"""
import logging
from typing import Callable

from .parser import split_rule
from .rules import JSoupRule, JsonPath, StrRule
from ..utils.text import classify_string


def rule_compile(rules_str: str, var: dict, *, allow_str_rule=True, default=None,
                 callback: Callable | None = None) -> str:
    """
    To process the rule.
    :param callback:
    :param rules_str: The rule string.
    :param var: The variable of the rule.
    :param allow_str_rule: If allow_str_rule is True, then compile the rule as a string.
    :param default: The default value.
    :return: The result of the rule.
    """
    # Something on first:
    #   The widely known rule of legado is consist of several rules. So this "rule" should name as "rules".
    logger = logging.getLogger("rule_compile")
    logger.debug(f"compiling rule: {rules_str}")
    if not rules_str:  # If the rules_str is None, then return the default value.
        if callback is not None:
            return callback(default)
        return default

    rules = split_rule(rules_str)
    for rule in rules:
        if isinstance(rule, StrRule):
            if allow_str_rule:  # If allow_str_rule is True, then compile the rule as a string.
                var["result"] = rule.compile(var)
            else:  # Otherwise, classify the rule and compile it.
                _type = classify_string(rule.compile(var))
                if _type == "jsonpath":
                    var["result"] = JsonPath(rule.compile(var)).compile(var)
                else:
                    var["result"] = JSoupRule(rule.compile(var)).compile(var)
        else:
            var["result"] = rule.compile(var)  # Compile the rule in the normal way.
    logger.debug(f"compiled rule: {var['result']}")
    if callback is not None:
        return callback(var["result"])
    return var["result"]  # Return the result.
