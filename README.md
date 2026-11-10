# Jojo Code

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
- [Accessibility](#accessibility)
- [Try it now](#try-it-now)
- [Getting started](#getting-started)
- [Where your code runs](#where-your-code-runs)
- [Python dictionary](#python-dictionary)
- [Common mistakes](#common-mistakes-of-programmers)
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
- **Fonts** — OpenDyslexic by default, plus Atkinson Hyperlegible, Lexend, Nunito and Andika for dyslexia-friendly reading. Calibri, Arial, Comic Sans and Courier New come from your own computer.
- **Languages** — English, Hindi, French, Spanish, Portuguese, Russian, Korean, Japanese, Chinese, Greek, Arabic, Hijazi Arabic and Ukrainian, with right-to-left layout for Arabic.
- **Focus mode** — hide the gutter, or blur every line except the one you are on
- **Themes** — 15 presets (high contrast, dark, pastel, light, ocean, forest, white, AMOLED, red, orange, yellow, green, blue, indigo, violet), a custom theme builder with a hex colour grid, and a per-colour reset
- **Text size and spacing** — separate size, line height and letter spacing for the editor, output and shell
- **Reading ruler** — a shaded band follows your pointer over the code, so one line stays easy to follow without moving the caret
- **Per-pane toolbars** — each of the editor, output and shell has its own text toolbar, and anything you leave alone keeps following the settings you already chose
- **Text-to-speech** — reads your code and errors aloud, with hover and click reading
- **Sounds** — a short tone when your code starts, finishes, fails or waits for an answer, and a soft click on buttons, each with a switch in Settings
- **About** - the version, the licence and a credits list (see `CREDITS.md`)
- **First run** — a short wizard asks for language, font and theme with the same dropdowns as Settings, shows a line of text in the font you are choosing, and keeps Next, Back and Skip in a footer you can always see. A **Reset all settings** button sits in the corner of every screen for the case where the font or colour you picked cannot be read.
- **Screen readers** — native landmarks, live regions, focus management and spoken step changes; no ARIA invented where the browser already does the job
- **Errors** — plain-English messages, no jargon
- **Storage** — offline-first, settings saved to your computer
- **Privacy** — see [PRIVACY.md](PRIVACY.md): no accounts, no analytics; code runs on your machine unless you use the browser copy
- **Platforms** — browser web app and Windows `.exe`

[↑ Back to contents](#contents)

---

## Accessibility

Jojo Code is built for dyslexic and neurodivergent readers, not adapted for them afterwards. The accessibility features are part of the interface, and the test suite checks the ones that can be measured.

- **Reading fonts:** OpenDyslexic is the default. Atkinson Hyperlegible, Lexend and Nunito are bundled, and you can add your own `.ttf`, `.otf`, `.woff` or `.woff2` file. The chosen font can be applied to the code, the output, the shell and the rest of the interface separately.
- **Text size and spacing:** font size, line height, letter spacing and text weight are adjustable, with separate controls for the editor, output and shell.
- **Contrast:** every bundled theme and every derived custom colour is checked against WCAG 2.1 AA (4.5:1 for text). `tests/test_contrast.py` is the arbiter and must pass before a visual change lands. The custom theme builder nudges a colour that would fail until it is readable again.
- **Themes:** 15 presets — high contrast, dark, pastel, light, ocean, forest, white, AMOLED, and red, orange, yellow, green, blue, indigo and violet. The custom theme has a hex grid, a native colour picker and a hex field, and every colour has its own reset. Code colours for keywords, strings, comments, numbers and functions sit under **Settings → Colours → Advanced**.
- **Languages:** English, Hindi, French, Spanish, Portuguese, Russian, Korean, Japanese, Chinese, Greek, Arabic and Ukrainian. Arabic switches the page to right-to-left, and the editor pins its own left-to-right direction so code, gutter, caret and scrollbar never mirror. Every visible string is translated; nothing falls back to English silently.
- **Reading ruler:** a shaded band follows the pointer over the editor so one line is easy to follow. It is a reading aid only, so it leaves the caret, the keyboard and the text untouched.
- **Standards:** WCAG 2.1 AA is the floor, with the WCAG 2.2 additions that apply here — focus is never obscured by floating content (2.4.11), every pointer action has a keyboard alternative (2.5.7), targets are at least 24 by 24 pixels (2.5.8), and help stays in the same place at every width (3.2.6).
- **Screen readers:** the app uses native landmarks, headings, fieldsets, labels, live regions and focus management. Opening a dialog moves focus into it, a setup step announces itself when it changes, and an error is announced rather than only coloured. Hidden setup panels are removed from the tab order.
- **Keyboard:** every control is reachable without a mouse. Running and stopping have configurable key presses, and the setup screen never traps the reader behind Escape.
- **Text-to-speech:** reads output and errors aloud, can speak buttons and labels on hover or click, and lets the reader choose the voice and speed. It works alongside a screen reader rather than replacing it.
- **Sounds:** four short tones say when a run starts, finishes, fails or waits on an answer, so a reader who cannot see the output pane is still told what happened. Reduce motion silences them along with everything else, and **Settings → Sound** has a switch of its own.
- **Focus and motion:** focus mode hides the gutter or fades other lines, and reduced motion can be set to follow the operating system or be turned on and off explicitly.
- **Plain English:** Python errors are translated into sentences that say what went wrong and how to fix it, with the original error kept available.

[↑ Back to contents](#contents)

---

## Try it now

- **Web app:** [https://accessible-coding.duckdns.org](https://accessible-coding.duckdns.org) — hosted on Oracle Cloud
- **Windows installer (recommended):** download `JojoCode-Setup.exe` from the [beta release](https://github.com/hot-hilux21/jojo-code-ide/releases/download/beta/JojoCode-Setup.exe) — installs the app to any folder, installs Python and adds it to PATH, and creates shortcuts
- **Windows exe (portable):** download `JojoCode.exe` from the [beta release](https://github.com/hot-hilux21/jojo-code-ide/releases/download/beta/JojoCode.exe)

[↑ Back to contents](#contents) · [↓ Next: Getting started](#getting-started)

---

## Getting started

### Windows installer (recommended)

1. Download `JojoCode-Setup.exe` from the [beta release](https://github.com/hot-hilux21/jojo-code-ide/releases/download/beta/JojoCode-Setup.exe)
2. Run it. Choose any install folder.
3. Tick **Install Python and add it to PATH** (on by default) — the installer also installs the Microsoft Visual C++ runtime and the WebView2 runtime it needs.
4. Finish, and the IDE opens in its own **desktop window** (no browser needed). Write Python, then press **Run** (or `Ctrl+Enter`).

### Windows portable (.exe)

1. Download `JojoCode.exe` from the [beta release](https://github.com/hot-hilux21/jojo-code-ide/releases/download/beta/JojoCode.exe)
2. Double-click to run. A **desktop window** opens with the IDE (no browser tab).
3. Write Python, then press **Run** (or `Ctrl+Enter`).

> Needs the Microsoft Edge **WebView2 runtime** (built into Windows 10/11 or installed by the setup above). Click **Quit** in the sidebar footer to close the app.

> Windows builds are code-signed through the [SignPath Foundation](https://signpath.org/) open-source programme. Until a signed build is published, Windows may still show a SmartScreen prompt: click **More info** then **Run anyway**.

### Browser (web)

Open [https://accessible-coding.duckdns.org](https://accessible-coding.duckdns.org). No install needed. The site runs on Oracle Cloud and is updated automatically when `main` is pushed.

### Development

```bash
git clone https://github.com/hot-hilux21/jojo-code-ide.git
cd accessible-coding
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000

### Build the exe yourself

```bash
pip install pyinstaller
pyinstaller Jojo Code.spec --noconfirm
```

Your exe is at `dist/JojoCode.exe`.

### Run tests

```bash
python smoke_test.py
python -m unittest discover -s tests -t .
node tests/dom_harness.js
```

[↑ Back to contents](#contents) · [↓ Next: Where your code runs](#where-your-code-runs)

---

## Where your code runs

**Windows app.** Your code runs on your own computer. Press Run and the app starts a process of its own to run your file, then prints what came out. Nothing you write is uploaded, no account is needed, and the app makes no network requests to run your code. The only thing it goes online for is checking for a new version; that check is on by default and can be turned off in Settings.

**Browser copy.** Your code is sent to the server hosting the site, run there, and the output is sent back. This is the only version where your code leaves your machine. That server is shared by everyone using the site, so this copy runs with a sandbox the Windows app does not: imports such as `os` and `subprocess` are refused before your program starts.

[↑ Back to contents](#contents) · [↓ Next: Python dictionary](#python-dictionary)

---

## Python dictionary

A glossary of the Python you will meet in this app. Each entry says what a command does and shows something you can type straight into the editor and run.

[↑ Back to contents](#contents) · [↓ Next: Project structure](#project-structure)

---

### Printing

print() shows something on the screen.

| Command | What it does |
| --- | --- |
| `print("Hello")` | Show text on the screen. |
| `print(5)` | Show a number. |
| `print("Hi", name)` | Show several things at once. |

```python
print("Hello, world!")
print("Counting:", 1, 2, 3)
```

### Comments

Text after # is ignored by Python.

| Command | What it does |
| --- | --- |
| `# a comment` | Text after # is ignored by Python. |
| `# print("not run")` | You can comment out code to stop it running. |

```python
# This line is ignored
print("This runs")  # and this comment too
```

### Variables

`=` saves a value under a name. Variable names cannot start with a number and cannot have spaces.

| Command | What it does |
| --- | --- |
| `x = 5` | Save the number 5 as x. |
| `name = "Ana"` | Save text as name. |
| `type(5)` | Find out the type of a value. |
| `int` | Whole numbers like 1, 2, 3. |
| `float` | Numbers with a decimal point like 3.5. |
| `str` | Text like "hello". |
| `bool` | True or False. |
| `list` | A collection in order. |
| `int("5")` | Turn text into an integer. |
| `str(5)` | Turn a number into text. |

```python
x = 5
name = "Ana"
print(type(x), type(name))
print(int("5") + 1)
```

### User input

Ask the user a question and get their answer.

| Command | What it does |
| --- | --- |
| `name = input("What is your name? ")` | Ask for input and save it as text. |
| `age = int(input("How old are you? "))` | Get input and turn it into a number. |
| `print("Hi", name)` | Use the answer. |

```python
name = input("What is your name? ")
print("Hello", name)
```

### Numbers and math

Numbers and the signs that work on them.

| Command | What it does |
| --- | --- |
| `x = 5` | An integer. |
| `y = 3.14` | A float. |
| `x + y` | Add numbers together. |
| `x - y` | Subtract numbers. |
| `x * y` | Multiply numbers. |
| `x / y` | Divide numbers. |
| `x // y` | Divide and keep the whole number. |
| `x % y` | Get the remainder (modulus). |
| `x ** y` | Raise to a power. |
| `abs(-5)` | Get the absolute value. |
| `round(3.14159, 2)` | Round to 2 decimal places. |

```python
x = 5
y = 3.14
print(x + y, x - y, x * y)
print(x % 2, x ** 2)
print(round(3.14159, 2))
```

### Booleans and comparisons

Values that are True or False, and the signs that compare.

| Command | What it does |
| --- | --- |
| `True` | A true value. |
| `False` | A false value. |
| `5 > 3` | Compare values to get True or False. |
| `5 == 5` | Check if two values are equal. |
| `5 != 3` | Check if two values are not equal. |
| `5 >= 3` | Greater than or equal. |
| `5 <= 3` | Less than or equal. |
| `and or not` | Logical operators. |

```python
age = 14
print(age > 10 and age < 20)
print(age == 14, age != 5)
```

### Making decisions

Run code only when a condition is True or False.

| Command | What it does |
| --- | --- |
| `if x > 5:` | Run if condition is True. |
| `elif x == 5:` | Run if previous was False and this is True. |
| `else:` | Run if all conditions are False. |
| `if x > 5 and x < 10:` | Combine conditions. |
| `if x > 5 or x < 2:` | Either condition can be True. |

```python
x = 7
if x > 5:
    print("big")
elif x == 5:
    print("five")
else:
    print("small")
```

### Loops

Run code more than once.

| Command | What it does |
| --- | --- |
| `while x < 5:` | Repeat while condition is True. |
| `    x += 1` | Change something so the loop ends. |
| `for i in range(3):` | Loop three times. |
| `for fruit in fruits:` | Loop through each item in a list. |
| `break` | Leave the loop. |
| `continue` | Skip to the next item. |

```python
for i in range(3):
    print("Counting:", i)

x = 0
while x < 3:
    print("While:", x)
    x += 1
```

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

```python
def greet(name):
    return "Hello " + name

print(greet("Ana"))
```

### Lists

Lists hold values in order and can be changed.

| Command | What it does |
| --- | --- |
| `fruits = []` | Create an empty list. |
| `fruits = ["apple", "pear"]` | Create a list with the items in it. |
| `fruits[0]` | Get the first item (lists are zero indexed, so the first item is 0). |
| `len(fruits)` | Get how many items. |
| `fruits.append("plum")` | Add an item to the end. |
| `fruits.remove("pear")` | Remove an item. |
| `fruits[0] = "banana"` | Change an item. |
| `fruits.pop()` | Remove the last item. |

```python
fruits = []
fruits.append("apple")
fruits.append("pear")
print(fruits, len(fruits))
print(fruits[0])
```

### Formatting

Format text and numbers.

| Command | What it does |
| --- | --- |
| `"Hello {}".format("Ana")` | Format with curly braces. |
| `f"Hello {name}"` | Format with f strings. |
| `round(3.14159, 2)` | Round to 2 decimal places. |
| `"{:.2f}".format(3.14159)` | Format to 2 decimal places. |
| `format(3.14159, ".3g")` | Format to 3 significant figures. |

```python
pi = 3.14159
print(round(pi, 2))
print(f"{pi:.2f}")
print(format(pi, ".3g"))
```

### Vocabulary

Words you will meet in this app.

| Command | What it does |
| --- | --- |
| `IDE` | Integrated Development Environment: the app you write code in. |
| `zero-index` | Counting starts at 0, so the first item is at index 0. |
| `interpreter` | Runs Python code line by line. |
| `compiler` | Turns code into another form before running. |
| `boolean` | A value that is True or False. |
| `operator` | A symbol like +, == or and that does work on values. |
| `terminal` | A text window where you type commands. |

```python
print("IDE, zero-index, interpreter, compiler, boolean, operator")
```

## Common mistakes of programmers

Everyone writes these when they are learning. The mistake is underlined, and the fix is beside it. If you recognise one of these in your own code, you are in good company.

❌ = the mistake. ✅ = what to write instead.

| ❌ Mistake | ✅ Correct solution |
| --- | --- |
| <u>Using one equals sign to compare</u> — `if name = "Sam":` sets the value instead of checking it. | `if name == "Sam":` — two equals signs compare. |
| <u>Forgetting the colon</u> — `if name == "Sam"` | `if name == "Sam":` — the line ends with a colon. |
| <u>Mixing up text and numbers</u> — `"1" + 1` adds nothing, it errors. | `int("1") + 1` — turn the text into a number first. |
| <u>Assuming input is a number</u> — `input()` always gives back text. | `age = int(input("How old are you? "))` |
| <u>Misspelling a name</u> — `name` and `Name` are two different things in Python. | Use the same spelling every time. |
| <u>Off-by-one on `range`</u> — `range(1, 5)` stops at 4, not 5. | `range(1, 6)` — the end value is not included. |
| <u>Changing a list while looping over it</u> — items get skipped. | Loop over a copy: `for item in list(items):` |
| <u>Using a name before it exists</u> — `print(total)` before `total` is set. | Give the value a starting point first, then use it. |
| <u>Confusing `append` and `extend`</u> — `append` adds one item, `extend` adds each item of a list. | Pick the one that matches what you mean. |
| <u>Ignoring indentation</u> — Python uses indentation to know what belongs together. | Indent the body of `if`, `for`, `while`, and `def` the same amount. |
| <u>Catching every error and saying nothing</u> — `except:` hides real problems. | `except ValueError:` and say what went wrong. |
| <u>Repeating the same code</u> — three copies means three places to fix a bug. | Write a function once, then call it. |


## Project structure

```
accessible-coding/
├── .github/workflows/       # CI: tests + exe build on release tags
├── docs/                    # Documentation
├── src/accessible_ide/
│   ├── assets/              # Fonts (OpenDyslexic, Atkinson Hyperlegible, Lexend, Nunito, Andika, Almarai, Mukta)
│   ├── i18n/                # Translation catalogues (13 languages)
│   ├── static/              # CSS + JavaScript (CodeMirror, app logic) + the interface sounds in static/audio
│   ├── templates/           # HTML page
│   ├── routes.py            # Flask routes, themes and settings validation
│   ├── shell.py             # Python shell sessions
│   ├── trace_runner.py      # Line-by-line variable trace
│   └── utils/               # Helpers (colour maths, error translation)
├── tests/                   # Python tests and the DOM harness
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
- [x] 15 preset themes (high contrast, dark, pastel, light, ocean, forest, white, AMOLED, red, orange, yellow, green, blue, indigo, violet)
- [x] Custom theme builder with hex colour grid and a per-colour reset
- [x] Reading ruler that follows the pointer without moving the caret
- [x] 13 languages, including right-to-left Arabic and Hijazi Arabic
- [x] Adjustable text size, line height and letter spacing per pane
- [x] Text-to-speech for output, errors, buttons and labels
- [x] Reading font choice (OpenDyslexic by default, Atkinson Hyperlegible / Lexend / Nunito / Andika also bundled)
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

*Jojo Code — code comfortably.*
