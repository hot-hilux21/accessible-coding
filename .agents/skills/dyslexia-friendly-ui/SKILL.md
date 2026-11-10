---
name: dyslexia-friendly-ui
description: Design, build, and review more readable and inclusive software interfaces. Covers dyslexia-friendly language and typography, adjustable reading preferences, visual focus assistance, numerical accessibility considerations for dyscalculia, framework-specific implementation, and human-centred testing.
---

# Dyslexia-Friendly UI & Inclusive Coding

## Purpose

Use this skill when creating, modifying, or reviewing user interfaces, application content, documentation, forms, dashboards, educational tools, or other software that people need to read and understand.

Build accessibility into the application rather than treating it as a decorative theme.

The aim is to give people meaningful control over how information is presented. Dyslexia and dyscalculia affect people differently. Do not assume that one font, colour, layout, or interaction works for everyone.

**Core principles**

1. Offer choice instead of enforcing one supposedly universal dyslexia-friendly design.
2. Keep language clear without making it childish or removing necessary detail.
3. Make accessibility controls functional, persistent, and available throughout the application.
4. Preserve the application's existing behaviour and visual identity unless a change is required.
5. Test with assistive technology and, where practical, people with relevant lived experience.
6. Be honest about what has and has not been tested.

---

## 1. Start by understanding the project

Before changing code:

1. Identify the framework, language, build system, and existing design system.
2. Inspect existing components, typography, themes, settings storage, and accessibility support.
3. Identify the main user journeys and the screens where reading or numerical information matters.
4. Check whether the project already has accessibility preferences. Extend them instead of creating competing systems.
5. Avoid adding dependencies unless they provide clear value.
6. Make a plan that fits the existing architecture.

For an existing application, do not rewrite unrelated parts of the project.

---

## 2. Dyslexia-friendly writing

Apply these guidelines to interface text, instructions, documentation, tooltips, notifications, error messages, onboarding, and code comments.

### Sentence construction

- Prefer short, direct sentences.
- Aim for roughly 8–15 words where practical. This is a guide, not a strict limit.
- Keep one main idea in each sentence where possible.
- Prefer active voice.
- Use familiar words when they communicate the meaning accurately.
- Explain unfamiliar technical terms in plain language.
- Avoid double negatives and unnecessarily complex sentence structures.
- Remove repetition and filler.
- Replace vague references such as "this", "that", or "it" when the meaning is unclear.
- Keep terminology consistent throughout the application.
- Do not remove important warnings, qualifications, or technical detail just to shorten text.

### Instructions and documentation

- Break complex procedures into numbered steps.
- Give each step one main action.
- Put steps in the order the user should complete them.
- Explain important outcomes and what the user should expect.
- Use descriptive headings.
- Use bullets for related items.
- Keep paragraphs focused on one topic.
- Use examples when they make an abstract explanation easier to understand.

### UI language

Prefer labels that describe the action or outcome.

| Avoid | Prefer |
|---|---|
| Submit | Save changes |
| Invalid input detected | Enter a valid email address |
| Processing your request | Saving your changes… |
| Click here | View your settings |
| Operation unsuccessful | We couldn't save your changes. Try again. |

Error messages should explain what happened and how to fix it. Do not blame or shame the user.

### Tone

Use a natural, respectful, professional tone. Never assume that a person with dyslexia has limited intelligence, knowledge, or technical ability.

---

## 3. Typography and font choices

Offer several font choices rather than forcing one typeface.

Possible options include:

- Atkinson Hyperlegible
- OpenDyslexic
- Lexend
- Arial
- Verdana
- Tahoma
- The operating system's default sans-serif font

These are options to evaluate, not a ranking or a guarantee of improved reading for every person. Some people prefer conventional fonts. Let users decide.

### Implementation guidance

- Use a clear fallback font stack.
- Host font files locally when practical, while respecting each font's licence.
- Do not make the application unusable if a downloadable font fails to load.
- Avoid using all-caps for long passages.
- Avoid long passages in italics or underlined text.
- Use bold sparingly to identify important terms.
- Keep text resizable and avoid fixed-height containers that clip enlarged text.

Example CSS:

