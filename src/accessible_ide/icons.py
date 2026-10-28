"""The icon set this app draws with.

Every icon is a Lucide outline glyph, vendored as path data rather than
fetched at runtime. The app is offline-first, and a CDN request would fail
in the packaged Windows build, so the shapes live here in Python and are
rendered by the ``icon()`` Jinja helper. Lucide is ISC licensed; see
``assets/licenses/lucide-ISC.txt``.

To add one, copy the child markup of the matching 24x24 Lucide SVG into
``_ICONS`` below (``npm pack lucide-static`` puts them in ``icons/``).
Never paste an emoji into a template: this module is the one place icons
come from.
"""

from markupsafe import Markup

_ICONS = {
    'play': (
        '<path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z" />'
    ),
    'square': (
        '<rect width="18" height="18" x="3" y="3" rx="2" />'
    ),
    'save': (
        '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" /> <path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7" /> <path d="M7 3v4a1 1 0 0 0 1 1h7" />'
    ),
    'folder-open': (
        '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2" />'
    ),
    'volume-2': (
        '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z" /> <path d="M16 9a5 5 0 0 1 0 6" /> <path d="M19.364 18.364a9 9 0 0 0 0-12.728" />'
    ),
    'book-open': (
        '<path d="M12 5v16" /> <path d="M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z" />'
    ),
    'settings': (
        '<path d="M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915" /> <circle cx="12" cy="12" r="3" />'
    ),
    'table-2': (
        '<path d="M3 9h18" /> <path d="M9 3v18" /> <rect x="3" y="3" width="18" height="18" rx="2" />'
    ),
    'terminal': (
        '<path d="M12 19h8" /> <path d="m4 17 6-6-6-6" />'
    ),
    'type': (
        '<path d="M12 4v16" /> <path d="M4 7V5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v2" /> <path d="M9 20h6" />'
    ),
    'move-vertical': (
        '<path d="M12 2v20" /> <path d="m8 18 4 4 4-4" /> <path d="m8 6 4-4 4 4" />'
    ),
    'move-horizontal': (
        '<path d="m18 8 4 4-4 4" /> <path d="M2 12h20" /> <path d="m6 8-4 4 4 4" />'
    ),
    'triangle-alert': (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" /> <path d="M12 9v4" /> <path d="M12 17h.01" />'
    ),
    'grip-vertical': (
        '<circle cx="9" cy="12" r="1" /> <circle cx="9" cy="5" r="1" /> <circle cx="9" cy="19" r="1" /> <circle cx="15" cy="12" r="1" /> <circle cx="15" cy="5" r="1" /> <circle cx="15" cy="19" r="1" />'
    ),
    'x': (
        '<path d="M18 6 6 18" /> <path d="m6 6 12 12" />'
    ),
    'minus': (
        '<path d="M5 12h14" />'
    ),
    'plus': (
        '<path d="M5 12h14" /> <path d="M12 5v14" />'
    ),
    'palette': (
        '<path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z" /> <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" /> <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" /> <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" /> <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" />'
    ),
    'check': (
        '<path d="M20 6 9 17l-5-5" />'
    ),
    'rotate-ccw': (
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /> <path d="M3 3v5h5" />'
    ),
    'download': (
        '<path d="M12 15V3" /> <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /> <path d="m7 10 5 5 5-5" />'
    ),
    'upload': (
        '<path d="M12 3v12" /> <path d="m17 8-5-5-5 5" /> <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />'
    ),
    'keyboard': (
        '<path d="M10 8h.01" /> <path d="M12 12h.01" /> <path d="M14 8h.01" /> <path d="M16 12h.01" /> <path d="M18 8h.01" /> <path d="M6 8h.01" /> <path d="M7 16h10" /> <path d="M8 12h.01" /> <rect width="20" height="16" x="2" y="4" rx="2" />'
    ),
    'chevron-down': (
        '<path d="m6 9 6 6 6-6" />'
    ),
    'chevron-up': (
        '<path d="m18 15-6-6-6 6" />'
    ),
    'circle': (
        '<circle cx="12" cy="12" r="10" />'
    ),
    'trash-2': (
        '<path d="M10 11v6" /> <path d="M14 11v6" /> <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /> <path d="M3 6h18" /> <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />'
    ),
}

# Every name the templates are allowed to ask for. A typo raises KeyError
# at render time rather than producing an empty box nobody notices.
ICON_NAMES = frozenset(_ICONS)

_SVG = (
    '<svg class="icon icon-{name}" viewBox="0 0 24 24" width="{size}" '
    'height="{size}" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true" focusable="false">{body}</svg>'
)


def icon(name, size=18, extra_class=''):
    """Render one icon as inline SVG.

    The SVG inherits ``currentColor`` so it follows the theme and the
    high-contrast remaps. It is always decorative: the control around it
    carries the accessible name, so there is no second announcement.
    """
    try:
        body = _ICONS[name]
    except KeyError:
        raise KeyError(
            'unknown icon %r; add it to accessible_ide.icons' % name
        )
    markup = _SVG.format(name=name, size=int(size), body=body)
    if extra_class:
        markup = markup.replace('class="icon', 'class="%s icon' % extra_class, 1)
    return Markup(markup)


def sprite_names():
    """The names in this set, for tests and documentation."""
    return sorted(_ICONS)
