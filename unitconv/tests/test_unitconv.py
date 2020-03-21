# -*- coding: utf-8 -*-

# Copyright 2010-2018 Canonical Ltd.
# All Rights Reserved

"""Tests for the units converter."""

import logging
import random
from unittest import TestCase
from io import BytesIO

from mock import patch

import unitconv

# store the logged globally to use when any of the check fail
_l = unitconv.logger
_l.setLevel(logging.DEBUG)
stored_logging = BytesIO()
_h = logging.StreamHandler(stored_logging)
_h.setLevel(logging.DEBUG)
_l.addHandler(_h)


class StructuresConsistencyTestCase(TestCase):
    """Some checks of the structures."""

    def test_extras_supported(self):
        extra_units = set(v for k, v in unitconv.EXTRA_UNITS_INPUT)
        miss = extra_units - set(unitconv.SUPPORTED_UNITS)
        self.assertFalse(miss, miss)

    def test_output_supported_match(self):
        miss = set(unitconv.UNITS_OUTPUT) ^ set(unitconv.SUPPORTED_UNITS)
        self.assertFalse(miss, miss)

    def test_suggested_from(self):
        miss = set(unitconv.SUGGESTED_SECOND_UNIT) - set(unitconv.SUPPORTED_UNITS)
        self.assertFalse(miss, miss)

    def test_suggested_to(self):
        miss = set(unitconv.SUGGESTED_SECOND_UNIT.values()) - set(unitconv.SUPPORTED_UNITS)
        self.assertFalse(miss, miss)


class CheckingTestCase(TestCase):
    """Common code for all test cases."""

    def check(self, operations):
        for inp, result in operations:
            # clean stored logs
            stored_logging.seek(0)
            stored_logging.truncate()

            try:
                calculated = unitconv.convert(inp)
            except Exception as err:
                logged = "Logged:\n" + stored_logging.getvalue()
                self.fail("Converter exploded with %s(%s) when %r\n%s" % (
                          err.__class__.__name__, err, inp, logged))
            else:
                logged = "Logged:\n" + stored_logging.getvalue()
                m = "%r gave %r (should: %r)\n%s" % (
                    inp, calculated, result, logged)
                self.assertEqual(calculated, result, m)


