# AccessibleIDE

A fully accessible IDE for dyslexic and neurodivergent learners.

Python-first. Dyslexia-friendly fonts. Focus mode. Text-to-speech. Plain-English errors. Custom themes.

> **Motivation:** Enable dyslexic classmates and neurodivergent learners to code comfortably; driven by empathy and shared experience.

---

(Sorry guys, but as well as being so vibe-coded, I really wanted a solution. So you don't really need to call this **"AI SLOP"**.

- I'm proficient in Python and HTML, CSS and even batch scripting in Windows with several personal security and performance scripts I have made in the past by myself.
- And I've even modded in Android assembly (smali) disassembling .dex (dalvik executable files manually)...
- But I just want to push solutions and fill up my account with repo projects to build my career and make a difference to everyone esp. my friends and classmates.

---

## Contents

Jump to any section:

- [Key features](#key-features)
- [Try it now](#try-it-now)
- [Getting started](#getting-started)
- [Where your code runs](#where-your-code-runs)
- [Python dictionary](#python-dictionary)
- [Project structure](#project-structure)
- [MVP checklist](#mvp-checklist)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Full specification](#full-specification)
- [Contact](#contact)

---

## Key features

- **Editor** — CodeMirror Python editor with syntax highlighting
- **Execution** — built-in Python runner (10-second safety timeout)
- **Fonts** — OpenDyslexic by default, plus Atkinson Hyperlegible, Lexend and Nunito for dyslexia-friendly reading. Calibri, Arial, Comic Sans and Courier New come from your own computer.
- **Focus mode** — hide the gutter, or blur every line except the one you are on
- **Themes** — high contrast, dark, pastel, and light
- **Text-to-speech** — reads your code and errors aloud
- **Errors** — plain-English messages, no jargon
- **Storage** — offline-first, settings saved to your computer
- **Platforms** — browser web app and Windows `.exe`

[↑ Back to contents](#contents)

---

## Try it now

- **Web app:** [https://accessible-coding.onrender.com](https://accessible-coding.onrender.com)
- **Windows installer (recommended):** download `AccessibleIDE-Setup.exe` from the [**v1.0.0 stable release**](https://github.com/hot-hilux21/accessible-coding/releases/tag/v1.0.0) - installs the app to any folder, installs Python and adds it to PATH, and creates shortcuts
- **Windows exe (portable):** download `AccessibleIDE.exe` from the [**v1.0.0 stable release**](https://github.com/hot-hilux21/accessible-coding/releases/tag/v1.0.0)

[↑ Back to contents](#contents) · [↓ Next: Getting started](#getting-started)

---

## Getting started

### Windows installer (recommended)

1. Download `AccessibleIDE-Setup.exe` from the [beta release](https://github.com/hot-hilux21/accessible-coding/releases/download/beta/AccessibleIDE-Setup.exe)
2. Run it. Choose any install folder.
3. Tick **Install Python and add it to PATH** (on by default) — the installer also installs the Microsoft Visual C++ runtime and the WebView2 runtime it needs.
4. Finish, and the IDE opens in its own **desktop window** (no browser needed). Write Python, then press **Run** (or `Ctrl+Enter`).

### Windows portable (.exe)

1. Download `AccessibleIDE.exe` from the [beta release](https://github.com/hot-hilux21/accessible-coding/releases/download/beta/AccessibleIDE.exe)
2. Double-click to run. A **desktop window** opens with the IDE (no browser tab).
3. Write Python, then press **Run** (or `Ctrl+Enter`).

> Needs the Microsoft Edge **WebView2 runtime** (built into Windows 10/11 or installed by the setup above). Click **Quit** in the sidebar footer to close the app.

> If Windows shows "Windows protected your PC", click **More info** then **Run anyway** — the app is not code-signed yet.

### Browser (web)

Open [https://accessible-coding.onrender.com](https://accessible-coding.onrender.com). No install needed.

### Development

```bash
git clone https://github.com/hot-hilux21/accessible-coding.git
cd accessible-coding
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000

### Build the exe yourself

```bash
pip install pyinstaller
pyinstaller AccessibleIDE.spec --noconfirm
```

Your exe is at `dist/AccessibleIDE.exe`.

### Run tests

```bash
python smoke_test.py
```

[↑ Back to contents](#contents) · [↓ Next: Where your code runs](#where-your-code-runs)

---

## Where your code runs

**Windows app.** Your code runs on your own computer. Press Run and the app starts a process of its own to run your file, then prints what came out. Nothing you write is uploaded, no account is needed, and the app makes no network requests. The only thing it can go online for is checking for a new version, and that stays off until you turn it on in Settings.

**Browser copy.** Your code is sent to the server hosting the site, run there, and the output is sent back. This is the only version where your code leaves your machine. That server is shared by everyone using the site, so this copy runs with a sandbox the Windows app does not: imports such as `os` and `subprocess` are refused before your program starts.

[↑ Back to contents](#contents) · [↓ Next: Python dictionary](#python-dictionary)

---

## Python dictionary

A glossary of the Python you will meet in this app. Each entry says what a command does and shows something you can type straight into the editor and run.

[↑ Back to contents](#contents) · [↓ Next: Project structure](#project-structure)

---

### Introduction and getting started

Python is a programming language you can type and run straight away.

| Command | What it does |
| --- | --- |
| `python --version` | Check which version of Python is installed. |
| `python script.py` | Run a Python file from the command line. |
| `print()` | Show something on the screen. |

### Syntax

Python reads spaces at the start of a line to know how things belong together.

| Command | What it does |
| --- | --- |
| `if x == 5:` | A line that ends with a colon starts a new block. |
| `    print(x)` | Indented lines belong to the block above them. |
| `# a comment` | Text after `#` is ignored by Python. |

### Comments

| Command | What it does |
| --- | --- |
| `# This is a comment` | Python ignores this line. |
| `# print("not run")` | You can comment out code to stop it running. |

### Variables

`=` saves a value under a name. Variable names cannot start with a number and cannot have spaces.

| Command | What it does |
| --- | --- |
| `x = 5` | Save the number 5 as x. |
| `name = "Ana"` | Save text as name. |
| `x, y = 5, 6` | Assign two values at the same time. |
| `x = y = 7` | Assign the same value to two names. |

### Data types

Python works out the type from the value you save.

| Command | What it does |
| --- | --- |
| `type(5)` | Find out the type of a value. |
| `int` | Whole numbers like 1, 2, 3. |
| `float` | Numbers with a decimal point like 3.5. |
| `str` | Text like "hello". |
| `bool` | True or False. |
| `list` | A collection in order. |
| `tuple` | A collection that cannot be changed. |
| `set` | A collection with no duplicates. |
| `dict` | Values saved under keys. |

### Numbers

| Command | What it does |
| --- | --- |
| `x = 5` | An integer. |
| `y = 3.14` | A float. |
| `x + y` | Add numbers together. |
| `x - y` | Subtract numbers. |
| `x * y` | Multiply numbers. |
| `x / y` | Divide numbers. |
| `x // y` | Divide and keep the whole number. |
| `x % y` | Get the remainder. |
| `x ** y` | Raise to a power. |

### Casting

Turn one type of value into another.

| Command | What it does |
| --- | --- |
| `int("5")` | Turn text into an integer. |
| `float("3.5")` | Turn text into a float. |
| `str(5)` | Turn a number into text. |
| `bool(0)` | Turn a value into True or False. |

### Strings

| Command | What it does |
| --- | --- |
| `"hello".upper()` | Make all letters uppercase. |
| `"HELLO".lower()` | Make all letters lowercase. |
| `len("hello")` | Get the length of text. |
| `"hello"[0]` | Get the first character. |
| `"hello" in "hello world"` | Check if text contains something. |
| `"a,b".split(",")` | Split text into a list. |
| `"a".replace("a","b")` | Replace part of the text. |

### Booleans

| Command | What it does |
| --- | --- |
| `True` | A true value. |
| `False` | A false value. |
| `5 > 3` | Compare values to get True or False. |
| `5 == 5` | Check if two values are equal. |
| `5 != 3` | Check if two values are not equal. |
| `bool("hello")` | Most values become True. Zero and empty become False. |

### Operators

| Command | What it does |
| --- | --- |
| `+ - * /` | Arithmetic operators. |
| `== != < > <= >=` | Comparison operators. |
| `and or not` | Logical operators. |
| `in not in` | Membership operators. |
| `is is not` | Identity operators. |

### Lists

Lists hold values in order and can be changed.

| Command | What it does |
| --- | --- |
| `fruits = ["apple", "pear"]` | Create a list. |
| `fruits[0]` | Get the first item. |
| `len(fruits)` | Get how many items. |
| `fruits.append("plum")` | Add an item to the end. |
| `fruits.remove("pear")` | Remove an item. |
| `fruits[0] = "banana"` | Change an item. |
| `fruits.pop()` | Remove the last item. |

### Tuples

Tuples hold values in order but cannot be changed.

| Command | What it does |
| --- | --- |
| `colors = ("red", "blue")` | Create a tuple. |
| `colors[0]` | Get the first item. |
| `len(colors)` | Get how many items. |
| `"red" in colors` | Check if an item is in the tuple. |

### Sets

Sets hold values with no duplicates and no set order.

| Command | What it does |
| --- | --- |
| `nums = {1, 2, 3}` | Create a set. |
| `nums.add(4)` | Add an item. |
| `nums.remove(1)` | Remove an item. |
| `len(nums)` | Get how many items. |
| `1 in nums` | Check if an item is in the set. |

### Dictionaries

Dictionaries save values under keys.

| Command | What it does |
| --- | --- |
| `me = {"name": "Ana", "age": 14}` | Create a dictionary. |
| `me["name"]` | Get a value by key. |
| `me["age"] = 15` | Change a value. |
| `me["city"] = "Paris"` | Add a new key and value. |
| `me.keys()` | Get all keys. |
| `me.values()` | Get all values. |
| `len(me)` | Get how many key value pairs. |

### If...Else

Run code only when a condition is True or False.

| Command | What it does |
| --- | --- |
| `if x > 5:` | Run if condition is True. |
| `elif x == 5:` | Run if previous was False and this is True. |
| `else:` | Run if all conditions are False. |
| `if x > 5 and x < 10:` | Combine conditions. |
| `if x > 5 or x < 2:` | Either condition can be True. |

### Match

Compare a value against several patterns. Available in Python 3.10 and later.

| Command | What it does |
| --- | --- |
| `match day:` | Start a match statement. |
| `  case "Mon":` | Run if day matches this pattern. |
| `    print("start")` | Code to run for this case. |
| `  case _:` | A default case when nothing matches. |

### While loops

Keep running code while a condition is True.

| Command | What it does |
| --- | --- |
| `while x < 5:` | Repeat while condition is True. |
| `    x += 1` | Change something so the loop ends. |
| `break` | Leave the loop straight away. |
| `continue` | Skip the rest of this round and go to the next. |

### For loops

Loop through a sequence of items.

| Command | What it does |
| --- | --- |
| `for i in range(3):` | Loop three times. |
| `for fruit in fruits:` | Loop through each item in a list. |
| `for c in "abc":` | Loop through each character in text. |
| `break` | Leave the loop. |
| `continue` | Skip to the next item. |

### Functions

Group code together and reuse it by name.

| Command | What it does |
| --- | --- |
| `def greet():` | Define a function with no input. |
| `    print("hi")` | Code that runs when called. |
| `greet()` | Call the function. |
| `def greet(name):` | Define a function that takes an input. |
| `    return name` | Return a value from the function. |
| `greet("Ana")` | Call with an argument. |

### Range

`range()` gives a sequence of numbers to use in loops.

| Command | What it does |
| --- | --- |
| `range(5)` | Numbers from 0 up to but not including 5. |
| `range(1, 5)` | Numbers from 1 up to but not including 5. |
| `range(1, 10, 2)` | Numbers from 1 stepping by 2. |
| `list(range(5))` | Turn range into a list to see the numbers. |

### Arrays

Python has lists. Some libraries also use arrays for numbers.

| Command | What it does |
| --- | --- |
| `nums = [1, 2, 3]` | Create a list to hold numbers. |
| `len(nums)` | Get the number of items. |
| `nums.append(4)` | Add a new number. |
| `nums[0] = 0` | Change a number. |

### Iterators

An iterator lets you go through items one by one.

| Command | What it does |
| --- | --- |
| `fruits = ["apple", "pear"]` | A list is iterable. |
| `it = iter(fruits)` | Get an iterator from the list. |
| `next(it)` | Get the next item. |
| `for fruit in fruits:` | A for loop uses iterators behind the scenes. |

### Modules

Modules let you reuse code from other files or built in tools.

| Command | What it does |
| --- | --- |
| `import math` | Import a module. |
| `math.sqrt(16)` | Use something from the module. |
| `from math import sqrt` | Import just one thing. |
| `import random` | Another common module. |
| `random.randint(1, 10)` | Get a random number. |

### Dates

| Command | What it does |
| --- | --- |
| `from datetime import datetime` | Import the datetime tools. |
| `datetime.now()` | Get the current date and time. |
| `datetime.now().year` | Get just the year. |
| `datetime.now().strftime("%Y-%m-%d")` | Format the date as text. |

### Math

| Command | What it does |
| --- | --- |
| `import math` | Import math tools. |
| `math.pi` | Get pi. |
| `math.sqrt(25)` | Get the square root. |
| `math.ceil(3.2)` | Round up. |
| `math.floor(3.8)` | Round down. |
| `abs(-5)` | Get the absolute value. |

### JSON

Work with JSON data in Python.

| Command | What it does |
| --- | --- |
| `import json` | Import the json module. |
| `data = {"name": "Ana"}` | Python dictionary. |
| `json.dumps(data)` | Turn a dictionary into JSON text. |
| `json.loads("{\"name\": \"Ana\"}")` | Turn JSON text into a Python dictionary. |

### RegEx

Search and match text patterns.

| Command | What it does |
| --- | --- |
| `import re` | Import the re module. |
| `re.search("a", "apple")` | Search for a pattern. |
| `re.findall("a", "apple")` | Find all matches. |
| `re.match("a", "apple")` | Match at the start of text. |
| `re.sub("a", "b", "apple")` | Replace matches. |

### Try...Except

Handle errors so your program does not crash.

| Command | What it does |
| --- | --- |
| `try:` | Try to run code that might cause an error. |
| `    x = int("abc")` | This will cause an error. |
| `except ValueError:` | Run this if a ValueError happens. |
| `    print("not a number")` | Show a friendly message. |
| `else:` | Run this if no error happened. |
| `finally:` | Run this no matter what. |

### String formatting

| Command | What it does |
| --- | --- |
| `"Hello {}".format("Ana")` | Format with curly braces. |
| `f"Hello {name}"` | Format with f strings. |
| `"Hello %s" % "Ana"` | Format with percent signs. |
| `"{0} {1}".format("Hello", "Ana")` | Format with numbered placeholders. |

### User input

Ask the user a question and get their answer.

| Command | What it does |
| --- | --- |
| `name = input("What is your name? ")` | Ask for input and save it as text. |
| `age = int(input("How old are you? "))` | Get input and turn it into a number. |
| `print("Hi", name)` | Use the answer. |


## Project structure

```
accessible-coding/
├── .github/workflows/       # CI: tests + exe build on release tags
├── docs/                    # Documentation
├── src/accessible_ide/
│   ├── assets/              # Fonts (OpenDyslexic, Atkinson Hyperlegible, Lexend, Nunito)
│   ├── static/              # CSS + JavaScript (CodeMirror, app logic)
│   ├── templates/           # HTML page
│   ├── config/              # Settings load/save
│   └── utils/               # Helpers (error translation)
├── tests/                   # Test suite
├── accessible-ide-requirements.md  # Full specification
├── AGENTS.md                # Agent instructions
└── README.md                # This file
```

[↑ Back to contents](#contents) · [↓ Next: MVP checklist](#mvp-checklist)

---

## MVP checklist

What is done so far:

- [x] Python code editor (CodeMirror)
- [x] Built-in Python runner
- [x] Save and open code files
- [x] Local settings save/load (JSON)
- [x] 4 preset themes (high contrast, dark, pastel, light)
- [x] Custom theme builder
- [x] Reading font choice (OpenDyslexic by default, Atkinson Hyperlegible / Lexend / Nunito also bundled)
- [x] Focus mode (hide gutter / blur other lines)
- [x] Error messages in plain English
- [x] Visual error highlighting in the editor
- [x] Flask web version
- [x] Windows `.exe` (PyInstaller)
- [x] GitHub public repo

Coming next:

- [ ] More text-to-speech options
- [ ] Configurable blur zones (blocks, functions)

[↑ Back to contents](#contents) · [↓ Next: Roadmap](#roadmap)

---

## Roadmap

- **Now** — editor, runner, save/open, fonts, focus mode, themes, plain errors, error line highlighting
- **Next** — more text-to-speech options, configurable blur zones
- **v1.0+** — linter, Jupyter, collaboration, plugins

See the [full specification](#full-specification) for details.

[↑ Back to contents](#contents) · [↓ Next: Contributing](#contributing)

---

## Contributing

- **License:** MIT — free to use, modify, and fork
- **Core development:** solo (owner)
- **External pull requests:** please ask first. Changes are reviewed before merging.
- **Feedback:** very welcome, especially from dyslexic and neurodivergent users.

[↑ Back to contents](#contents) · [↓ Next: Full specification](#full-specification)

---

## Full specification

The complete requirements document is at [accessible-ide-requirements.md](accessible-ide-requirements.md).

It covers:

- Platform and distribution
- Storage and sync model
- Core IDE features
- Accessibility features (fonts, TTS, visual, cognitive)
- Technical stack
- Open source and collaboration model
- Timeline and release strategy
- Validation and testing
- User personas
- Feature checklists
- Success metrics
- Resources and references
- Next steps

[↑ Back to contents](#contents) · [↓ Next: Contact](#contact)

---

## Contact

Built with empathy for dyslexic and neurodivergent learners.

Feedback and testing help are always welcome — especially from the people this is for.

[↑ Back to contents](#contents)

---

*AccessibleIDE — code comfortably.*