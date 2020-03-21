# Copyright 2010-2018 Canonical Ltd.
# Copyright 2020 Facundo Batista
# All Rights Reserved

"""A units converter."""

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
RE_NUMBER = r"""               # A numeric string consists of:
    (?=\d|\.\d|\,\d)           # starts with a number or a point/comma
    (?P<int>\d*)               # having a (possibly empty) integer part
    ((\.|\,)(?P<frac>\d*))?    # followed by an optional fractional part
    ((e|E)(?P<exp>[-+]?\d+))?  # followed by an optional exponent, or...
"""


# supported units by the system; the key is the reference name, its
# multiplier (if any) and the pint unit
SUPPORTED_UNITS = {
    'are': (None, _ureg.are),
    'celsius': (None, _ureg.degC),
    'centimeter': (None, _ureg.centimeter),
    'cubic_centimeter': (None, _ureg.centimeter ** 3),
    'cubic_foot': (None, _ureg.feet ** 3),
    'cubic_inch': (None, _ureg.inch ** 3),
    'cubic_kilometer': (None, _ureg.kilometer ** 3),
    'cubic_meter': (None, _ureg.meter ** 3),
    'cubic_mile': (None, _ureg.mile ** 3),
    'cubic_yard': (None, _ureg.yard ** 3),
    'cup': (None, _ureg.cup),
    'day': (None, _ureg.day),
    'fahrenheit': (None, _ureg.degF),
    'fluid_ounce': (None, _ureg.floz),
    'foot': (None, _ureg.feet),
    'gallon': (None, _ureg.gallon),
    'gram': (None, _ureg.grams),
    'hectare': (100, _ureg.are),
    'hour': (None, _ureg.hour),
    'inch': (None, _ureg.inch),
    'kelvin': (None, _ureg.degK),
    'kilogram': (None, _ureg.kilogram),
    'kilometer': (None, _ureg.kilometer),
    'litre': (None, _ureg.litres),
    'meter': (None, _ureg.meter),
    'metric_ton': (None, _ureg.metric_ton),
    'mile': (None, _ureg.mile),
    'milligram': (.001, _ureg.gram),
    'millilitre': (.001, _ureg.litre),
    'minute': (None, _ureg.minute),
    'month': (None, _ureg.month),
    'ounce': (None, _ureg.oz),
    'pint': (None, _ureg.pint),
    'pound': (None, _ureg.pound),
    'quart': (None, _ureg.quart),
    'second': (None, _ureg.second),
    'short_ton': (None, _ureg.ton),
    'square_centimeter': (None, _ureg.centimeter ** 2),
    'square_foot': (None, _ureg.feet ** 2),
    'square_inch': (None, _ureg.inch ** 2),
    'square_kilometer': (None, _ureg.kilometer ** 2),
    'square_meter': (None, _ureg.meter ** 2),
    'square_mile': (None, _ureg.mile ** 2),
    'square_yard': (None, _ureg.yard ** 2),
    'tablespoon': (None, _ureg.tablespoon),
    'teaspoon': (None, _ureg.teaspoon),
    'week': (None, _ureg.week),
    'yard': (None, _ureg.yard),
    'year': (None, _ureg.year),
}


# unit symbols (not to be translated), indicating the symbol, the supported
# unit name, and if it's linear (so we add area and volume postfixes)
UNIT_SYMBOLS = [
    ('c', 'celsius', False),
    ('c', 'cup', False),
    ('cc', 'cubic_centimeter', False),
    ('cm', 'centimeter', True),
    ('d', 'day', False),
    ('f', 'fahrenheit', False),
    ('f', 'foot', True),
    ('ft', 'foot', True),
    ('g', 'gram', False),
    ('h', 'hour', False),
    ('in', 'inch', True),
    ('k', 'kelvin', False),
    ('kg', 'kilogram', False),
    ('km', 'kilometer', True),
    ('l', 'litre', False),
    ('m', 'meter', True),
    ('m', 'month', False),
    ('mg', 'milligram', False),
    ('mi', 'mile', True),
    ('ml', 'millilitre', False),
    ('s', 'second', False),
    ('t', 'metric_ton', False),
    ('w', 'week', False),
    ('y', 'yard', True),
    ('y', 'year', False),
    ('°c', 'celsius', False),
    ('°f', 'fahrenheit', False),
]

