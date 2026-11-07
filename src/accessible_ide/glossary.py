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
# Each section may also carry an `example`: a short program the reader can
# copy into the editor and run. It is plain Python, shown with syntax
# highlighting and a copy button.
SECTIONS = (
    {
        'title': 'Printing',
        'note': 'print() shows something on the screen.',
        'rows': (
            ('`print("Hello")`', 'Show text on the screen.'),
            ('`print(5)`', 'Show a number.'),
            ('`print("Hi", name)`', 'Show several things at once.'),
        ),
        'example': 'print("Hello, world!")\nprint("Counting:", 1, 2, 3)',
    },
    {
        'title': 'Comments',
        'note': 'Text after # is ignored by Python.',
        'rows': (
            ('`# a comment`', 'Text after # is ignored by Python.'),
            ('`# print("not run")`', 'You can comment out code to stop it running.'),
        ),
        'example': '# This line is ignored\nprint("This runs")  # and this comment too',
    },
    {
        'title': 'Variables',
        'note': '`=` saves a value under a name. Variable names cannot start with a number and cannot have spaces.',
        'rows': (
            ('`x = 5`', 'Save the number 5 as x.'),
            ('`name = "Ana"`', 'Save text as name.'),
            ('`x, y = 5, 6`', 'Assign two values at the same time.'),
            ('`x = y = 7`', 'Assign the same value to two names.'),
            ('`type(5)`', 'Find out the type of a value.'),
            ('`int`', 'Whole numbers like 1, 2, 3.'),
            ('`float`', 'Numbers with a decimal point like 3.5.'),
            ('`str`', 'Text like "hello".'),
            ('`bool`', 'True or False.'),
            ('`list`', 'A collection in order.'),
            ('`int("5")`', 'Turn text into an integer.'),
            ('`str(5)`', 'Turn a number into text.'),
        ),
        'example': 'x = 5\nname = "Ana"\nprint(type(x), type(name))\nprint(int("5") + 1)',
    },
    {
        'title': 'User input',
        'note': 'Ask the user a question and get their answer.',
        'rows': (
            ('`name = input("What is your name? ")`', 'Ask for input and save it as text.'),
            ('`age = int(input("How old are you? "))`', 'Get input and turn it into a number.'),
            ('`print("Hi", name)`', 'Use the answer.'),
        ),
        'example': 'name = input("What is your name? ")\nprint("Hello", name)',
    },
    {
        'title': 'Numbers and math',
        'note': 'Numbers and the signs that work on them.',
        'rows': (
            ('`x = 5`', 'An integer.'),
            ('`y = 3.14`', 'A float.'),
            ('`x + y`', 'Add numbers together.'),
            ('`x - y`', 'Subtract numbers.'),
            ('`x * y`', 'Multiply numbers.'),
            ('`x / y`', 'Divide numbers.'),
            ('`x // y`', 'Divide and keep the whole number.'),
            ('`x % y`', 'Get the remainder (modulus).'),
            ('`x ** y`', 'Raise to a power.'),
            ('`abs(-5)`', 'Get the absolute value.'),
            ('`round(3.14159, 2)`', 'Round to 2 decimal places.'),
        ),
        'example': 'x = 5\ny = 3.14\nprint(x + y, x - y, x * y)\nprint(x % 2, x ** 2)\nprint(round(3.14159, 2))',
    },
    {
        'title': 'Booleans and comparisons',
        'note': 'Values that are True or False, and the signs that compare.',
        'rows': (
            ('`True`', 'A true value.'),
            ('`False`', 'A false value.'),
            ('`5 > 3`', 'Compare values to get True or False.'),
            ('`5 == 5`', 'Check if two values are equal.'),
            ('`5 != 3`', 'Check if two values are not equal.'),
            ('`5 >= 3`', 'Greater than or equal.'),
            ('`5 <= 3`', 'Less than or equal.'),
            ('`and or not`', 'Logical operators.'),
        ),
        'example': 'age = 14\nprint(age > 10 and age < 20)\nprint(age == 14, age != 5)',
    },
    {
        'title': 'Making decisions',
        'note': 'Run code only when a condition is True or False.',
        'rows': (
            ('`if x > 5:`', 'Run if condition is True.'),
            ('`elif x == 5:`', 'Run if previous was False and this is True.'),
            ('`else:`', 'Run if all conditions are False.'),
            ('`if x > 5 and x < 10:`', 'Combine conditions.'),
            ('`if x > 5 or x < 2:`', 'Either condition can be True.'),
        ),
        'example': 'x = 7\nif x > 5:\n    print("big")\nelif x == 5:\n    print("five")\nelse:\n    print("small")',
    },
    {
        'title': 'Loops',
        'note': 'Run code more than once.',
        'rows': (
            ('`while x < 5:`', 'Repeat while condition is True.'),
            ('`    x += 1`', 'Change something so the loop ends.'),
            ('`for i in range(3):`', 'Loop three times.'),
            ('`for fruit in fruits:`', 'Loop through each item in a list.'),
            ('`break`', 'Leave the loop.'),
            ('`continue`', 'Skip to the next item.'),
        ),
        'example': 'for i in range(3):\n    print("Counting:", i)\n\nx = 0\nwhile x < 3:\n    print("While:", x)\n    x += 1',
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
        'example': 'def greet(name):\n    return "Hello " + name\n\nprint(greet("Ana"))',
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
        'example': 'fruits = ["apple", "pear"]\nfruits.append("plum")\nprint(fruits, len(fruits))\nfruits.remove("pear")\nprint(fruits)',
    },
    {
        'title': 'Formatting',
        'note': 'Format text and numbers.',
        'rows': (
            ('`"Hello {}".format("Ana")`', 'Format with curly braces.'),
            ('`f"Hello {name}"`', 'Format with f strings.'),
            ('`round(3.14159, 2)`', 'Round to 2 decimal places.'),
            ('`"{:.2f}".format(3.14159)`', 'Format to 2 decimal places.'),
            ('`format(3.14159, ".3g")`', 'Format to 3 significant figures.'),
        ),
        'example': 'pi = 3.14159\nprint(round(pi, 2))\nprint(f"{pi:.2f}")\nprint(format(pi, ".3g"))',
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
