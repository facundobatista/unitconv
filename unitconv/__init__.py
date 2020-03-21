# -*- coding: utf-8 -*-

# Copyright 2010-2018 Canonical Ltd.
# All Rights Reserved

"""A units converter."""

from __future__ import division, print_function

import collections
import itertools
import logging
import math
import random
import re

import pint

__all__ = ['convert']

logger = logging.getLogger(__name__)

_ureg = pint.UnitRegistry()

UnitInfo = collections.namedtuple("UnitInfo", "mult unit human_single human_plural")

# crazy regex to match a number; this comes from the Python's Decimal code,
# adapted to support also commas
RE_NUMBER = """        # A numeric string consists of:
    (?=\d|\.\d|\,\d)           # starts with a number or a point/comma
    (?P<int>\d*)               # having a (possibly empty) integer part
    ((\.|\,)(?P<frac>\d*))?    # followed by an optional fractional part
    ((e|E)(?P<exp>[-+]?\d+))?  # followed by an optional exponent, or...
"""


# supported units by the system; the key is the reference name, its
# multiplier (if any) and the pint unit
SUPPORTED_UNITS = {
    u'are': (None, _ureg.are),
    u'celsius': (None, _ureg.degC),
    u'centimeter': (None, _ureg.centimeter),
    u'cubic_centimeter': (None, _ureg.centimeter ** 3),
    u'cubic_foot': (None, _ureg.feet ** 3),
    u'cubic_inch': (None, _ureg.inch ** 3),
    u'cubic_kilometer': (None, _ureg.kilometer ** 3),
    u'cubic_meter': (None, _ureg.meter ** 3),
    u'cubic_mile': (None, _ureg.mile ** 3),
    u'cubic_yard': (None, _ureg.yard ** 3),
    u'cup': (None, _ureg.cup),
    u'day': (None, _ureg.day),
    u'fahrenheit': (None, _ureg.degF),
    u'fluid_ounce': (None, _ureg.floz),
    u'foot': (None, _ureg.feet),
    u'gallon': (None, _ureg.gallon),
    u'gram': (None, _ureg.grams),
    u'hectare': (100, _ureg.are),
    u'hour': (None, _ureg.hour),
    u'inch': (None, _ureg.inch),
    u'kelvin': (None, _ureg.degK),
    u'kilogram': (None, _ureg.kilogram),
    u'kilometer': (None, _ureg.kilometer),
    u'litre': (None, _ureg.litres),
    u'meter': (None, _ureg.meter),
    u'metric_ton': (None, _ureg.metric_ton),
    u'mile': (None, _ureg.mile),
    u'milligram': (.001, _ureg.gram),
    u'millilitre': (.001, _ureg.litre),
    u'minute': (None, _ureg.minute),
    u'month': (None, _ureg.month),
    u'ounce': (None, _ureg.oz),
    u'pint': (None, _ureg.pint),
    u'pound': (None, _ureg.pound),
    u'quart': (None, _ureg.quart),
    u'second': (None, _ureg.second),
    u'short_ton': (None, _ureg.ton),
    u'square_centimeter': (None, _ureg.centimeter ** 2),
    u'square_foot': (None, _ureg.feet ** 2),
    u'square_inch': (None, _ureg.inch ** 2),
    u'square_kilometer': (None, _ureg.kilometer ** 2),
    u'square_meter': (None, _ureg.meter ** 2),
    u'square_mile': (None, _ureg.mile ** 2),
    u'square_yard': (None, _ureg.yard ** 2),
    u'tablespoon': (None, _ureg.tablespoon),
    u'teaspoon': (None, _ureg.teaspoon),
    u'week': (None, _ureg.week),
    u'yard': (None, _ureg.yard),
    u'year': (None, _ureg.year),
}