# synonyms, abbreviations, and other names for same unit; and also
# multi-word conversions
EXTRA_UNITS_INPUT = [
    ('ares', 'are'),
    ('centimeters', 'centimeter'),
    ('cubic centimeter', 'cubic_centimeter'),
    ('cubic centimeters', 'cubic_centimeter'),
    ('cubic cm', 'cubic_centimeter'),
    ('cubic feet', 'cubic_foot'),
    ('cubic foot', 'cubic_foot'),
    ('cubic ft', 'cubic_foot'),
    ('cubic in', 'cubic_inch'),
    ('cubic inch', 'cubic_inch'),
    ('cubic inches', 'cubic_inch'),
    ('cubic kilometer', 'cubic_kilometer'),
    ('cubic kilometers', 'cubic_kilometer'),
    ('cubic km', 'cubic_kilometer'),
    ('cubic m', 'cubic_meter'),
    ('cubic meter', 'cubic_meter'),
    ('cubic meters', 'cubic_meter'),
    ('cubic mi', 'cubic_mile'),
    ('cubic mile', 'cubic_mile'),
    ('cubic miles', 'cubic_mile'),
    ('cubic y', 'cubic_yard'),
    ('cubic yard', 'cubic_yard'),
    ('cubic yards', 'cubic_yard'),
    ('cups', 'cup'),
    ('days', 'day'),
    ('feet', 'foot'),
    ('floz', 'fluid_ounce'),
    ('flozs', 'fluid_ounce'),
    ('fluid ounce', 'fluid_ounce'),
    ('fluid ounces', 'fluid_ounce'),
    ('gal', 'gallon'),
    ('gallons', 'gallon'),
    ('grams', 'gram'),
    ('hectares', 'hectare'),
    ('hours', 'hour'),
    ('inches', 'inch'),
    ('kilograms', 'kilogram'),
    ('kilometers', 'kilometer'),
    ('lb', 'pound'),
    ('lbs', 'pound'),
    ('liter', 'litre'),
    ('liters', 'litre'),
    ('litres', 'litre'),
    ('meters', 'meter'),
    ('metric ton', 'metric_ton'),
    ('metric tons', 'metric_ton'),
    ('miles', 'mile'),
    ('milligrams', 'milligram'),
    ('milliliter', 'millilitre'),
    ('milliliters', 'millilitre'),
    ('millilitres', 'millilitre'),
    ('min', 'minute'),
    ('minutes', 'minute'),
    ('months', 'month'),
    ('ounce', 'fluid_ounce'),
    ('ounces', 'fluid_ounce'),
    ('ounces', 'ounce'),
    ('oz', 'fluid_ounce'),
    ('oz', 'ounce'),
    ('ozs', 'fluid_ounce'),
    ('ozs', 'ounce'),
    ('pints', 'pint'),
    ('pounds', 'pound'),
    ('qt', 'quart'),
    ('qts', 'quart'),
    ('quarts', 'quart'),
    ('sec', 'second'),
    ('seconds', 'second'),
    ('short ton', 'short_ton'),
    ('short tons', 'short_ton'),
    ('sq centimeter', 'square_centimeter'),
    ('sq centimeters', 'square_centimeter'),
    ('sq cm', 'square_centimeter'),
    ('sq feet', 'square_foot'),
    ('sq foot', 'square_foot'),
    ('sq ft', 'square_foot'),
    ('sq in', 'square_inch'),
    ('sq inch', 'square_inch'),
    ('sq inches', 'square_inch'),
    ('sq kilometer', 'square_kilometer'),
    ('sq kilometers', 'square_kilometer'),
    ('sq km', 'square_kilometer'),
    ('sq m', 'square_meter'),
    ('sq meter', 'square_meter'),
    ('sq meters', 'square_meter'),
    ('sq mi', 'square_mile'),
    ('sq mile', 'square_mile'),
    ('sq miles', 'square_mile'),
    ('sq y', 'square_yard'),
    ('sq yard', 'square_yard'),
    ('sq yards', 'square_yard'),
    ('square centimeter', 'square_centimeter'),
    ('square centimeters', 'square_centimeter'),
    ('square cm', 'square_centimeter'),
    ('square feet', 'square_foot'),
    ('square foot', 'square_foot'),
    ('square ft', 'square_foot'),
    ('square in', 'square_inch'),
    ('square inch', 'square_inch'),
    ('square inches', 'square_inch'),
    ('square kilometer', 'square_kilometer'),
    ('square kilometers', 'square_kilometer'),
    ('square km', 'square_kilometer'),
    ('square m', 'square_meter'),
    ('square meter', 'square_meter'),
    ('square meters', 'square_meter'),
    ('square mi', 'square_mile'),
    ('square mile', 'square_mile'),
    ('square miles', 'square_mile'),
    ('square y', 'square_yard'),
    ('square yard', 'square_yard'),
    ('square yards', 'square_yard'),
    ('tablespoons', 'tablespoon'),
    ('tbs', 'tablespoon'),
    ('tbsp', 'tablespoon'),
    ('teaspoons', 'teaspoon'),
    ('ton', 'short_ton'),
    ('tonne', 'metric_ton'),
    ('ts', 'teaspoon'),
    ('tsp', 'teaspoon'),
    ('weeks', 'week'),
    ('yards', 'yard'),
    ('years', 'year'),
]