```css
:root {
  --reading-font: Arial, sans-serif;
  --reading-size: 1rem;
  --reading-line-height: 1.7;
  --reading-letter-spacing: 0.02em;
  --reading-word-spacing: 0.06em;
  --reading-paragraph-spacing: 1em;
  --reading-measure: 70ch;
}

body {
  font-family: var(--reading-font);
  font-size: var(--reading-size);
  line-height: var(--reading-line-height);
  letter-spacing: var(--reading-letter-spacing);
  word-spacing: var(--reading-word-spacing);
}

.reading-content {
  max-width: var(--reading-measure);
}

.reading-content p {
  margin-block: 0 var(--reading-paragraph-spacing);
}
```

Do not assume that increased letter spacing or line height is always better. Make these values adjustable.

---

## 4. Adjustable reading preferences

Where appropriate, provide a clearly labelled Reading or Accessibility settings panel.

Consider offering:

- Font family
- Text size
- Line height
- Letter spacing
- Word spacing
- Paragraph spacing
- Reading width
- Text colour
- Background colour
- Light and dark themes
- Bold-text preference
- Reset to defaults

### Behaviour requirements

- Show a preview when this helps users understand the effect.
- Apply changes immediately where practical.
- Make every control change the actual application.
- Persist preferences between sessions using the project's existing settings system.
- Provide a clear reset option.
- Avoid storing unnecessary personal information.
- Do not override a user's choice with operating-system preferences after they have explicitly selected an application setting.

Use sensible defaults, but do not describe them as universally suitable.

---

## 5. Colour and visual presentation

Offer customisable themes where appropriate. Possible starting presets include:

- Warm cream
- Soft beige
- Pale blue
- Soft green
- Light grey
- Dark theme
- High contrast

Do not force pure white backgrounds or pure black text. Equally, do not assume that tinted backgrounds are better for everyone.

### Contrast and colour

- Meet WCAG 2.2 AA contrast requirements where applicable: 4.5:1 for normal text and 3:1 for large text.
- Ensure controls and meaningful graphical objects have sufficient contrast.
- Never communicate important information through colour alone.
- Pair colour with text, icons, patterns, or other visual cues.
- Check every supported theme, including hover, selected, disabled, and focus states.

Allow custom colours only if the resulting interface remains usable. Where possible, warn users when their chosen combination has poor contrast.

---

## 6. Spacing and layout

- Prefer left-aligned text for reading passages.
- Avoid justified paragraphs.
- Use comfortable line and paragraph spacing.
- Avoid excessively long lines.
- Group related information.
- Use clear heading levels.
- Keep navigation and component placement predictable.
- Avoid unnecessary visual clutter.
- Do not crowd controls together.
- Use responsive layouts.
- Allow content to reflow when text is enlarged.
- Avoid fixed heights and hidden overflow that cut off text.

Do not use spacing as a substitute for clear information architecture.

---

## 7. Visual Focus Assistance

Visual Focus Assistance is an optional set of features that can reduce competing visual information.

It must not make surrounding content inaccessible or prevent users from understanding the wider page.

### 7.1 Hover focus

When a pointer enters an appropriate interactive item:

- Make the item visually prominent.
- Keep its text sharp and readable.
- Optionally soften or dim nearby sibling items.
- Restore the surrounding items when the pointer leaves.

Potential targets include cards, navigation items, list options, buttons, and menu items.

Do not apply broad dimming to entire pages by default. Scope effects to a relevant group of related items.

### 7.2 Selection focus

When an item is selected:

- Show a persistent selected state.
- Keep the state until the selection changes or is cleared.
- Distinguish selection from hover and keyboard focus.
- Do not rely on colour alone.
- Do not dim other content if doing so would hide useful context.

### 7.3 Keyboard focus

- Provide a clear `:focus-visible` indicator.
- Maintain logical keyboard order.
- Ensure focus is not obscured by sticky headers, overlays, or other content.
- Do not require a pointer to use focus assistance.
- Keep keyboard focus distinct from a selected item.

Example:

```css
:focus-visible {
  outline: 3px solid #2878c8;
  outline-offset: 3px;
}

.focus-group:has(.focus-item:hover)
.focus-item:not(:hover) {
  opacity: 0.65;
}

.focus-group:has(.focus-item:focus-visible)
.focus-item:not(:focus-visible) {
  opacity: 0.65;
}
```

The `:has()` selector is supported in current major browsers. If the project's browser support includes older environments, provide a JavaScript or class-based fallback. Do not make essential functionality depend on hover.

