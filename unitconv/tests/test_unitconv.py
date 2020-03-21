# Copyright 2010-2018 Canonical Ltd.
# Copyright 2020 Facundo Batista
# All Rights Reserved

"""Tests for the units converter."""

import logging
import random
from io import StringIO
from unittest import TestCase

from mock import patch

import unitconv

# store the logged globally to use when any of the check fail
_l = unitconv.logger
_l.setLevel(logging.DEBUG)
stored_logging = StringIO()
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
            ("45°C in fahrenheit", "45°C = 113°F"),
            ("20F in C", "20°F = -6.6667°C"),
            ("120K in celsius", "120K = -153.15°C"),
            ("20 degrees F in C", "20°F = -6.6667°C"),
            ("20 deg F in C", "20°F = -6.6667°C"),
            ("20C to f", "20°C = 68°F"),
        ])

    def test_distance(self):
        self.check([
            ("yards 1000 METERS", "1000 meters = 1093.6133 yards"),
            ("20 inches in ft", "20 inches = 1.6667 feet"),
            ("5 feet to in", "5 feet = 60 inches"),
            ("20 inches in foot", "20 inches = 1.6667 feet"),
            ("2 meter in cm", "2 meters = 200 centimeters"),
        ])

    def test_area(self):
        self.check([
            ("1000 sq feet to sq meter", "1000 square feet = 92.903 square meters"),
            ("1 are square meter", "1 are = 100 square meters"),
            ("100 hectare sq kilometer", "100 hectares = 1 square kilometer"),
            ("hectare 1 sq kilometer", "1 square kilometer = 100 hectares"),
            ("1 sq m in square cm", "1 square meter = 10000 square centimeters"),
        ])

    def test_volume(self):
        self.check([
            ("1m3 litres", "1 cubic meter = 1000 litres"),
            ("1 cubic meter litres", "1 cubic meter = 1000 litres"),
            ("1m³ litres", "1 cubic meter = 1000 litres"),
            ("25 floz in litres", "25 US fluid ounces = 0.7393 litres"),
            ("1 litre in cm**3", "1 litre = 1000 cubic centimeters"),
            ("1 cc ml", "1 cubic centimeter = 1 millilitre"),
            ("100 gallons litres", "100 US gallons = 378.5412 litres"),
            (".75 qts in flozs", "0.75 quarts = 24 US fluid ounces"),
            ("5 tsp to tbsp", "5 US teaspoons = 1.6667 US tablespoons"),
            ("1 tablespoons in a cup", "1 US tablespoon = 0.0625 US cups"),
            ("1 gal in pints", "1 US gallon = 8 US pints"),
            ("3 cups in floz", "3 US cups = 24 US fluid ounces"),

            # this case can't be done until this issue is fixed:
            #   https://github.com/hgrecco/pint/issues/228
            # ("1 bbl in pints", "1 US beer barrel = 248 US pints"),
        ])

    def test_weight(self):
        self.check([
            ("1t grams", "1 metric ton = 1000000 grams"),
            ("  1 ton grams", "1 short ton = 907184.74 grams"),
            ("1 tonne grams  ", "1 metric ton = 1000000 grams"),
            ("3lb in mg", "3 pounds = 1360777.11 milligrams"),
            ("250g pounds", "250 grams = 0.5512 pounds"),
            ("20 lbs in kg", "20 pounds = 9.0718 kilograms"),
            ("50 ounce lb", "50 ounces = 3.125 pounds"),
        ])

    def test_time(self):
        self.check([
            ("1 year days", "1 year = 365.25 days"),
            ("5 days in sec", "5 days = 432000 seconds"),
            ("2200 hours in weeks", "2200 hours = 13.0952 weeks"),
            ("20h in minutes", "20 hours = 1200 minutes"),
        ])

    def test_verbose_good_and_bad(self):
        self.check([
            ("how much is 20 inches in FEET?", "20 inches = 1.6667 feet"),
            ("45°C in meters", None),
            ("23 rabbits under pressure", None),
            ("five yards in meters", None),
            ("meters in inches", None),
            ("around the world in 80 days", None),
            ("50 shades of gray", None),
            ("multimeters in yards", None),
            ("1 sq magnolia in square cm", None),
        ])

    def test_not_only_ints(self):
        self.check([
            ("20.0 inches in feet", "20 inches = 1.6667 feet"),
            (",7 meter in feet", "0.7 meters = 2.2966 feet"),
            ("1234e-2 inches in feet", "12.34 inches = 1.0283 feet"),
            ("1.23455e6 inches in feet", "1234550 inches = 102879.1667 feet"),
        ])

    def test_special_square_cubic_marks(self):
        self.check([
            ("10 ft**2 to m^2", "10 square feet = 0.929 square meters"),
            ("10 ft  **2 to m ^2", "10 square feet = 0.929 square meters"),
            ("10 ft** 2 to m^  2", "10 square feet = 0.929 square meters"),
            ("10 ft ** 2 to m  ^  2", "10 square feet = 0.929 square meters"),
            ("10 ft2 to sq m", "10 square feet = 0.929 square meters"),
            ("1m3 litres", "1 cubic meter = 1000 litres"),
            ("1m**3 litres", "1 cubic meter = 1000 litres"),
            ("1m** 3 litres", "1 cubic meter = 1000 litres"),
            ("1m **3 litres", "1 cubic meter = 1000 litres"),
            ("1m  ** 3 litres", "1 cubic meter = 1000 litres"),
            ("1m^3 litres", "1 cubic meter = 1000 litres"),
            ("1m ^ 3 litres", "1 cubic meter = 1000 litres"),
            ("1m^  3 litres", "1 cubic meter = 1000 litres"),
            ("1m ^3 litres", "1 cubic meter = 1000 litres"),
        ])

    def test_multiword_units(self):
        self.check([
            ("2 fluid ounce in litres", "2 US fluid ounces = 0.0591 litres"),
            ("2 fluid ounces in litres", "2 US fluid ounces = 0.0591 litres"),
            ("3 metric ton in kilograms", "3 metric tons = 3000 kilograms"),
            ("3 metric ton in metric ton", "3 metric tons = 3 metric tons"),
        ])

    def test_dimensional_collision(self):
        self.check([
            (".75 qts in ozs", "0.75 quarts = 24 US fluid ounces"),
            ("1 liter in ozs", "1 litre = 33.814 US fluid ounces"),
            ("1 liter in ounces", "1 litre = 33.814 US fluid ounces"),
            ("1y in weeks", "1 year = 52.1786 weeks"),
            ("1y in meters", "1 yard = 0.9144 meters"),
            ("1 year in m", "1 year = 12 months"),
            ("1y in m", None),  # it can be a combination of year/month or yard/meter
            ("3c in floz", "3 US cups = 24 US fluid ounces"),
            ("150f in °C", "150°F = 65.5556°C"),
            ("150f in meters", "150 feet = 45.72 meters"),
        ])

    def test_single_unit(self):
        self.check([
            ("120 °f", "120°F = 48.8889°C"),
            ("27 celsius", "27°C = 80.6°F"),
            ("100 hectare", "100 hectares = 0.3861 square miles"),
            (" cm 20  ", "20 centimeters = 7.874 inches"),
            ("2 floz", "2 US fluid ounces = 59.1471 millilitres"),
            ("30 grams", "30 grams = 1.0582 ounces"),
            ("5h    ", "5 hours = 18000 seconds"),
            ("       3 tsp", "3 US teaspoons = 14.7868 millilitres"),
            ("20 yards", "20 yards = 18.288 meters"),
        ])