# human unit representation for outputs to the user
UNITS_OUTPUT = {
    'are': ('{} are', '{} ares'),
    'celsius': ('{}°C', '{}°C'),
    'centimeter': ('{} centimeter', '{} centimeters'),
    'cubic_centimeter': ('{} cubic centimeter', '{} cubic centimeters'),
    'cubic_foot': ('{} cubic foot', '{} cubic feet'),
    'cubic_inch': ('{} cubic inch', '{} cubic inches'),
    'cubic_kilometer': ('{} cubic kilometer', '{} cubic kilometers'),
    'cubic_meter': ('{} cubic meter', '{} cubic meters'),
    'cubic_mile': ('{} cubic mile', '{} cubic miles'),
    'cubic_yard': ('{} cubic yard', '{} cubic yards'),
    'cup': ('{} US cup', '{} US cups'),
    'day': ('{} day', '{} days'),
    'fahrenheit': ('{}°F', '{}°F'),
    'fluid_ounce': ('{} US fluid ounce', '{} US fluid ounces'),
    'foot': ('{} foot', '{} feet'),
    'gallon': ('{} US gallon', '{} US gallons'),
    'gram': ('{} gram', '{} grams'),
    'hectare': ('{} hectare', '{} hectares'),
    'hour': ('{} hour', '{} hours'),
    'inch': ('{} inch', '{} inches'),
    'kelvin': ('{}K', '{}K'),
    'kilogram': ('{} kilogram', '{} kilograms'),
    'kilometer': ('{} kilometer', '{} kilometers'),
    'litre': ('{} litre', '{} litres'),
    'meter': ('{} meter', '{} meters'),
    'metric_ton': ('{} metric ton', '{} metric tons'),
    'mile': ('{} mile', '{} miles'),
    'milligram': ('{} milligram', '{} milligrams'),
    'millilitre': ('{} millilitre', '{} millilitres'),
    'minute': ('{} minute', '{} minutes'),
    'month': ('{} month', '{} months'),
    'ounce': ('{} ounce', '{} ounces'),
    'pint': ('{} US pint', '{} US pints'),
    'pound': ('{} pound', '{} pounds'),
    'quart': ('{} quart', '{} quarts'),
    'second': ('{} second', '{} seconds'),
    'square_centimeter': ('{} square centimeter', '{} square centimeters'),
    'square_foot': ('{} square foot', '{} square feet'),
    'square_inch': ('{} square inch', '{} square inches'),
    'square_kilometer': ('{} square kilometer', '{} square kilometers'),
    'square_meter': ('{} square meter', '{} square meters'),
    'square_mile': ('{} square mile', '{} square miles'),
    'square_yard': ('{} square yard', '{} square yards'),
    'tablespoon': ('{} US tablespoon', '{} US tablespoons'),
    'teaspoon': ('{} US teaspoon', '{} US teaspoons'),
    'short_ton': ('{} short ton', '{} short tons'),
    'week': ('{} week', '{} weeks'),
    'yard': ('{} yard', '{} yards'),
    'year': ('{} year', '{} years'),
}

