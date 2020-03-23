What is unitconv?
-----------------

A units converter that understands a lot of written queries and produce
a nice human response::

    >>> import unitconv
    >>> unitconv.convert("3 meters in cm")
    '3 meters = 300 centimeters'

    >>> unitconv.convert("1000 grams in kg")
    '1000 grams = 1 kilogram'

    >>> unitconv.convert("2 cups to l")
    '2 US cups = 0.4732 litres'

    >>> print unitconv.convert("300 yards")
    300 yards = 274.32 meters

    >>> unitconv.convert("34 days in weeks")
    '34 days = 4.8571 weeks'

    >>> unitconv.convert("45mg in ounces")
    '45 milligrams = 0.0016 ounces'

    >>> print unitconv.convert("300K in °f")
    300K = 80.33°F

    >>> unitconv.convert("50 cubic feet in m3")
    '50 cubic feet = 1.4158 cubic meters'

    >>> unitconv.convert("2 cups in l")
    '2 US cups = 0.4732 litres'

    >>> unitconv.convert("4 teaspoons")
    '4 US teaspoons = 19.7157 millilitres'

You can also use it as a script::

    $ unitconv 42 km to miles
    42 kilometers = 26.0976 miles


Project's history
-----------------

Code here comes from other internal Canonical's project, this part was 
opensourced in 2018:

    https://launchpad.net/unitconv

I forked that to bring it to GitHub, migrate it to Python 3, shape it more
like a project (have a ``setup.py``, etc.), and do some releases.