# unit symbols (not to be translated), indicating the symbol, the supported
# unit name, and if it's linear (so we add area and volume postfixes)
UNIT_SYMBOLS = [
    (u'c', u'celsius', False),
    (u'c', u'cup', False),
    (u'cc', u'cubic_centimeter', False),
    (u'cm', u'centimeter', True),
    (u'd', u'day', False),
    (u'f', u'fahrenheit', False),
    (u'f', u'foot', True),
    (u'ft', u'foot', True),
    (u'g', u'gram', False),
    (u'h', u'hour', False),
    (u'in', u'inch', True),
    (u'k', u'kelvin', False),
    (u'kg', u'kilogram', False),
    (u'km', u'kilometer', True),
    (u'l', u'litre', False),
    (u'm', u'meter', True),
    (u'm', u'month', False),
    (u'mg', u'milligram', False),
    (u'mi', u'mile', True),
    (u'ml', u'millilitre', False),
    (u's', u'second', False),
    (u't', u'metric_ton', False),
    (u'w', u'week', False),
    (u'y', u'yard', True),
    (u'y', u'year', False),
    (u'°c', u'celsius', False),
    (u'°f', u'fahrenheit', False),
]

# synonyms, abbreviations, and other names for same unit; and also
# multi-word conversions
EXTRA_UNITS_INPUT = [
    (u'ares', u'are'),
    (u'centimeters', u'centimeter'),
    (u'cubic centimeter', u'cubic_centimeter'),
    (u'cubic centimeters', u'cubic_centimeter'),
    (u'cubic cm', u'cubic_centimeter'),
    (u'cubic feet', u'cubic_foot'),
    (u'cubic foot', u'cubic_foot'),
    (u'cubic ft', u'cubic_foot'),
    (u'cubic in', u'cubic_inch'),
    (u'cubic inch', u'cubic_inch'),
    (u'cubic inches', u'cubic_inch'),
    (u'cubic kilometer', u'cubic_kilometer'),
    (u'cubic kilometers', u'cubic_kilometer'),
    (u'cubic km', u'cubic_kilometer'),
    (u'cubic m', u'cubic_meter'),
    (u'cubic meter', u'cubic_meter'),
    (u'cubic meters', u'cubic_meter'),
    (u'cubic mi', u'cubic_mile'),
    (u'cubic mile', u'cubic_mile'),
    (u'cubic miles', u'cubic_mile'),
    (u'cubic y', u'cubic_yard'),
    (u'cubic yard', u'cubic_yard'),
    (u'cubic yards', u'cubic_yard'),
    (u'cups', u'cup'),
    (u'days', u'day'),
    (u'feet', u'foot'),
    (u'floz', u'fluid_ounce'),
    (u'flozs', u'fluid_ounce'),
    (u'fluid ounce', u'fluid_ounce'),
    (u'fluid ounces', u'fluid_ounce'),
    (u'gal', u'gallon'),
    (u'gallons', u'gallon'),
    (u'grams', u'gram'),
    (u'hectares', u'hectare'),
    (u'hours', u'hour'),
    (u'inches', u'inch'),
    (u'kilograms', u'kilogram'),
    (u'kilometers', u'kilometer'),
    (u'lb', u'pound'),
    (u'lbs', u'pound'),
    (u'liter', u'litre'),
    (u'liters', u'litre'),
    (u'litres', u'litre'),
    (u'meters', u'meter'),
    (u'metric ton', u'metric_ton'),
    (u'metric tons', u'metric_ton'),
    (u'miles', u'mile'),
    (u'milligrams', u'milligram'),
    (u'milliliter', u'millilitre'),
    (u'milliliters', u'millilitre'),
    (u'millilitres', u'millilitre'),
    (u'min', u'minute'),
    (u'minutes', u'minute'),
    (u'months', u'month'),
    (u'ounce', u'fluid_ounce'),
    (u'ounces', u'fluid_ounce'),
    (u'ounces', u'ounce'),
    (u'oz', u'fluid_ounce'),
    (u'oz', u'ounce'),
    (u'ozs', u'fluid_ounce'),
    (u'ozs', u'ounce'),
    (u'pints', u'pint'),
    (u'pounds', u'pound'),
    (u'qt', u'quart'),
    (u'qts', u'quart'),
    (u'quarts', u'quart'),
    (u'sec', u'second'),
    (u'seconds', u'second'),
    (u'short ton', u'short_ton'),
    (u'short tons', u'short_ton'),
    (u'sq centimeter', u'square_centimeter'),
    (u'sq centimeters', u'square_centimeter'),
    (u'sq cm', u'square_centimeter'),
    (u'sq feet', u'square_foot'),
    (u'sq foot', u'square_foot'),
    (u'sq ft', u'square_foot'),
    (u'sq in', u'square_inch'),
    (u'sq inch', u'square_inch'),
    (u'sq inches', u'square_inch'),
    (u'sq kilometer', u'square_kilometer'),
    (u'sq kilometers', u'square_kilometer'),
    (u'sq km', u'square_kilometer'),
    (u'sq m', u'square_meter'),
    (u'sq meter', u'square_meter'),
    (u'sq meters', u'square_meter'),
    (u'sq mi', u'square_mile'),
    (u'sq mile', u'square_mile'),
    (u'sq miles', u'square_mile'),
    (u'sq y', u'square_yard'),
    (u'sq yard', u'square_yard'),
    (u'sq yards', u'square_yard'),
    (u'square centimeter', u'square_centimeter'),
    (u'square centimeters', u'square_centimeter'),
    (u'square cm', u'square_centimeter'),
    (u'square feet', u'square_foot'),
    (u'square foot', u'square_foot'),
    (u'square ft', u'square_foot'),
    (u'square in', u'square_inch'),
    (u'square inch', u'square_inch'),
    (u'square inches', u'square_inch'),
    (u'square kilometer', u'square_kilometer'),
    (u'square kilometers', u'square_kilometer'),
    (u'square km', u'square_kilometer'),
    (u'square m', u'square_meter'),
    (u'square meter', u'square_meter'),
    (u'square meters', u'square_meter'),
    (u'square mi', u'square_mile'),
    (u'square mile', u'square_mile'),
    (u'square miles', u'square_mile'),
    (u'square y', u'square_yard'),
    (u'square yard', u'square_yard'),
    (u'square yards', u'square_yard'),
    (u'tablespoons', u'tablespoon'),
    (u'tbs', u'tablespoon'),
    (u'tbsp', u'tablespoon'),
    (u'teaspoons', u'teaspoon'),
    (u'ton', u'short_ton'),
    (u'tonne', u'metric_ton'),
    (u'ts', u'teaspoon'),
    (u'tsp', u'teaspoon'),
    (u'weeks', u'week'),
    (u'yards', u'yard'),
    (u'years', u'year'),
]