class NumbersInfoTestCase(CheckingTestCase):
    """Check the basic functionality: simple conversions."""

    def test_simple_scales(self):
        data = [
            (100, 'meters', 'size', 'a monster'),
        ]
        with patch.object(unitconv, 'NUMBERS_INFO', data):
            self.check([
                ("50", "50 meters is about half of the size of a monster"),
                ("60", "60 meters is about half of the size of a monster"),
                ("40", "40 meters is about half of the size of a monster"),
                ("1", None),
                ("65", None),
                ("100", "100 meters is close to the size of a monster"),
                ("90", "90 meters is close to the size of a monster"),
                ("110", "110 meters is close to the size of a monster"),
                ("80", None),
                ("130", None),
                ("180", "180 meters is around 2 times the size of a monster"),
                ("580", "580 meters is around 6 times the size of a monster"),
                ("839", "839 meters is around 8 times the size of a monster"),
                ("7800", "7800 meters is around 78 times the size of a monster"),
                ("17800", None),
            ])

    def test_approximation(self):
        data = [
            (10, 'inches', 'height', 'a gremlin'),
            (100, 'meters', 'size', 'a monster'),
        ]
        with patch.object(unitconv, 'NUMBERS_INFO', data):
            with patch.object(unitconv, 'NUMBERS_UNCERTAINTY', 1):  # no random behaviour
                self.check([
                    ("10", "10 inches is close to the height of a gremlin"),
                    ("30", "30 inches is around 3 times the height of a gremlin"),
                    ("40", "40 meters is about half of the size of a monster"),
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
                    ("95", "95 unit3 is close to the dim3 of targ3"),
                ])

        # check it was called with the top 3 of the possible choices,
        # ordered by distance
        calls = mock_choice.mock_calls[0][1][0]
        self.assertEqual(calls, [
            "95 unit3 is close to the dim3 of targ3",
            "95 unit1 is close to the dim1 of targ1",
            "95 unit4 is about half of the dim4 of targ4",
        ])

    def test_number_only(self):
        data = [
            (100, 'meters', 'size', 'a monster'),
        ]
        with patch.object(unitconv, 'NUMBERS_INFO', data):
            self.check([
                ("stuff 100 ", None),
                ("100 chanchos", None),
                ("100x", None),
                ("100   ", "100 meters is close to the size of a monster"),
                (" 100", "100 meters is close to the size of a monster"),
            ])

    def test_unicode(self):
        data = [
            (100, '°C', 'temperature', 'boiling water'),
        ]
        with patch.object(unitconv, 'NUMBERS_INFO', data):
            self.check([
                ("200", "200 °C is around 2 times the temperature of boiling water"),
            ])