### 7.4 Modal, dialog, drawer, and panel focus

When a modal dialog opens:

- Display a backdrop that separates the dialog from the page.
- Optionally blur the inactive background.
- Keep the dialog itself sharp and readable.
- Move focus into the dialog.
- Keep keyboard navigation within a modal dialog while it is open.
- Make the background inert to pointer and keyboard interaction.
- Support Escape to close when appropriate.
- Restore focus to the control that opened the dialog.
- Give the dialog an accessible name and appropriate semantics.

A backdrop or blur effect alone does not provide accessible modal behaviour. Use native `<dialog>` appropriately or a well-tested accessible dialog component.

Do not blur the background for every small popover or tooltip. Choose an effect that matches the interaction.

### 7.5 Adjustable focus controls

Where appropriate, allow users to configure:

- Focus Assistance on or off
- Hover emphasis
- Selection emphasis
- Keyboard focus enhancement
- Background blur strength
- Surrounding-item dim intensity
- Highlight intensity
- Transition effects
- Which component groups use focus assistance

Provide a way to disable each visual effect independently.

### 7.6 Motion and touch

- Respect `prefers-reduced-motion`.
- Keep transitions subtle.
- Do not rely on hover on touch devices.
- Provide tap, selection, or keyboard alternatives.
- Avoid flashing, pulsing, or rapidly changing effects.
- Never hide essential information when focus moves.

---

## 8. Accessible components and interaction

### Buttons

- Use descriptive action labels.
- Provide visible hover, active, and focus states.
- Make targets large enough to use comfortably.
- Use native buttons for actions.
- Do not use vague labels when a specific action can be named.

### Forms

- Associate every input with a visible label.
- Explain required fields.
- Identify errors in text, not only by colour.
- Explain how to fix validation errors.
- Preserve valid entries when a form fails validation.
- Use appropriate input types and autocomplete attributes.
- Do not rely on placeholder text as the only label.

### Navigation

- Use consistent names and structures.
- Indicate the current location.
- Avoid unnecessarily deep menus.
- Ensure menus work with keyboard and touch.
- Keep focus visible when menus open and close.

### Notifications

- Use concise, informative messages.
- Give users enough time to read them.
- Do not communicate status through colour alone.
- Use accessible live regions when appropriate.
- Avoid announcing excessive or repetitive information.

### Tooltips

- Keep explanations short.
- Do not put essential instructions only in a tooltip.
- Make tooltip content available to keyboard and touch users.
- Avoid tooltips that disappear before users can read them.

---

## 9. Keyboard and assistive technology

- Use semantic HTML and native controls wherever possible.
- Support keyboard operation.
- Keep focus order logical.
- Make focus indicators visible.
- Use meaningful headings and link text.
- Associate form labels and instructions correctly.
- Use ARIA only when native HTML does not provide the required semantics.
- Test with relevant screen readers.
- Ensure accessibility settings can themselves be operated without a pointer.

Do not add ARIA attributes simply to make code appear accessible. Incorrect ARIA can make an interface harder to use.

---

## 10. Dyscalculia-aware numerical presentation

Dyscalculia is distinct from dyslexia. It can affect how some people understand, process, remember, or work with numbers and mathematical relationships.

Do not assume that every person with dyscalculia has the same needs.

### Numerical information

- Use consistent number formatting.
- Label values clearly.
- Put units beside measurements.
- Explain abbreviations.
- Make decimal and thousands separators unambiguous.
- Distinguish similar-looking values.
- Avoid unnecessary numerical density.
- Preserve precision where it matters.

### Calculations

Where useful:

- Show the values used.
- Break calculations into steps.
- Label mathematical operations.
- Explain how the result was obtained.
- Offer optional calculator assistance.
- Let users review their inputs.
- Explain calculation errors in plain language.

Example:

Instead of showing only `£120 - £35 = £85`, present:

- Starting amount: £120
- Amount spent: £35
- Remaining amount: £85
- Calculation: £120 minus £35

Do not remove the calculation itself when users need to verify it.

### Charts and graphs

- Label axes clearly.
- Provide written summaries of important trends.
- Do not rely on colour alone.
- Use distinguishable markers or patterns.
- Avoid crowded charts.
- Offer a data table where useful.
- Explain percentages and proportions.
- Allow users to inspect individual values.

### Dates, times, tables, and money