# human unit representation for outputs to the user
UNITS_OUTPUT = {
    u'are': (u'{} are', u'{} ares'),
    u'celsius': (u'{}°C', u'{}°C'),
    u'centimeter': (u'{} centimeter', u'{} centimeters'),
    u'cubic_centimeter': (u'{} cubic centimeter', u'{} cubic centimeters'),
    u'cubic_foot': (u'{} cubic foot', u'{} cubic feet'),
    u'cubic_inch': (u'{} cubic inch', u'{} cubic inches'),
    u'cubic_kilometer': (u'{} cubic kilometer', u'{} cubic kilometers'),
    u'cubic_meter': (u'{} cubic meter', u'{} cubic meters'),
    u'cubic_mile': (u'{} cubic mile', u'{} cubic miles'),
    u'cubic_yard': (u'{} cubic yard', u'{} cubic yards'),
    u'cup': (u'{} US cup', u'{} US cups'),
    u'day': (u'{} day', u'{} days'),
    u'fahrenheit': (u'{}°F', u'{}°F'),
    u'fluid_ounce': (u'{} US fluid ounce', u'{} US fluid ounces'),
    u'foot': (u'{} foot', u'{} feet'),
    u'gallon': (u'{} US gallon', u'{} US gallons'),
    u'gram': (u'{} gram', u'{} grams'),
    u'hectare': (u'{} hectare', u'{} hectares'),
    u'hour': (u'{} hour', u'{} hours'),
    u'inch': (u'{} inch', u'{} inches'),
    u'kelvin': (u'{}K', u'{}K'),
    u'kilogram': (u'{} kilogram', u'{} kilograms'),
    u'kilometer': (u'{} kilometer', u'{} kilometers'),
    u'litre': (u'{} litre', u'{} litres'),
    u'meter': (u'{} meter', u'{} meters'),
    u'metric_ton': (u'{} metric ton', u'{} metric tons'),
    u'mile': (u'{} mile', u'{} miles'),
    u'milligram': (u'{} milligram', u'{} milligrams'),
    u'millilitre': (u'{} millilitre', u'{} millilitres'),
    u'minute': (u'{} minute', u'{} minutes'),
    u'month': (u'{} month', u'{} months'),
    u'ounce': (u'{} ounce', u'{} ounces'),
    u'pint': (u'{} US pint', u'{} US pints'),
    u'pound': (u'{} pound', u'{} pounds'),
    u'quart': (u'{} quart', u'{} quarts'),
    u'second': (u'{} second', u'{} seconds'),
    u'square_centimeter': (u'{} square centimeter', u'{} square centimeters'),
    u'square_foot': (u'{} square foot', u'{} square feet'),
    u'square_inch': (u'{} square inch', u'{} square inches'),
    u'square_kilometer': (u'{} square kilometer', u'{} square kilometers'),
    u'square_meter': (u'{} square meter', u'{} square meters'),
    u'square_mile': (u'{} square mile', u'{} square miles'),
    u'square_yard': (u'{} square yard', u'{} square yards'),
    u'tablespoon': (u'{} US tablespoon', u'{} US tablespoons'),
    u'teaspoon': (u'{} US teaspoon', u'{} US teaspoons'),
    u'short_ton': (u'{} short ton', u'{} short tons'),
    u'week': (u'{} week', u'{} weeks'),
    u'yard': (u'{} yard', u'{} yards'),
    u'year': (u'{} year', u'{} years'),
}

