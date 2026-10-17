# Code signing the Windows build

The Windows builds are unsigned. Windows shows "Windows protected your PC" the
first time somebody runs the installer, and the publisher line reads as unknown
rather than as the project. This file is the plan for fixing that for free, and
the record of what was wired up and why.

## What signing changes, and what it does not

Signing attaches a certificate to the `.exe`. Windows can then say who published
the file, and the warning becomes a prompt that names a publisher. It does not
delete the warning. Reputation with SmartScreen is earned per certificate over
downloads and time, so the first signed release is still a prompt; the difference
is that it is a prompt naming the project instead of an unknown.

A signature is also the only thing that ties the file a reader downloads to the
code in this repository. That is the part worth having even during the period
when the prompt is still there.

## The free option: SignPath Foundation

[SignPath Foundation](https://signpath.org/) issues a code signing certificate to
open source projects at no cost and holds the private key on their hardware
security module, which is what makes it usable from a cloud build: there is no
USB token to plug in. They do not identify you personally. They verify that the
binary was built from the public repository, and they vouch for that with their
name, so the publisher line reads as SignPath Foundation on behalf of this
project.

It is free for projects that are open source, public, and not sold. This one is
MIT and public, so it fits.

### Applying

Apply at <https://signpath.org/apply>. The form asks for the repository, the
license, and how the builds are produced. Everything it wants already exists in
this repository, so the answers are short. What to say:

- **Project:** AccessibleIDE, <https://github.com/hot-hilux21/accessible-coding>
- **License:** MIT (see `LICENSE` in the repository root)
- **What it is:** a Python editor for dyslexic and neurodivergent learners, built
  as a Flask app that runs in a WebView2 window on Windows. Offered free, with
  no paid tier and nothing to buy.
- **How it is built:** GitHub Actions, hosted runners only, from tagged commits
  on `main`. Two jobs build a PyInstaller bundle and an Inno Setup installer
  (`.github/workflows/build-release.yml`). Both are produced from the tagged
  commit by the workflow, with nothing built by hand outside it.
- **What needs signing:** `AccessibleIDE.exe` (the portable build) and
  `AccessibleIDE-Setup.exe` (the installer readers download).

They may ask for a maintainer to be named and for the repository to have the
SignPath GitHub App installed, which is at <https://github.com/apps/signpath>.
Install it once, before applying, so there is nothing to wait for afterwards.

## After approval

Approval gives an organization id. Create a project in SignPath for this
repository, with a signing policy that this workflow is allowed to use, and an
artifact configuration that describes what is inside the file being signed.

Set these in the repository under Settings, Secrets and variables, Actions:

| Name | Kind | Value |
| --- | --- | --- |
| `SIGNPATH_API_TOKEN` | secret | a SignPath API token for a user who may submit signing requests |
| `SIGNPATH_ORGANIZATION_ID` | variable | the organization id SignPath issues |
| `SIGNPATH_PROJECT_SLUG` | variable | the project slug from the SignPath project |
| `SIGNPATH_SIGNING_POLICY_SLUG` | variable | the signing policy slug |

There is a fifth thing SignPath calls the artifact configuration, which
describes the layout of the file being signed. It is not passed by the workflow
because SignPath uses the project's default one. If a project ever needs more
than one, pass `artifact-configuration-slug` from a variable in the same three
places the other slugs appear.

`SIGNPATH_ORGANIZATION_ID` is the switch. While it is blank, every signing step
is skipped and the workflow builds and releases exactly as it did before. There
is no branch to remember to turn on and no way for an unfinished signing setup
to break a release that has nothing to do with it.

## The artifact configuration

`actions/upload-artifact` stores what it is given as a ZIP archive. The
configuration for each artifact therefore has a root element of `<zip-file>`,
with the executable inside it:

```xml
<artifact-configuration xmlns="http://signpath.io/artifact-configuration">
  <zip-file>
    <pe-file path="AccessibleIDE-Setup.exe">
      <authenticode-sign />
    </pe-file>
  </zip-file>
</artifact-configuration>
```

and the same shape with `AccessibleIDE.exe` for the portable build. The `path`
is matched against the entry names inside the archive, so if a release starts
failing at the signing step with a message about a missing file, this is the
line to look at first.

## What the workflow does

`.github/workflows/build-release.yml` signs two files, in two jobs, in an order
that matters:

- **The portable exe** is signed after PyInstaller builds it, before it is
  uploaded. It is a download in its own right, so the signature has to be part
  of the bytes that get published. It is not the file the updater installs, so
  no manifest is generated from it.
- **The installer** is signed after Inno Setup compiles it, and then
  `version.json` is generated from the signed file: the manifest records the
  `sha256` and the size of the file the updater will download, and a signature
  changes both. Generating the manifest first would publish a manifest that
  refuses the build it names, and every reader on the channel would be offered
  an update that cannot install. The installer is the update payload, because
  replacing an installed copy means replacing a folder that is in use and
  under Program Files, which is a job for the installer rather than for a
  second copy of the app.

Each job uploads the unsigned file, submits it, copies the signed file back over
the original, and then checks the result with `Get-AuthenticodeSignature`. A run
that gets as far as signing and comes back with something Windows will not accept
fails there rather than shipping it.

The main-branch build in `.github/workflows/build-exe.yml` is left unsigned.
When signing goes live, that workflow is the one to revisit: it now publishes
to `beta`, the channel the README links to and the default a reader is given,
so an unsigned build landing there is a file in front of readers that Windows
will not vouch for. The same steps belong there, and the manifest has to be
generated after signing rather than before it, because a signature changes
both the `sha256` and the size it records. Until then the build is skipped the
same way the others are, by leaving the variable unset.

## Checking a download

On a Windows machine, on the file that was downloaded:

```powershell
Get-AuthenticodeSignature .\AccessibleIDE-Setup.exe | Format-List Status, SignerCertificate
```

`Status` should read `Valid` and the subject should name SignPath Foundation.
Before signing is live this reads `NotSigned`, which is also what the workflow
asserts against once it is.

## Options that were considered and are not this

- **A self-signed certificate or a GPG signature.** Neither is trusted by
  SmartScreen for an `.exe`. A self-signed file looks signed to nobody but its
  author, and the warning is unchanged.
- **Let's Encrypt.** Issues TLS certificates for domains, not code signing
  certificates for executables. It cannot sign a `.exe` at all.
- **An EV certificate.** This is the one route to instant SmartScreen
  reputation, and it is not free: an EV certificate costs money each year and is
  issued on hardware that has to be present, which is the opposite of what a
  cloud build needs.
- **Azure Trusted Signing.** Around $10 a month, and the identity requirements
  are the part that bites: an organization generally needs a few years of
  verifiable history. Worth revisiting if SignPath does not work out.
- **Certum's open source programme.** Cheap rather than free, and the signing
  key lives in their cloud service, so it does work with CI. A fallback if
  SignPath is not granted.
