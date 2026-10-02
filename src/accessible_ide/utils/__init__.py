"""Helpers that are not part of the app's surface.

Colour maths lives here rather than in routes.py because it is real
arithmetic that wants its own tests, and because the same rules are
implemented again in the browser (static/js/tint.js) so a theme change can
be reflected without asking the server. See colour.py for why the two exist
together.
"""