- Use unambiguous date formats.
- Identify AM and PM where relevant.
- Include units and currency symbols.
- Use descriptive table headings.
- Align numerical values consistently.
- Separate totals from individual entries.
- Avoid unnecessarily dense tables.

### Optional customisation

Consider adjustable number size, spacing between number groups, number highlighting, step-by-step calculations, and alternative chart presentations.

These are options to test with users, not universal requirements.

---

## 11. Framework-specific implementation

Adapt examples to the project's architecture. These examples are starting points, not complete production accessibility systems.

### 11.1 Vanilla HTML, CSS, and JavaScript

Use CSS custom properties for shared reading preferences.

```css
:root {
  --reading-font: Arial, sans-serif;
  --reading-size: 1rem;
  --reading-line-height: 1.7;
  --reading-letter-spacing: 0.02em;
  --reading-word-spacing: 0.06em;
  --reading-background: #f5ebd7;
  --reading-text: #29251f;
}

body {
  font-family: var(--reading-font);
  font-size: var(--reading-size);
  line-height: var(--reading-line-height);
  letter-spacing: var(--reading-letter-spacing);
  word-spacing: var(--reading-word-spacing);
  background: var(--reading-background);
  color: var(--reading-text);
}

:focus-visible {
  outline: 3px solid #2878c8;
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

Update CSS custom properties from JavaScript when preferences change. Persist settings using the application's existing storage approach.

### 11.2 React

Use a shared context or state store rather than separate, conflicting settings in each component.

Example:

```jsx
import React, { createContext, useContext, useState } from "react";

const defaults = {
  font: "Arial",
  fontSize: 17,
  lineHeight: 1.7,
  letterSpacing: 0.02,
  wordSpacing: 0.06,
  theme: "warm",
  focusAssistance: true,
  hoverFocus: true,
  selectionFocus: true,
  backgroundBlur: 4,
  dimIntensity: 35
};

const AccessibilityContext = createContext(null);

export function AccessibilityProvider({ children }) {
  const [preferences, setPreferences] = useState(() => {
    try {
      const saved = JSON.parse(
        localStorage.getItem("accessibility-preferences") || "{}"
      );
      return { ...defaults, ...saved };
    } catch {
      return { ...defaults };
    }
  });

  function updatePreference(key, value) {
    setPreferences(previous => {
      const next = { ...previous, [key]: value };
      try {
        localStorage.setItem(
          "accessibility-preferences",
          JSON.stringify(next)
        );
      } catch {
        // Keep the current session usable if storage is unavailable.
      }
      return next;
    });
  }

  return (
    <AccessibilityContext.Provider
      value={{ preferences, updatePreference }}
    >
      {children}
    </AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error(
      "useAccessibility must be used inside AccessibilityProvider"
    );
  }
  return context;
}
```

Apply preferences to a root element or shared theme layer. Validate saved values before applying them. For server-rendered applications, avoid accessing `localStorage` during server rendering and prevent theme flashes where practical.

Use a tested accessible dialog component for modal focus management.

### 11.3 Vue

Use a composable and reactive state. Load saved preferences safely and apply them through a shared root element.

```javascript
import { reactive, watch } from "vue";

const defaults = {
  fontFamily: "Arial",
  fontSize: 17,
  lineHeight: 1.7,
  focusAssistance: true
};

function loadPreferences() {
  try {
    return {
      ...defaults,
      ...JSON.parse(
        localStorage.getItem("accessibility-preferences") || "{}"
      )
    };
  } catch {
    return { ...defaults };
  }
}

const preferences = reactive(loadPreferences());

watch(
  preferences,
  value => {
    document.documentElement.style.setProperty(
      "--reading-font",
      `"${value.fontFamily}", Arial, sans-serif`
    );
    document.documentElement.style.setProperty(
      "--reading-size",
      `${value.fontSize}px`
    );
    document.documentElement.style.setProperty(
      "--reading-line-height",
      String(value.lineHeight)
    );

    try {
      localStorage.setItem(
        "accessibility-preferences",
        JSON.stringify(value)
      );
    } catch {
      // The current session should still work without persistence.
    }
  },
  { deep: true, immediate: true }
);

export function useAccessibility() {
  return { preferences };
}
```

In server-rendered Vue applications, guard browser-only APIs and initialise preferences on the client.

### 11.4 Python Tkinter

Use configurable fonts, colours, wrapping, and keyboard focus.

```python
import tkinter as tk
from tkinter import font