class BasicConversionsTestCase(CheckingTestCase):
    """Check the basic functionality: simple conversions."""

    def test_temperature(self):
        self.check([
            (u"45°C in fahrenheit", u"45°C = 113°F"),
            (u"20F in C", u"20°F = -6.6667°C"),
            (u"120K in celsius", u"120K = -153.15°C"),
            (u"20 degrees F in C", u"20°F = -6.6667°C"),
            (u"20 deg F in C", u"20°F = -6.6667°C"),
            (u"20C to f", u"20°C = 68°F"),
        ])

    def test_distance(self):
        self.check([
            (u"yards 1000 METERS", u"1000 meters = 1093.6133 yards"),
            (u"20 inches in ft", u"20 inches = 1.6667 feet"),
            (u"5 feet to in", u"5 feet = 60 inches"),
            (u"20 inches in foot", u"20 inches = 1.6667 feet"),
            (u"2 meter in cm", u"2 meters = 200 centimeters"),
        ])

    def test_area(self):
        self.check([
            (u"1000 sq feet to sq meter", u"1000 square feet = 92.903 square meters"),
            (u"1 are square meter", u"1 are = 100 square meters"),
            (u"100 hectare sq kilometer", u"100 hectares = 1 square kilometer"),
            (u"hectare 1 sq kilometer", u"1 square kilometer = 100 hectares"),
            (u"1 sq m in square cm", u"1 square meter = 10000 square centimeters"),
        ])

    def test_volume(self):
        self.check([
            (u"1m3 litres", u"1 cubic meter = 1000 litres"),
            (u"1 cubic meter litres", u"1 cubic meter = 1000 litres"),
            (u"1m³ litres", u"1 cubic meter = 1000 litres"),
            (u"25 floz in litres", u"25 US fluid ounces = 0.7393 litres"),
            (u"1 litre in cm**3", u"1 litre = 1000 cubic centimeters"),
            (u"1 cc ml", u"1 cubic centimeter = 1 millilitre"),
            (u"100 gallons litres", u"100 US gallons = 378.5412 litres"),
            (u".75 qts in flozs", u"0.75 quarts = 24 US fluid ounces"),
            (u"5 tsp to tbsp", u"5 US teaspoons = 1.6667 US tablespoons"),
            (u"1 tablespoons in a cup", u"1 US tablespoon = 0.0625 US cups"),
            (u"1 gal in pints", u"1 US gallon = 8 US pints"),
            (u"3 cups in floz", u"3 US cups = 24 US fluid ounces"),

            # this case can't be done until this issue is fixed:
            #   https://github.com/hgrecco/pint/issues/228
            # (u"1 bbl in pints", u"1 US beer barrel = 248 US pints"),
        ])

    def test_weight(self):
        self.check([
            (u"1t grams", u"1 metric ton = 1000000 grams"),
            (u"  1 ton grams", u"1 short ton = 907184.74 grams"),
            (u"1 tonne grams  ", u"1 metric ton = 1000000 grams"),
            (u"3lb in mg", u"3 pounds = 1360777.11 milligrams"),
            (u"250g pounds", u"250 grams = 0.5512 pounds"),
            (u"20 lbs in kg", u"20 pounds = 9.0718 kilograms"),
            (u"50 ounce lb", u"50 ounces = 3.125 pounds"),
        ])

    def test_time(self):
        self.check([
            (u"1 year days", u"1 year = 365.2422 days"),
            (u"5 days in sec", u"5 days = 432000 seconds"),
            (u"2200 hours in weeks", u"2200 hours = 13.0952 weeks"),
            (u"20h in minutes", u"20 hours = 1200 minutes"),
        ])

    def test_verbose_good_and_bad(self):
        self.check([
            (u"how much is 20 inches in FEET?", u"20 inches = 1.6667 feet"),
            (u"45°C in meters", None),
            (u"23 rabbits under pressure", None),
            (u"five yards in meters", None),
            (u"meters in inches", None),
            (u"around the world in 80 days", None),
            (u"50 shades of gray", None),
            (u"multimeters in yards", None),
            (u"1 sq magnolia in square cm", None),
        ])

    def test_not_only_ints(self):
        self.check([
            (u"20.0 inches in feet", u"20 inches = 1.6667 feet"),
            (u",7 meter in feet", u"0.7 meters = 2.2966 feet"),
            (u"1234e-2 inches in feet", u"12.34 inches = 1.0283 feet"),
            (u"1.23455e6 inches in feet", u"1234550 inches = 102879.1667 feet"),
        ])

    def test_special_square_cubic_marks(self):
        self.check([
            (u"10 ft**2 to m^2", u"10 square feet = 0.929 square meters"),
            (u"10 ft  **2 to m ^2", u"10 square feet = 0.929 square meters"),
            (u"10 ft** 2 to m^  2", u"10 square feet = 0.929 square meters"),
            (u"10 ft ** 2 to m  ^  2", u"10 square feet = 0.929 square meters"),
            (u"10 ft2 to sq m", u"10 square feet = 0.929 square meters"),
            (u"1m3 litres", u"1 cubic meter = 1000 litres"),
            (u"1m**3 litres", u"1 cubic meter = 1000 litres"),
            (u"1m** 3 litres", u"1 cubic meter = 1000 litres"),
            (u"1m **3 litres", u"1 cubic meter = 1000 litres"),
            (u"1m  ** 3 litres", u"1 cubic meter = 1000 litres"),
            (u"1m^3 litres", u"1 cubic meter = 1000 litres"),
            (u"1m ^ 3 litres", u"1 cubic meter = 1000 litres"),
            (u"1m^  3 litres", u"1 cubic meter = 1000 litres"),
            (u"1m ^3 litres", u"1 cubic meter = 1000 litres"),
        ])

    def test_multiword_units(self):
        self.check([
            (u"2 fluid ounce in litres", u"2 US fluid ounces = 0.0591 litres"),
            (u"2 fluid ounces in litres", u"2 US fluid ounces = 0.0591 litres"),
            (u"3 metric ton in kilograms", u"3 metric tons = 3000 kilograms"),
            (u"3 metric ton in metric ton", u"3 metric tons = 3 metric tons"),
        ])

    def test_dimensional_collision(self):
        self.check([
            (u".75 qts in ozs", u"0.75 quarts = 24 US fluid ounces"),
            (u"1 liter in ozs", u"1 litre = 33.814 US fluid ounces"),
            (u"1 liter in ounces", u"1 litre = 33.814 US fluid ounces"),
            (u"1y in weeks", u"1 year = 52.1775 weeks"),
            (u"1y in meters", u"1 yard = 0.9144 meters"),
            (u"1 year in m", u"1 year = 12 months"),
            (u"1y in m", None),  # it can be a combination of year/month or yard/meter
            (u"3c in floz", u"3 US cups = 24 US fluid ounces"),
            (u"150f in °C", u"150°F = 65.5556°C"),
            (u"150f in meters", u"150 feet = 45.72 meters"),
        ])

    def test_single_unit(self):
        self.check([
            (u"120 °f", u"120°F = 48.8889°C"),
            (u"27 celsius", u"27°C = 80.6°F"),
            (u"100 hectare", u"100 hectares = 0.3861 square miles"),
            (u" cm 20  ", u"20 centimeters = 7.874 inches"),
            (u"2 floz", u"2 US fluid ounces = 59.1471 millilitres"),
            (u"30 grams", u"30 grams = 1.0582 ounces"),
            (u"5h    ", u"5 hours = 18000 seconds"),
            (u"       3 tsp", u"3 US teaspoons = 14.7868 millilitres"),
            (u"20 yards", u"20 yards = 18.288 meters"),
        ])


