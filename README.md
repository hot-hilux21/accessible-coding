# AccessibleIDE

A fully accessible IDE for dyslexic and neurodivergent learners.

Python-first. Dyslexia-friendly fonts. Focus mode. Text-to-speech. Plain-English errors. Custom themes.

> **Motivation:** Enable dyslexic classmates and neurodivergent learners to code comfortably; driven by empathy and shared experience.

---

(Sorry guys, but as well as being so vibe-coded, I really wanted a solution. The MD files got pushed and I could close them but ig it's transparency.

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
- **Windows installer (recommended):** download `AccessibleIDE-Setup.exe` from the [beta release](https://github.com/hot-hilux21/accessible-coding/releases/download/beta/AccessibleIDE-Setup.exe) — installs the app to any folder, installs Python and adds it to PATH, and creates shortcuts
- **Windows exe (portable):** download `AccessibleIDE.exe` from the [beta release](https://github.com/hot-hilux21/accessible-coding/releases/download/beta/AccessibleIDE.exe)

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

### Saving a value under a name

| Command | What it does |
| --- | --- |
| `age = 14` | Saves a value under a name so you can use it again later. |
| `age = age + 1` | Works out the right side first, then saves the answer. |
| `age += 1` | The short way of writing the line above. |

`=` saves a value. `==` compares two values. Mixing them up is the most common first mistake.

### Saying something and reading an answer

| Command | What it does |
| --- | --- |
| `print("hello")` | Puts something on the screen. |
| `input("How old are you? ")` | Asks on screen, waits for you to type, then hands back what you typed as text. |
| `type(3.5)` | Tells you what kind of value something is. |

### Turning one kind of value into another

| Command | What it does |
| --- | --- |
| `int("12")` | Makes a whole number out of text. `int(3.9)` gives `3`. |
| `float("3.5")` | Makes a decimal number out of text. |
| `str(12)` | Makes text out of anything. |

### Sums

| Command | What it does |
| --- | --- |
| `+` `-` `*` `/` | Add, subtract, multiply, divide. |
| `7 // 2` | Divides and keeps the whole number only: `3`. |
| `7 % 2` | The remainder after dividing: `1`. |
| `2 ** 3` | Powers: `8`. |
| `round(3.6)` | Rounds to the nearest whole number: `4`. |

### Comparing two values

| Command | What it does |
| --- | --- |
| `==` | Are these two the same? |
| `!=` | Are these two different? |
| `<` `>` `<=` `>=` | Smaller, bigger, smaller or equal, bigger or equal. |
| `and` `or` `not` | Joins True and False answers together. |

### Doing something only sometimes

| Command | What it does |
| --- | --- |
| `if age >= 13:` | Does the lines below only when the answer is True. Note the colon at the end. |
| `elif age == 12:` | A second check to try when the first one was False. |
| `else:` | What to do when none of the checks worked. |

### Doing something more than once

| Command | What it does |
| --- | --- |
| `for i in range(3):` | Does the lines below three times. |
| `for fruit in fruits:` | Goes through a list one item at a time. |
| `while answer != "yes":` | Keeps repeating for as long as the answer stays True. |
| `break` | Leaves the loop straight away. |
| `continue` | Skips the rest of this round and starts the next one. |

### Keeping several values together

| Command | What it does |
| --- | --- |
| `fruits = ["apple", "pear"]` | A list: values in order, inside square brackets. |
| `me = {"name": "Ana", "age": 14}` | A dictionary: a value stored under each name, inside curly brackets. |
| `len(fruits)` | How many items are in a list, a dictionary or some text. |
| `fruits.append("plum")` | Adds an item to the end of a list. |
| `fruits[0]` | The first item of a list. Counting starts at `0`. |

### Comments and mistakes

| Command | What it does |
| --- | --- |
| `# later` | A comment. Python ignores the rest of the line. |
| `NameError` `SyntaxError` `TypeError` | The three errors you will see most often. |

Anything that goes wrong is rewritten in plain English in the message under the editor, so you do not have to read the raw Python error to work out what happened.

[↑ Back to contents](#contents) · [↓ Next: Project structure](#project-structure)

---

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

What is done in v0.1.0-beta:

- [x] Python code editor (CodeMirror)
- [x] Built-in Python runner
- [x] Local settings save/load (JSON)
- [x] 4 preset themes (high contrast, dark, pastel, light)
- [x] Reading font choice (OpenDyslexic by default, Atkinson Hyperlegible / Lexend / Nunito also bundled)
- [x] Focus mode (hide gutter / blur other lines)
- [x] Error messages in plain English
- [x] Flask web version
- [x] Windows `.exe` (PyInstaller)
- [x] GitHub public repo

Coming next (v0.2):

- [ ] Save and open code files
- [ ] Custom theme builder
- [ ] More text-to-speech options
- [ ] Visual error highlighting in the editor
- [ ] Configurable blur zones (blocks, functions)

[↑ Back to contents](#contents) · [↓ Next: Roadmap](#roadmap)

---

## Roadmap

- **v0.1 (now)** — editor, runner, fonts, focus mode, themes, plain errors
- **v0.2** — custom themes, more TTS, file save/open, visual error highlighting
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