root = tk.Tk()
root.title("Accessible application")

settings = {
    "font": "Arial",
    "size": 17,
    "background": "#F5EBD7",
    "foreground": "#29251F",
}

reading_font = font.Font(
    family=settings["font"],
    size=settings["size"]
)

label = tk.Label(
    root,
    text="Welcome to your workspace.",
    font=reading_font,
    bg=settings["background"],
    fg=settings["foreground"],
    wraplength=500,
    justify="left",
)

label.pack(padx=20, pady=20)

def increase_text():
    reading_font.configure(size=reading_font.cget("size") + 1)

button = tk.Button(
    root,
    text="Increase text size",
    command=increase_text,
)
button.pack(pady=10)

root.mainloop()
```

Apply settings consistently to all relevant widgets. Check focus order, keyboard shortcuts, scaling, and platform-specific screen reader support.

### 11.5 PySide6 and PyQt

Use application-wide fonts, palettes, and reusable settings.

```python
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
)
from PySide6.QtGui import QFont

app = QApplication([])

window = QWidget()
layout = QVBoxLayout(window)

reading_font = QFont("Arial", 17)
reading_font.setLetterSpacing(
    QFont.SpacingType.AbsoluteSpacing, 0.5
)

label = QLabel("Welcome to your workspace.")
label.setFont(reading_font)
label.setWordWrap(True)

layout.addWidget(label)

button = QPushButton("Increase text size")
layout.addWidget(button)

def increase_text():
    reading_font.setPointSize(reading_font.pointSize() + 1)
    label.setFont(reading_font)

button.clicked.connect(increase_text)