# normal connectors in user input
CONNECTORS = [
    u'to',
    u'in',
]

# facts list to provide useful/fun information about numbers
NUMBERS_INFO = [
    (3.2, u'meters', u'wingspan', u'a large andean condor'),
    (5.5, u'meters', u'length', u'a white wale'),
    (41, u'centimeters', u'height', u'a blue penguin'),
    (146, u'meters', u'height', u'the Great Pyramid of Giza'),
    (113, u'km/h', u'top speed', u'a cheetah'),
    (3475, u'kilometers', u'diameter', u'the Moon'),
    (1600, u'kilograms', u'weight', u' a white wale'),
    (8850, u'meters', u'height', u'Mount Everest'),
    (5500, u'°C', u'temperature', u'the surface of the Sun'),
    (12756, u'kilometers', u'diameter', u'the Earth'),
    (6430, u'kilometers', u'lenght', u'the Great Wall of China'),
    (100, u'°C', u'temperature', u'boiling water'),
]

# we will not always select the best match for number info (as it will be
# too repeated), but will select randomly between the top N:
NUMBERS_UNCERTAINTY = 3

# table to suggest a second unit; general rules are:
#  - if it's temperature, just go celsius<->fahrenheit
#  - if it's time, go to a lower unit, but not immediate one (which is
#    so easy that user shouldn't need it the unit conversor)
#  - for the rest, just go imperial<->metric, using a similar size unit
SUGGESTED_SECOND_UNIT = {
    u'are': 'square_yard',
    u'celsius': 'fahrenheit',
    u'centimeter': 'inch',
    u'cubic_centimeter': 'fluid_ounce',
    u'cubic_foot': 'litre',
    u'cubic_inch': 'millilitre',
    u'cubic_kilometer': 'cubic_mile',
    u'cubic_meter': 'cubic_yard',
    u'cubic_mile': 'cubic_kilometer',
    u'cubic_yard': 'cubic_meter',
    u'cup': 'millilitre',
    u'day': 'hour',
    u'fahrenheit': u'celsius',
    u'fluid_ounce': 'millilitre',
    u'foot': 'meter',
    u'gallon': 'litre',
    u'gram': 'ounce',
    u'hectare': 'square_mile',
    u'hour': 'second',
    u'inch': 'centimeter',
    u'kilogram': 'pound',
    u'kilometer': 'mile',
    u'litre': 'gallon',
    u'meter': 'yard',
    u'mile': 'kilometer',
    u'minute': 'second',
    u'month': 'day',
    u'ounce': 'gram',
    u'pint': 'litre',
    u'pound': 'kilogram',
    u'quart': 'litre',
    u'square_centimeter': 'square_inch',
    u'square_foot': 'square_meter',
    u'square_inch': 'square_centimeter',
    u'square_kilometer': 'square_mile',
    u'square_meter': 'square_foot',
    u'square_mile': 'square_kilometer',
    u'square_yard': 'square_meter',
    u'tablespoon': 'millilitre',
    u'teaspoon': 'millilitre',
    u'week': 'hour',
    u'yard': 'meter',
    u'year': 'day',
}


