"""Check that a release is safe to publish before it is published.

Two mistakes are cheap to make and expensive to notice.

The first is a name that no longer matches. The app carries the owner and
repository it trusts in ``updater.py``, and refuses any download that is not a
release asset of that exact project. When this repository was renamed, the app
was updated but a manifest already published on a channel still named the old
owner, so every reader was offered an update and then told the address was not
from this project. Comparing the pinned name against the repository the build
is actually running in turns that into a failed job instead.

The second is a version that goes backwards. A build is published whose
version sorts lower than the one already on the channel, so no reader is ever
offered it and the update silently never arrives. The version about to be
published is compared against the one already there.

Both checks run in the release workflows, just before a channel is moved. The
version comparison is the same one the app uses, so "newer" cannot mean two
different things.
"""

import argparse
import importlib.util
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_updater():
    """Load ``updater.py`` from its file rather than importing the package.

    The job that publishes a release installs nothing. It downloads the built
    artifacts and moves a release tag; ``requirements.txt`` is never
    installed there. ``accessible_ide/__init__.py`` builds the Flask
    application, so importing the package in that job dies on ``flask``
    before a single check runs - and because this tool runs *before* the
    release is moved, the guard added to protect dev publishes was itself
    what stopped the dev publish.

    The updater is standard library only, which is what makes loading it this
    way possible. It stays one module in the repository, so the ordering the
    app applies to versions and the ordering applied here cannot drift apart.

    ``updater.current_version()`` is the one function unavailable from here,
    because it imports ``__version__`` from the package. Nothing calls it.
    """
    path = ROOT / 'src' / 'accessible_ide' / 'updater.py'
    spec = importlib.util.spec_from_file_location('accessible_ide_updater', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


updater = _load_updater()


class CheckError(Exception):
    """Publishing would be wrong, for a reason the reader of the log can fix."""


def pinned_name() -> str:
    """The owner and repository the app trusts, as one string."""
    return f'{updater.OWNER}/{updater.REPO}'


def verify_publish(repo: str, url: str, version: str,
                   published_version: str | None) -> None:
    """Raise ``CheckError`` if publishing this build would be wrong.

    ``published_version`` is what the channel carries now, or ``None`` when
    nothing is published there yet or the lookup was skipped.
    """
    expected = pinned_name()
    if repo.lower() != expected.lower():
        raise CheckError(
            f'this build is for {repo} but the app is pinned to {expected}; '
            'a rename was not followed through'
        )

    # Built from the pinned, canonical name rather than from ``repo`` as
    # given, so the address has to match what the app itself will accept.
    # The app compares the address against the pinned name character for
    # character, so an address that only differs in case is refused there too,
    # and it has to be refused here rather than by every reader.
    prefix = f'https://github.com/{expected}/releases/download/'
    if not isinstance(url, str) or not url.startswith(prefix):
        raise CheckError(
            f'the download address is not a release asset of {expected}: {url!r}'
        )

    # The same guard the app applies, so a bad address is caught here rather
    # than by every reader who is offered the update.
    try:
        updater._allowed_asset_url(url)
    except updater.UpdateError as error:
        raise CheckError(str(error)) from error

    # Only a version that goes *backwards* is refused. Re-running a tag to
    # replace a build that failed to upload is a normal thing to do, and the
    # channel ending up on the same number it already had is harmless: readers
    # on an older build are still offered it. A number lower than the one
    # already published is not harmless. The channel would point at an older
    # build than the one readers may already have, and anyone on the newer
    # build would never be offered it at all.
    if published_version is not None and updater.is_newer(published_version, version):
        raise CheckError(
            f'{version} is older than {published_version} already on the '
            'channel, so the channel would move backwards and readers on '
            f'{published_version} would never be offered it'
        )


def lookup_version(channel: str) -> str | None:
    """The version published on ``channel`` now, or ``None`` if there is none.

    The address is cache-busted, because a channel manifest that was just
    replaced is served stale for a while otherwise and the check would compare
    against the copy it is trying to replace.
    """
    try:
        raw = updater._read_url(
            f'{updater.manifest_url(channel)}?t={int(time.time() * 1000)}',
            updater.DEFAULT_TIMEOUT,
            updater.MAX_MANIFEST_BYTES,
        )
    except updater._NotFound:
        return None
    try:
        data = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as error:
        raise CheckError(
            f'the manifest on the {channel} channel could not be read'
        ) from error
    version = data.get('version') if isinstance(data, dict) else None
    if not isinstance(version, str) or not version:
        raise CheckError(
            f'the manifest on the {channel} channel has no version number'
        )
    return version


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)

    check = commands.add_parser('check', help='refuse a publish that would be wrong')
    check.add_argument('--channel', required=True)
    check.add_argument('--version', required=True)
    check.add_argument('--url', required=True)
    check.add_argument('--repo', default=pinned_name(),
                       help='the repository this build is for')
    check.add_argument('--offline', action='store_true',
                       help='skip the published-version comparison')

    args = parser.parse_args(argv)
    try:
        if args.channel not in updater.CHANNELS:
            raise CheckError(
                f'{args.channel!r} is not a channel; expected one of '
                + ', '.join(updater.CHANNELS)
            )
        published = None if args.offline else lookup_version(args.channel)
        verify_publish(args.repo, args.url, args.version, published)
    except (CheckError, updater.UpdateError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1

    if published is None:
        print(f'ok: {args.channel} starts at {args.version}')
    elif updater.parse_version(published) == updater.parse_version(args.version):
        print(
            f'ok: {args.channel} stays at {args.version} (republished, so '
            'readers already on it will not be offered it again)'
        )
    else:
        print(f'ok: {args.channel} moves from {published} to {args.version}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
