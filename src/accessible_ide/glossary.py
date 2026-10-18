"""The Python dictionary: the glossary the README has always carried.

The README has had a Python dictionary since the first release, and its
opening line makes a promise a README cannot keep: that each entry shows
something you can type into the editor. It also cannot be read in the font
the reader chose, because a README is rendered by whatever browser or code
host is showing it, not by this app.

So the same entries are served from here and drawn inside the app, in a
dialog, in the reader's own font at the size and line spacing they set. A
reader who meets an unfamiliar word halfway through a line can look it up
without leaving the window they are working in.

The words are the README's words, unchanged. tests/test_glossary.py reads
that table back out of the Markdown and fails if the two ever disagree, so
neither copy can drift away from the other in silence.

Why these entries are not translation keys
------------------------------------------
Every other visible word in this app comes from an i18n catalogue. These do
not, deliberately, for now.

A label is short enough that a wrong translation announces itself. An entry
here is a whole explanation of Python in a learner's second language, and a
reader has no way to tell a careful translation from a plausible wrong one,
which is exactly the failure mode a plain-English feature exists to avoid.
Shipping English and saying so on the screen is an honest state. Once
speakers have reviewed the entries they move into the catalogues like every
other string, which is why the dialog states which language it is in.
"""

from markupsafe import Markup, escape