# normal connectors in user input
CONNECTORS = [
    'to',
    'in',
]

# facts list to provide useful/fun information about numbers
NUMBERS_INFO = [
    (3.2, 'meters', 'wingspan', 'a large andean condor'),
    (5.5, 'meters', 'length', 'a white wale'),
    (41, 'centimeters', 'height', 'a blue penguin'),
    (146, 'meters', 'height', 'the Great Pyramid of Giza'),
    (113, 'km/h', 'top speed', 'a cheetah'),
    (3475, 'kilometers', 'diameter', 'the Moon'),
    (1600, 'kilograms', 'weight', ' a white wale'),
    (8850, 'meters', 'height', 'Mount Everest'),
    (5500, '°C', 'temperature', 'the surface of the Sun'),
    (12756, 'kilometers', 'diameter', 'the Earth'),
    (6430, 'kilometers', 'lenght', 'the Great Wall of China'),
    (100, '°C', 'temperature', 'boiling water'),
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
    'are': 'square_yard',
    'celsius': 'fahrenheit',
    'centimeter': 'inch',
    'cubic_centimeter': 'fluid_ounce',
    'cubic_foot': 'litre',
    'cubic_inch': 'millilitre',
    'cubic_kilometer': 'cubic_mile',
    'cubic_meter': 'cubic_yard',
    'cubic_mile': 'cubic_kilometer',
    'cubic_yard': 'cubic_meter',
    'cup': 'millilitre',
    'day': 'hour',
    'fahrenheit': 'celsius',
    'fluid_ounce': 'millilitre',
    'foot': 'meter',
    'gallon': 'litre',
    'gram': 'ounce',
    'hectare': 'square_mile',
    'hour': 'second',
    'inch': 'centimeter',
    'kilogram': 'pound',
    'kilometer': 'mile',
    'litre': 'gallon',
    'meter': 'yard',
    'mile': 'kilometer',
    'minute': 'second',
    'month': 'day',
    'ounce': 'gram',
    'pint': 'litre',
    'pound': 'kilogram',
    'quart': 'litre',
    'square_centimeter': 'square_inch',
    'square_foot': 'square_meter',
    'square_inch': 'square_centimeter',
    'square_kilometer': 'square_mile',
    'square_meter': 'square_foot',
    'square_mile': 'square_kilometer',
    'square_yard': 'square_meter',
    'tablespoon': 'millilitre',
    'teaspoon': 'millilitre',
    'week': 'hour',
    'yard': 'meter',
    'year': 'day',
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
                _u[symbol + 'SUPERSCRIPT_TWO'] = _u['square_' + unit]
                _u[symbol + 'SUPERSCRIPT_THREE'] = _u['cubic_' + unit]

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
            msg = "{number} {unit} is about half of the {dimension} of {target}"
        elif value * .9 <= number <= value * 1.1:
            msg = "{number} {unit} is close to the {dimension} of {target}"
        elif value * 1.7 <= number <= value * 100:
            vals['mult'] = int(round(number / value))
            msg = "{number} {unit} is around {mult} times the {dimension} of {target}"

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
    text = re.sub(r" *?\*\* *?2| *?\^ *?2|(?<=[a-zA-Z])2|²", 'SUPERSCRIPT_TWO', text)
    text = re.sub(r" *?\*\* *?3| *?\^ *?3|(?<=[a-zA-Z])3|³", 'SUPERSCRIPT_THREE', text)

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
    for part in re.split(r'\W', text[:num_start], re.UNICODE):
        for token in unit_manager.useful_tokens:
            if part == token:
                found_tokens_before = True
                tokens.append(token)
                break
    for part in re.split(r'\W', text[num_end:], re.UNICODE):
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
    if isinstance(rounded, int) or rounded.is_integer():
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