window.show()
app.exec()
```

For production, use a shared settings object and apply changes across all relevant widgets. Test the actual Qt version and platform. Check accessible names, keyboard navigation, and screen reader behaviour.

### 11.6 Other frameworks

For Angular, Svelte, Next.js, Electron, Tauri, .NET, Kivy, Flet, and other frameworks:

1. Identify the framework's native accessibility patterns.
2. Reuse its existing state and settings architecture.
3. Centralise reading preferences.
4. Implement focus and dialog behaviour using tested framework components.
5. Test platform-specific accessibility support.
6. Avoid copying web-only code into frameworks where it does not apply.

---

## 12. Persistence, privacy, and user control

- Store only the preferences needed to provide the chosen experience.
- Use the project's existing settings storage where possible.
- Validate stored values before applying them.
- Provide a reset option.
- Do not transmit accessibility preferences to external services unless the user has been clearly informed and the feature requires it.
- Do not infer or record a user's diagnosis from their settings.
- Make it possible to use the application without enabling optional visual effects.

---

## 13. Accessibility testing

Automated checks are useful, but they cannot establish that an interface is comfortable or understandable for everyone.

Use a combination of automated testing, manual testing, assistive technology, and user research.

### 13.1 Automated checks

Use tools appropriate to the project, such as:

- axe-core
- Lighthouse accessibility audits
- WAVE
- Accessibility Insights
- Framework-specific testing tools

Check relevant WCAG 2.2 AA requirements. Do not claim conformance based on an automated score alone.

### 13.2 Manual checks

**Typography**
- Can users change fonts?
- Are font files and fallbacks working?
- Can users resize text?
- Does enlarged text remain readable?
- Does content reflow without clipping?

**Visual presentation**
- Can users change themes and colours?
- Is text contrast sufficient?
- Are focus indicators visible?
- Can users disable blur, dimming, and motion?

**Focus assistance**
- Does hover emphasis work where a pointer is available?
- Does selection remain visible?
- Does keyboard focus work independently?
- Does a dialog receive focus when opened?
- Is background interaction prevented while a modal is active?
- Is focus restored correctly when it closes?
- Can users adjust or disable each effect?

**Numerical information**
- Are numbers and units clearly labelled?
- Are calculations understandable?
- Are charts available in a non-visual or tabular form where appropriate?
- Are dates, times, and currency unambiguous?

**General use**
- Can important tasks be completed with a keyboard?
- Are forms labelled?
- Are errors actionable?
- Does the application work at different screen sizes and zoom levels?
- Does it work with relevant assistive technologies?

### 13.3 Human consultation: dyslexia

Where practical, involve people with lived experience of dyslexia during design, development, and evaluation.

Invite feedback on:

- Font readability and choice
- Text size and spacing
- Paragraph and line length
- Colour and contrast preferences
- Sentence clarity
- Navigation and information structure
- Hover, selection, and keyboard focus
- Dialogs, popups, and visual distraction
- Overall comfort when completing realistic tasks

Do not assume that participants all prefer OpenDyslexic, tinted backgrounds, or the same focus effects.

Let participants configure the interface and explain what works for them.

### 13.4 Human consultation: dyscalculia

Where numerical information is important, involve people with lived experience of dyscalculia.

Invite feedback on:

- Number formatting and grouping
- Mathematical instructions
- Calculators and step-by-step workings
- Numerical forms
- Tables and charts
- Financial information
- Dates, times, and measurements
- The clarity of totals, percentages, and comparisons

Do not assume that everyone experiences numerical information in the same way.

### 13.5 Ethical and inclusive research

When consulting participants:

- Obtain informed consent.
- Explain the purpose and format of the research.
- Allow participants to stop or withdraw.
- Do not require people to disclose a diagnosis.
- Collect only information needed for the research.
- Protect personal information and feedback.
- Offer accessible ways to participate.
- Consider reasonable compensation for participants' time.
- Do not treat one person's experience as representative of an entire group.
- Do not make medical or diagnostic claims.

Recruit a range of participants where practical, including people with different preferences and levels of technical experience.

### 13.6 Feedback and iteration

For each finding, record:

1. The feature or task tested.
2. The difficulty or positive experience reported.
3. The participant's suggested change, if any.
4. The change made by the development team.
5. The result of retesting.

Separate individual preferences from recurring usability barriers. A preference that differs from the majority can still be important to that individual.

### 13.7 Report testing honestly

Distinguish clearly between:

- Automated checks completed
- Developer-led manual checks completed
- Assistive technology testing completed
- Consultation with people with dyslexia completed
- Consultation with people with dyscalculia completed
- Independent accessibility review completed

Never claim that consultation took place if it did not. Never claim an application is fully dyslexia-friendly, dyscalculia-friendly, or WCAG-conformant solely because it follows this skill.

Document known limitations and outstanding issues.

---

## 14. Final implementation checklist

Before declaring work complete, check the items relevant to the project.

### Reading and writing
- [ ] User-facing language is clear and respectful.
- [ ] Font choices are available and functional.
- [ ] Text size can be adjusted.
- [ ] Line, letter, and word spacing can be adjusted where offered.
- [ ] Reading width and paragraph spacing are comfortable.
- [ ] Enlarged text does not break the layout.

### Visual customisation
- [ ] Theme and colour settings work.
- [ ] Contrast has been checked.
- [ ] Colour is not the only way information is conveyed.
- [ ] Preferences persist.
- [ ] Reset settings works.

### Focus assistance
- [ ] Hover focus works where applicable.
- [ ] Selection focus persists correctly.
- [ ] Keyboard focus is clearly visible.
- [ ] Modal focus is managed correctly.
- [ ] Background interaction is prevented when required.
- [ ] Focus returns to the correct control after a dialog closes.
- [ ] Blur, dimming, and motion can be adjusted or disabled.

### Numerical accessibility
- [ ] Numerical values have clear labels and units.
- [ ] Calculations are understandable where relevant.
- [ ] Charts have appropriate text or data alternatives.
- [ ] Dates, times, and currency are unambiguous.

### General accessibility
- [ ] Keyboard navigation works.
- [ ] Screen reader behaviour has been checked where applicable.
- [ ] Forms have accessible labels and errors.
- [ ] Reduced motion is respected.
- [ ] Responsive layouts work with enlarged text.
- [ ] Relevant automated and manual tests have been completed.
- [ ] Human consultation and its limitations are accurately documented.

---

## 15. Final principles

1. Accessibility is a core design consideration, not decoration.
2. Do not assume that one solution works for everyone.
3. Offer meaningful customisation.
4. Keep language clear without being patronising.
5. Preserve important technical and numerical detail.
6. Make every advertised setting functional.
7. Prefer predictable, consistent interactions.
8. Test with real tasks, not just screenshots.
9. Include people with lived experience when practical.
10. Be transparent about testing, evidence, and limitations.

The goal is to build software that people can adapt to their own reading, focus, and information-processing preferences.