class _UnitManager(object):
    """A unique class to hold all units mambo jambo."""

    def __init__(self):
        # generate the main unit conversion structure
        self._units = _u = {k: [k] for k in SUPPORTED_UNITS}

        for name, syn in EXTRA_UNITS_INPUT:
            _u.setdefault(name, []).append(syn)

        for symbol, unit, linear in UNIT_SYMBOLS:
            _u.setdefault(symbol, []).append(unit)
            if linear:
                _u[symbol + u'SUPERSCRIPT_TWO'] = _u[u'square_' + unit]
                _u[symbol + u'SUPERSCRIPT_THREE'] = _u[u'cubic_' + unit]

        # generate the useful tokens
        _all_tokens = set(itertools.chain(_u.keys(), CONNECTORS))
        self.useful_tokens = sorted(_all_tokens, key=len, reverse=True)

        # generate the complex units conversion
        _c = ((k, v) for k, v in EXTRA_UNITS_INPUT if ' ' in k)
        self.complex_units = sorted(_c, key=lambda x: len(x[0]), reverse=True)

        # the connectors
        self.connectors = CONNECTORS

    def get_units_info(self, unit_token_from, unit_token_to):
        """Return the info for the unit."""
        base_units_from = self._units[unit_token_from]
        base_units_to = self._units[unit_token_to]
        useful = []
        for b_u_from in base_units_from:
            for b_u_to in base_units_to:
                mult_from, u_from = SUPPORTED_UNITS[b_u_from]
                mult_to, u_to = SUPPORTED_UNITS[b_u_to]
                if u_from.dimensionality == u_to.dimensionality:
                    h_from_s, h_from_p = UNITS_OUTPUT[b_u_from]
                    h_to_s, h_to_p = UNITS_OUTPUT[b_u_to]
                    useful.append((UnitInfo(mult_from, u_from, h_from_s, h_from_p),
                                   UnitInfo(mult_to, u_to, h_to_s, h_to_p)))

        # return units info if there's a nice crossing and no ambiguity
        if len(useful) == 1:
            return useful[0]

    def suggest(self, unit_token_from):
        """Suggest a second destination unit."""
        base_units_from = self._units[unit_token_from]
        for b_u_from in base_units_from:
            if b_u_from in SUGGESTED_SECOND_UNIT:
                return SUGGESTED_SECOND_UNIT[b_u_from]


unit_manager = _UnitManager()


def _numbers_info(number):
    """Provide useful/fun info about some numbers."""
    results = []
    for value, unit, dimension, target in NUMBERS_INFO:
        msg = None
        vals = locals()
        if value * .4 <= number <= value * .6:
            msg = u"{number} {unit} is about half of the {dimension} of {target}"
        elif value * .9 <= number <= value * 1.1:
            msg = u"{number} {unit} is close to the {dimension} of {target}"
        elif value * 1.7 <= number <= value * 100:
            vals['mult'] = int(round(number / value))
            msg = u"{number} {unit} is around {mult} times the {dimension} of {target}"

        if msg is not None:
            text = msg.format(**vals)
            distance = abs(math.log10(number) - math.log10(value))
            results.append((distance, text))

    if results:
        return random.choice([x[1] for x in sorted(results)[:NUMBERS_UNCERTAINTY]])


def parse_number(m):
    """Return a float from a match of the regex above."""
    intpart, fracpart, expart = m.group('int', 'frac', 'exp')
    if intpart:
        result = int(intpart)
    else:
        result = 0
    if fracpart:
        result += float(fracpart) / 10 ** len(fracpart)
    if expart:
        result *= 10 ** int(expart)
    return result