# A row is (what you type, what it means), taken verbatim from the README's
# table cells, backticks included. The backticks are the only markup in the
# text: inline_code turns each pair into a <code> element, so the entries read
# the same in the app as they do in the Markdown.
#
# Straight apostrophes and no em dashes, matching the rest of the app's copy.
SECTIONS = (
    {
        'title': 'Introduction and getting started',
        'note': 'Python is a programming language you can type and run straight away.',
        'rows': (
            ('`python --version`', 'Check which version of Python is installed.'),
            ('`python script.py`', 'Run a Python file from the command line.'),
            ('`print()`', 'Show something on the screen.'),
        ),
    },
    {
        'title': 'Syntax',
        'note': 'Python reads spaces at the start of a line to know how things belong together.',
        'rows': (
            ('`if x == 5:`', 'A line that ends with a colon starts a new block.'),
            ('`    print(x)`', 'Indented lines belong to the block above them.'),
            ('`# a comment`', 'Text after `#` is ignored by Python.'),
        ),
    },
    {
        'title': 'Comments',
        'note': '',
        'rows': (
            ('`# This is a comment`', 'Python ignores this line.'),
            ('`# print("not run")`', 'You can comment out code to stop it running.'),
        ),
    },
    {
        'title': 'Variables',
        'note': '`=` saves a value under a name. Variable names cannot start with a number and cannot have spaces.',
        'rows': (
            ('`x = 5`', 'Save the number 5 as x.'),
            ('`name = "Ana"`', 'Save text as name.'),
            ('`x, y = 5, 6`', 'Assign two values at the same time.'),
            ('`x = y = 7`', 'Assign the same value to two names.'),
        ),
    },
    {
        'title': 'Data types',
        'note': 'Python works out the type from the value you save.',
        'rows': (
            ('`type(5)`', 'Find out the type of a value.'),
            ('`int`', 'Whole numbers like 1, 2, 3.'),
            ('`float`', 'Numbers with a decimal point like 3.5.'),
            ('`str`', 'Text like "hello".'),
            ('`bool`', 'True or False.'),
            ('`list`', 'A collection in order.'),
            ('`tuple`', 'A collection that cannot be changed.'),
            ('`set`', 'A collection with no duplicates.'),
            ('`dict`', 'Values saved under keys.'),
        ),
    },
    {
        'title': 'Numbers',
        'note': '',
        'rows': (
            ('`x = 5`', 'An integer.'),
            ('`y = 3.14`', 'A float.'),
            ('`x + y`', 'Add numbers together.'),
            ('`x - y`', 'Subtract numbers.'),
            ('`x * y`', 'Multiply numbers.'),
            ('`x / y`', 'Divide numbers.'),
            ('`x // y`', 'Divide and keep the whole number.'),
            ('`x % y`', 'Get the remainder.'),
            ('`x ** y`', 'Raise to a power.'),
        ),
    },
    {
        'title': 'Casting',
        'note': 'Turn one type of value into another.',
        'rows': (
            ('`int("5")`', 'Turn text into an integer.'),
            ('`float("3.5")`', 'Turn text into a float.'),
            ('`str(5)`', 'Turn a number into text.'),
            ('`bool(0)`', 'Turn a value into True or False.'),
        ),
    },
    {
        'title': 'Strings',
        'note': '',
        'rows': (
            ('`"hello".upper()`', 'Make all letters uppercase.'),
            ('`"HELLO".lower()`', 'Make all letters lowercase.'),
            ('`len("hello")`', 'Get the length of text.'),
            ('`"hello"[0]`', 'Get the first character.'),
            ('`"hello" in "hello world"`', 'Check if text contains something.'),
            ('`"a,b".split(",")`', 'Split text into a list.'),
            ('`"a".replace("a","b")`', 'Replace part of the text.'),
        ),
    },
    {
        'title': 'Booleans',
        'note': '',
        'rows': (
            ('`True`', 'A true value.'),
            ('`False`', 'A false value.'),
            ('`5 > 3`', 'Compare values to get True or False.'),
            ('`5 == 5`', 'Check if two values are equal.'),
            ('`5 != 3`', 'Check if two values are not equal.'),
            ('`bool("hello")`', 'Most values become True. Zero and empty become False.'),
        ),
    },
    {
        'title': 'Operators',
        'note': '',
        'rows': (
            ('`+ - * /`', 'Arithmetic operators.'),
            ('`== != < > <= >=`', 'Comparison operators.'),
            ('`and or not`', 'Logical operators.'),
            ('`in not in`', 'Membership operators.'),
            ('`is is not`', 'Identity operators.'),
        ),
    },
    {
        'title': 'Lists',
        'note': 'Lists hold values in order and can be changed.',
        'rows': (
            ('`fruits = ["apple", "pear"]`', 'Create a list.'),
            ('`fruits[0]`', 'Get the first item.'),
            ('`len(fruits)`', 'Get how many items.'),
            ('`fruits.append("plum")`', 'Add an item to the end.'),
            ('`fruits.remove("pear")`', 'Remove an item.'),
            ('`fruits[0] = "banana"`', 'Change an item.'),
            ('`fruits.pop()`', 'Remove the last item.'),
        ),
    },
    {
        'title': 'Tuples',
        'note': 'Tuples hold values in order but cannot be changed.',
        'rows': (
            ('`colors = ("red", "blue")`', 'Create a tuple.'),
            ('`colors[0]`', 'Get the first item.'),
            ('`len(colors)`', 'Get how many items.'),
            ('`"red" in colors`', 'Check if an item is in the tuple.'),
        ),
    },
    {
        'title': 'Sets',
        'note': 'Sets hold values with no duplicates and no set order.',
        'rows': (
            ('`nums = {1, 2, 3}`', 'Create a set.'),
            ('`nums.add(4)`', 'Add an item.'),
            ('`nums.remove(1)`', 'Remove an item.'),
            ('`len(nums)`', 'Get how many items.'),
            ('`1 in nums`', 'Check if an item is in the set.'),
        ),
    },
    {
        'title': 'Dictionaries',
        'note': 'Dictionaries save values under keys.',
        'rows': (
            ('`me = {"name": "Ana", "age": 14}`', 'Create a dictionary.'),
            ('`me["name"]`', 'Get a value by key.'),
            ('`me["age"] = 15`', 'Change a value.'),
            ('`me["city"] = "Paris"`', 'Add a new key and value.'),
            ('`me.keys()`', 'Get all keys.'),
            ('`me.values()`', 'Get all values.'),
            ('`len(me)`', 'Get how many key value pairs.'),
        ),
    },
    {
        'title': 'If...Else',
        'note': 'Run code only when a condition is True or False.',
        'rows': (
            ('`if x > 5:`', 'Run if condition is True.'),
            ('`elif x == 5:`', 'Run if previous was False and this is True.'),
            ('`else:`', 'Run if all conditions are False.'),
            ('`if x > 5 and x < 10:`', 'Combine conditions.'),
            ('`if x > 5 or x < 2:`', 'Either condition can be True.'),
        ),
    },
    {
        'title': 'Match',
        'note': 'Compare a value against several patterns. Available in Python 3.10 and later.',
        'rows': (
            ('`match day:`', 'Start a match statement.'),
            ('`  case "Mon":`', 'Run if day matches this pattern.'),
            ('`    print("start")`', 'Code to run for this case.'),
            ('`  case _:`', 'A default case when nothing matches.'),
        ),
    },
    {
        'title': 'While loops',
        'note': 'Keep running code while a condition is True.',
        'rows': (
            ('`while x < 5:`', 'Repeat while condition is True.'),
            ('`    x += 1`', 'Change something so the loop ends.'),
            ('`break`', 'Leave the loop straight away.'),
            ('`continue`', 'Skip the rest of this round and go to the next.'),
        ),
    },
    {
        'title': 'For loops',
        'note': 'Loop through a sequence of items.',
        'rows': (
            ('`for i in range(3):`', 'Loop three times.'),
            ('`for fruit in fruits:`', 'Loop through each item in a list.'),
            ('`for c in "abc":`', 'Loop through each character in text.'),
            ('`break`', 'Leave the loop.'),
            ('`continue`', 'Skip to the next item.'),
        ),
    },
    {
        'title': 'Functions',
        'note': 'Group code together and reuse it by name.',
        'rows': (
            ('`def greet():`', 'Define a function with no input.'),
            ('`    print("hi")`', 'Code that runs when called.'),
            ('`greet()`', 'Call the function.'),
            ('`def greet(name):`', 'Define a function that takes an input.'),
            ('`    return name`', 'Return a value from the function.'),
            ('`greet("Ana")`', 'Call with an argument.'),
        ),
    },
    {
        'title': 'Range',
        'note': '`range()` gives a sequence of numbers to use in loops.',
        'rows': (
            ('`range(5)`', 'Numbers from 0 up to but not including 5.'),
            ('`range(1, 5)`', 'Numbers from 1 up to but not including 5.'),
            ('`range(1, 10, 2)`', 'Numbers from 1 stepping by 2.'),
            ('`list(range(5))`', 'Turn range into a list to see the numbers.'),
        ),
    },
    {
        'title': 'Arrays',
        'note': 'Python has lists. Some libraries also use arrays for numbers.',
        'rows': (
            ('`nums = [1, 2, 3]`', 'Create a list to hold numbers.'),
            ('`len(nums)`', 'Get the number of items.'),
            ('`nums.append(4)`', 'Add a new number.'),
            ('`nums[0] = 0`', 'Change a number.'),
        ),
    },
    {
        'title': 'Iterators',
        'note': 'An iterator lets you go through items one by one.',
        'rows': (
            ('`fruits = ["apple", "pear"]`', 'A list is iterable.'),
            ('`it = iter(fruits)`', 'Get an iterator from the list.'),
            ('`next(it)`', 'Get the next item.'),
            ('`for fruit in fruits:`', 'A for loop uses iterators behind the scenes.'),
        ),
    },
    {
        'title': 'Modules',
        'note': 'Modules let you reuse code from other files or built in tools.',
        'rows': (
            ('`import math`', 'Import a module.'),
            ('`math.sqrt(16)`', 'Use something from the module.'),
            ('`from math import sqrt`', 'Import just one thing.'),
            ('`import random`', 'Another common module.'),
            ('`random.randint(1, 10)`', 'Get a random number.'),
        ),
    },
    {
        'title': 'Dates',
        'note': '',
        'rows': (
            ('`from datetime import datetime`', 'Import the datetime tools.'),
            ('`datetime.now()`', 'Get the current date and time.'),
            ('`datetime.now().year`', 'Get just the year.'),
            ('`datetime.now().strftime("%Y-%m-%d")`', 'Format the date as text.'),
        ),
    },
    {
        'title': 'Math',
        'note': '',
        'rows': (
            ('`import math`', 'Import math tools.'),
            ('`math.pi`', 'Get pi.'),
            ('`math.sqrt(25)`', 'Get the square root.'),
            ('`math.ceil(3.2)`', 'Round up.'),
            ('`math.floor(3.8)`', 'Round down.'),
            ('`abs(-5)`', 'Get the absolute value.'),
        ),
    },
    {
        'title': 'JSON',
        'note': 'Work with JSON data in Python.',
        'rows': (
            ('`import json`', 'Import the json module.'),
            ('`data = {"name": "Ana"}`', 'Python dictionary.'),
            ('`json.dumps(data)`', 'Turn a dictionary into JSON text.'),
            ('`json.loads("{\\"name\\": \\"Ana\\"}")`', 'Turn JSON text into a Python dictionary.'),
        ),
    },
    {
        'title': 'RegEx',
        'note': 'Search and match text patterns.',
        'rows': (
            ('`import re`', 'Import the re module.'),
            ('`re.search("a", "apple")`', 'Search for a pattern.'),
            ('`re.findall("a", "apple")`', 'Find all matches.'),
            ('`re.match("a", "apple")`', 'Match at the start of text.'),
            ('`re.sub("a", "b", "apple")`', 'Replace matches.'),
        ),
    },
    {
        'title': 'Try...Except',
        'note': 'Handle errors so your program does not crash.',
        'rows': (
            ('`try:`', 'Try to run code that might cause an error.'),
            ('`    x = int("abc")`', 'This will cause an error.'),
            ('`except ValueError:`', 'Run this if a ValueError happens.'),
            ('`    print("not a number")`', 'Show a friendly message.'),
            ('`else:`', 'Run this if no error happened.'),
            ('`finally:`', 'Run this no matter what.'),
        ),
    },
    {
        'title': 'String formatting',
        'note': '',
        'rows': (
            ('`"Hello {}".format("Ana")`', 'Format with curly braces.'),
            ('`f"Hello {name}"`', 'Format with f strings.'),
            ('`"Hello %s" % "Ana"`', 'Format with percent signs.'),
            ('`"{0} {1}".format("Hello", "Ana")`', 'Format with numbered placeholders.'),
        ),
    },
    {
        'title': 'User input',
        'note': 'Ask the user a question and get their answer.',
        'rows': (
            ('`name = input("What is your name? ")`', 'Ask for input and save it as text.'),
            ('`age = int(input("How old are you? "))`', 'Get input and turn it into a number.'),
            ('`print("Hi", name)`', 'Use the answer.'),
        ),
    },
)


def inline_code(text):
    """Turn paired backticks into <code>, escaping everything else.

    Escaping happens first and the tag is inserted after, so an entry can
    never introduce markup of its own. The entries are ours rather than a
    reader's, but the ordering costs nothing and means this stays safe if a
    reader-supplied string is ever put through it.
    """
    parts = escape(text).split('`')
    if len(parts) == 1:
        return Markup(parts[0])
    out = []
    for index, part in enumerate(parts):
        # Odd indexes sit between a pair of backticks. Every entry in this file
        # has them in pairs, which test_glossary asserts, so an odd count would
        # be a mistake in the data rather than something this has to render
        # well. If one ever got through, the unmatched tail is wrapped rather
        # than dropped, which is the harmless way round: a reader would see a
        # stray backtick, not lose the end of the entry.
        if index % 2:
            out.append(f'<code>{part}</code>')
        else:
            out.append(str(part))
    return Markup(''.join(out))


def entry_count():
    """How many entries the dialog holds. Used by the status line and tests."""
    return sum(len(section['rows']) for section in SECTIONS)
