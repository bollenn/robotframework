#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from robot.errors import DataError, VariableError
from robot.output import librarylogger as logger
from robot.utils import (escape, is_list_like, is_sequence, is_subscriptable,
                         type_name, unescape, unic)

from .search import search_variable, VariableMatch


class VariableReplacer(object):

    def __init__(self, variables):
        self._variables = variables

    def replace_list(self, items, replace_until=None, ignore_errors=False):
        """Replaces variables from a list of items.

        If an item in a list is a @{list} variable its value is returned.
        Possible variables from other items are replaced using 'replace_scalar'.
        Result is always a list.

        'replace_until' can be used to limit replacing arguments to certain
        index from the beginning. Used with Run Keyword variants that only
        want to resolve some of the arguments in the beginning and pass others
        to called keywords unmodified.
        """
        items = list(items or [])
        if replace_until is not None:
            return self._replace_list_until(items, replace_until, ignore_errors)
        return list(self._replace_list(items, ignore_errors))

    def _replace_list_until(self, items, replace_until, ignore_errors):
        # @{list} variables can contain more or less arguments than needed.
        # Therefore we need to go through items one by one, and escape possible
        # extra items we got.
        replaced = []
        while len(replaced) < replace_until and items:
            replaced.extend(self._replace_list([items.pop(0)], ignore_errors))
        if len(replaced) > replace_until:
            replaced[replace_until:] = [escape(item)
                                        for item in replaced[replace_until:]]
        return replaced + items

    def _replace_list(self, items, ignore_errors):
        for item in items:
            for value in self._replace_list_item(item, ignore_errors):
                yield value

    def _replace_list_item(self, item, ignore_errors):
        match = search_variable(item, ignore_errors=ignore_errors)
        if not match:
            return [unescape(match.string)]
        value = self.replace_scalar(match, ignore_errors)
        if match.is_list_variable and is_list_like(value):
            return value
        return [value]

    def replace_scalar(self, item, ignore_errors=False):
        """Replaces variables from a scalar item.

        If the item is not a string it is returned as is. If it is a variable,
        its value is returned. Otherwise possible variables are replaced with
        'replace_string'. Result may be any object.
        """
        match = self._search_variable(item, ignore_errors=ignore_errors)
        if not match:
            return unescape(match.string)
        return self._replace_scalar(match, ignore_errors)

    def _search_variable(self, item, ignore_errors):
        if isinstance(item, VariableMatch):
            return item
        return search_variable(item, ignore_errors=ignore_errors)

    def _replace_scalar(self, match, ignore_errors=False):
        if not match.is_variable:
            return self.replace_string(match, ignore_errors=ignore_errors)
        return self._get_variable_value(match, ignore_errors)

    def replace_string(self, item, custom_unescaper=None, ignore_errors=False):
        """Replaces variables from a string. Result is always a string.

        Input can also be an already found VariableMatch.
        """
        unescaper = custom_unescaper or unescape
        match = self._search_variable(item, ignore_errors=ignore_errors)
        if not match:
            return unic(unescaper(match.string))
        return self._replace_string(match, unescaper, ignore_errors)

    def _replace_string(self, match, unescaper, ignore_errors):
        parts = []
        while match:
            parts.extend([
                unescaper(match.before),
                unic(self._get_variable_value(match, ignore_errors))
            ])
            match = search_variable(match.after, ignore_errors=ignore_errors)
        parts.append(unescaper(match.string))
        return ''.join(parts)

    def _get_variable_value(self, match, ignore_errors):
        match.resolve_base(self, ignore_errors)
        # TODO: Do we anymore need to reserve `*{var}` syntax for anything?
        if match.identifier == '*':
            logger.warn(r"Syntax '%s' is reserved for future use. Please "
                        r"escape it like '\%s'." % (match, match))
            return unic(match)
        try:
            value = self._variables[match]
            if match.items:
                value = self._get_variable_item(match, value)
        except DataError:
            if not ignore_errors:
                raise
            value = unescape(match.match)
        return value

    def _get_variable_item(self, match, value):
        name = match.name
        if match.identifier in '@&':
            var = '%s[%s]' % (name, match.items[0])
            logger.warn("Accessing variable items using '%s' syntax "
                        "is deprecated. Use '$%s' instead." % (var, var[1:]))
        for item in match.items:
            if is_sequence(value):
                value = self._get_sequence_variable_item(name, value, item)
            elif is_subscriptable(value):
                value = self._get_subscriptable_variable_item(name, value, item)
            else:
                raise VariableError(
                    "Variable '%s' is %s, which is not subscriptable, and "
                    "thus accessing item '%s' from it is not possible. To use "
                    "'[%s]' as a literal value, it needs to be escaped like "
                    "'\\[%s]'." % (name, type_name(value), item, item, item)
                )
            name = '%s[%s]' % (name, item)
        return value

    def _get_sequence_variable_item(self, name, variable, index):
        index = self.replace_string(index)
        try:
            index = self._parse_sequence_variable_index(index, name[0] == '$')
        except ValueError:
            raise VariableError("%s '%s' used with invalid index '%s'. "
                                "To use '[%s]' as a literal value, it needs "
                                "to be escaped like '\\[%s]'."
                                % (type_name(variable, capitalize=True), name,
                                   index, index, index))
        try:
            return variable[index]
        except IndexError:
            raise VariableError("%s '%s' has no item in index %d."
                                % (type_name(variable, capitalize=True), name,
                                   index))

    def _parse_sequence_variable_index(self, index, support_slice=True):
        if ':' not in index:
            return int(index)
        if index.count(':') > 2 or not support_slice:
            raise ValueError
        return slice(*[int(i) if i else None for i in index.split(':')])

    def _get_subscriptable_variable_item(self, name, variable, item):
        """Gets item from a subscriptable variable.

        This variable can be a dictionary for example, but also a custom class
        that implements __getitem__(). If the item is not a variable, the
        subscriptable variable gets treated as a sequence, which means
        that the item is allowed to be an index/slice given as a string.
        """
        item = self.replace_scalar(item)
        try:
            return variable[item]
        except KeyError:
            raise VariableError("%s '%s' has no item '%s'."
                                % (type_name(variable, capitalize=True),
                                   name, item))
        except Exception as err:
            # Try to treat custom class as a Sequence but don't raise error
            # on failure
            try:
                return self._get_sequence_variable_item(name, variable, item)
            except:
                pass
            raise VariableError("Accessing item '%s' from %s '%s' failed: %s"
                                % (item, type_name(variable), name, err))