def convert(source):
    """Parse and convert the units found in the source text."""
    logger.debug("Input: %r", source)
    text = source.strip().lower()

    # normalize square and cubic combinations
    text = re.sub(u" *?\*\* *?2| *?\^ *?2|(?<=[a-zA-Z])2|²",
                  u'SUPERSCRIPT_TWO', text)
    text = re.sub(u" *?\*\* *?3| *?\^ *?3|(?<=[a-zA-Z])3|³",
                  u'SUPERSCRIPT_THREE', text)

    # replace the complex units to something useful
    for cu, real in unit_manager.complex_units:
        text = re.sub(cu, real, text)
    logger.debug("Preconverted: %r", text)

    m = re.search(RE_NUMBER, text, re.VERBOSE)
    if not m:
        logger.debug("OOPS, not number found")
        return
    number = parse_number(m)
    num_start, num_end = m.span()
    logger.debug("Number: %r  (limit=%s)", number, m.span())

    tokens = []
    found_tokens_before = False
    for part in re.split('\W', text[:num_start], re.UNICODE):
        for token in unit_manager.useful_tokens:
            if part == token:
                found_tokens_before = True
                tokens.append(token)
                break
    for part in re.split('\W', text[num_end:], re.UNICODE):
        for token in unit_manager.useful_tokens:
            if part == token:
                tokens.append(token)
    logger.debug("Tokens found: %s", tokens)

    if len(tokens) == 0:
        # only give number info if the number is alone
        if num_end - num_start == len(text.strip()):
            ni = _numbers_info(number)
            logger.debug("Numbers info: %r", ni)
            return ni
        else:
            return

    if len(tokens) == 1:
        # suggest the second unit
        suggested = unit_manager.suggest(tokens[0])
        if suggested is None:
            return

        # use suggested unit and assure it's the destination one
        logger.debug("Suggesting 2nd unit: %r", suggested)
        tokens.append(suggested)
        found_tokens_before = False

    if len(tokens) > 2:
        for conn in unit_manager.connectors:
            if conn in tokens:
                tokens.remove(conn)
                if len(tokens) == 2:
                    break
        else:
            logger.debug("OOPS, not enough tokens")
            return
    logger.debug("Tokens filtered: %s", tokens)

    if not found_tokens_before:
        # everything is after the number
        t_from_pos = 0
        t_to_pos = 1
    else:
        t_from_pos = 1
        t_to_pos = 0
    logger.debug("Token selector: from=%s to=%s", t_from_pos, t_to_pos)

    t_from = tokens[t_from_pos]
    t_to = tokens[t_to_pos]
    units_info = unit_manager.get_units_info(t_from, t_to)
    if units_info is None:
        logger.debug("OOPS, no matching units")
        return
    unit_from, unit_to = units_info

    to_convert = _ureg.Quantity(number, unit_from.unit)
    if unit_from.mult is not None:
        to_convert *= unit_from.mult
    try:
        converted = to_convert.to(unit_to.unit)
    except pint.unit.DimensionalityError:
        logger.debug("OOPS, dimensionality error")
        return
    if unit_to.mult is not None:
        converted /= unit_to.mult
    logger.debug("Converted: %r", converted)

    rounded = round(converted.magnitude, 4)
    human_from, human_to = unit_from.human_plural, unit_to.human_plural

    # care about result formatting
    if rounded.is_integer():
        if rounded == 1:
            human_to = unit_to.human_single
        nicer_res = str(int(rounded))
    else:
        nicer_res = "%.4f" % rounded
        # as it's not an integer, remove extra 0s at the right
        while nicer_res[-1] == '0':
            nicer_res = nicer_res[:-1]
    logger.debug("Nicer number: %r", nicer_res)

    # care about source formatting
    if number == 1:
        human_from = unit_from.human_single
    if isinstance(number, float) and number.is_integer():
        nicer_orig = str(int(number))
    else:
        nicer_orig = str(number)

    return human_from.format(nicer_orig) + ' = ' + human_to.format(nicer_res)


if __name__ == '__main__':
    import sys

    # set up logging so it's easier to debug
    logger.setLevel(logging.DEBUG)
    h = logging.StreamHandler()
    h.setLevel(logging.DEBUG)
    logger.addHandler(h)
    print("Response:", convert(" ".join(sys.argv[1:])))