class NumbersInfoTestCase(CheckingTestCase):
    """Check the basic functionality: simple conversions."""

    def test_simple_scales(self):
        data = [
            (100, 'meters', 'size', 'a monster'),
        ]
        with patch.object(unitconv, 'NUMBERS_INFO', data):
            self.check([
                (u"50", u"50 meters is about half of the size of a monster"),
                (u"60", u"60 meters is about half of the size of a monster"),
                (u"40", u"40 meters is about half of the size of a monster"),
                (u"1", None),
                (u"65", None),
                (u"100", u"100 meters is close to the size of a monster"),
                (u"90", u"90 meters is close to the size of a monster"),
                (u"110", u"110 meters is close to the size of a monster"),
                (u"80", None),
                (u"130", None),
                (u"180", u"180 meters is around 2 times the size of a monster"),
                (u"580", u"580 meters is around 6 times the size of a monster"),
                (u"839", u"839 meters is around 8 times the size of a monster"),
                (u"7800", u"7800 meters is around 78 times the size of a monster"),
                (u"17800", None),
            ])

    def test_approximation(self):
        data = [
            (10, 'inches', 'height', 'a gremlin'),
            (100, 'meters', 'size', 'a monster'),
        ]
        with patch.object(unitconv, 'NUMBERS_INFO', data):
            with patch.object(unitconv, 'NUMBERS_UNCERTAINTY', 1):  # no random behaviour
                self.check([
                    (u"10", u"10 inches is close to the height of a gremlin"),
                    (u"30", u"30 inches is around 3 times the height of a gremlin"),
                    (u"40", u"40 meters is about half of the size of a monster"),
                ])

    def test_random_choice(self):
        assert unitconv.NUMBERS_UNCERTAINTY == 3
        data = [
            (89, 'unit1', 'dim1', 'targ1'),   # close to unity
            (12, 'unit2', 'dim2', 'targ2'),   # multiple, far away
            (90, 'unit3', 'dim3', 'targ3'),   # even closer to unity
            (180, 'unit4', 'dim4', 'targ4'),  # half, not close, not very far
        ]
        with patch.object(unitconv, 'NUMBERS_INFO', data):
            with patch.object(random, 'choice') as mock_choice:
                mock_choice.side_effect = lambda values: values[0]
                self.check([
                    (u"95", u"95 unit3 is close to the dim3 of targ3"),
                ])

        # check it was called with the top 3 of the possible choices,
        # ordered by distance
        calls = mock_choice.mock_calls[0][1][0]
        self.assertEqual(calls, [
            u"95 unit3 is close to the dim3 of targ3",
            u"95 unit1 is close to the dim1 of targ1",
            u"95 unit4 is about half of the dim4 of targ4",
        ])

    def test_number_only(self):
        data = [
            (100, 'meters', 'size', 'a monster'),
        ]
        with patch.object(unitconv, 'NUMBERS_INFO', data):
            self.check([
                (u"stuff 100 ", None),
                (u"100 chanchos", None),
                (u"100x", None),
                (u"100   ", u"100 meters is close to the size of a monster"),
                (u" 100", u"100 meters is close to the size of a monster"),
            ])

    def test_unicode(self):
        data = [
            (100, u'°C', u'temperature', u'boiling water'),
        ]
        with patch.object(unitconv, 'NUMBERS_INFO', data):
            self.check([
                (u"200", u"200 °C is around 2 times the temperature of boiling water"),
            ])
