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
        'title': 'Saving a value under a name',
        'note': '`=` saves a value. `==` compares two values. Mixing them up '
                'is the most common first mistake.',
        'rows': (
            ('`age = 14`',
             'Saves a value under a name so you can use it again later.'),
            ('`age = age + 1`',
             'Works out the right side first, then saves the answer.'),
            ('`age += 1`',
             'The short way of writing the line above.'),
        ),
    },
    {
        'title': 'Saying something and reading an answer',
        'note': '',
        'rows': (
            ('`print("hello")`', 'Puts something on the screen.'),
            ('`input("How old are you? ")`',
             'Asks a question and hands back the answer as text. The program '
             'pauses here, a box appears for the answer, and it carries on '
             'when you send it.'),
            ('`type(3.5)`', 'Tells you what kind of value something is.'),
        ),
    },
    {
        'title': 'Turning one kind of value into another',
        'note': '',
        'rows': (
            ('`int("12")`',
             'Makes a whole number out of text. `int(3.9)` gives `3`.'),
            ('`float("3.5")`', 'Makes a decimal number out of text.'),
            ('`str(12)`', 'Makes text out of anything.'),
        ),
    },
    {
        'title': 'Sums',
        'note': '',
        'rows': (
            ('`+` `-` `*` `/`', 'Add, subtract, multiply, divide.'),
            ('`7 // 2`', 'Divides and keeps the whole number only: `3`.'),
            ('`7 % 2`', 'The remainder after dividing: `1`.'),
            ('`2 ** 3`', 'Powers: `8`.'),
            ('`round(3.6)`', 'Rounds to the nearest whole number: `4`.'),
        ),
    },
    {
        'title': 'Comparing two values',
        'note': '',
        'rows': (
            ('`==`', 'Are these two the same?'),
            ('`!=`', 'Are these two different?'),
            ('`<` `>` `<=` `>=`',
             'Smaller, bigger, smaller or equal, bigger or equal.'),
            ('`and` `or` `not`', 'Joins True and False answers together.'),
        ),
    },
    {
        'title': 'Doing something only sometimes',
        'note': '',
        'rows': (
            ('`if age >= 13:`',
             'Does the lines below only when the answer is True. Note the '
             'colon at the end.'),
            ('`elif age == 12:`',
             'A second check to try when the first one was False.'),
            ('`else:`', 'What to do when none of the checks worked.'),
        ),
    },
    {
        'title': 'Doing something more than once',
        'note': '',
        'rows': (
            ('`for i in range(3):`', 'Does the lines below three times.'),
            ('`for fruit in fruits:`',
             'Goes through a list one item at a time.'),
            ('`while answer != "yes":`',
             'Keeps repeating for as long as the answer stays True.'),
            ('`break`', 'Leaves the loop straight away.'),
            ('`continue`',
             'Skips the rest of this round and starts the next one.'),
        ),
    },
    {
        'title': 'Keeping several values together',
        'note': '',
        'rows': (
            ('`fruits = ["apple", "pear"]`',
             'A list: values in order, inside square brackets.'),
            ('`me = {"name": "Ana", "age": 14}`',
             'A dictionary: a value stored under each name, inside curly '
             'brackets.'),
            ('`len(fruits)`',
             'How many items are in a list, a dictionary or some text.'),
            ('`fruits.append("plum")`',
             'Adds an item to the end of a list.'),
            ('`fruits[0]`',
             'The first item of a list. Counting starts at `0`.'),
        ),
    },
    {
        'title': 'Comments',
        'note': '',
        'rows': (
            ('`# later`', 'A comment. Python ignores the rest of the line.'),
        ),
    },
    {
        'title': 'Mistakes everyone makes',
        'note': 'Most errors are not Python being difficult. They are a '
                'bracket left open, a command spelled slightly wrong, or a '
                'number needed where text turned up.',
        'rows': (
            ('`prnit("hi")`',
             '`prnit` is not a command. Python only knows the word it was '
             'given, so check the spelling of the part it did not understand.'),
            ('`print("hi"`',
             'A bracket or a quote mark was opened and never closed.'),
            ('`((1 + 2)`',
             'The same mistake with a doubled bracket. Brackets have to pair '
             'up, so count them.'),
            ('`if x = 5:`',
             '`=` saves a value. `==` compares two values, and that is what '
             'belongs here.'),
            ('`if x == 5`',
             'Every `if`, `elif`, `else`, `for` and `while` line ends with a '
             'colon.'),
            ('`print(hello)`',
             'Text needs quote marks: `print("hello")`. Without them Python '
             'looks for a variable called `hello`.'),
            ('`age = "14"` then `age + 1`',
             'Text and a number cannot be added together. Use `int(age) + 1` '
             'when you want a sum.'),
            ('A tab at the start of one line, spaces at the start of the next',
             'Python reads the indentation as part of the structure, so the '
             'two have to match.'),
        ),
        'after': 'The three you will meet most are `SyntaxError` (something is '
                 'misspelled or unbalanced), `NameError` (a name Python does '
                 'not know) and `TypeError` (text where a number was needed).',
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
