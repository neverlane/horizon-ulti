#!/usr/bin/env python3
"""Horizon-ulti: make launcher play work without a Microsoft account.

This is the fork's only source change. `upstream-sync.yml` resets `main` to
`ludovic111/horizon`, runs this script, runs the launcher tests and force-pushes
the result, so the fork follows upstream instead of fighting merge conflicts.

The patch removes the owner gate (the check that refuses Play while no account
in the launcher owns Minecraft: Java Edition):

  * `account::launch` never returns `NoOwner`; it returns the pass it built,
    with a session when an account could be renewed and nothing when not.
  * `Accounts::play_as_with` keeps an offline name without asking for an owner.
  * `owner_page::Launcher::asking_owner` is false, so the sign-in screen never
    covers the launcher on its own.

Microsoft sign-in stays: an account that owns the game still gets a session and
online-mode servers still need one. Nothing here touches the game binary.

Run it from the repository root after a clean upstream checkout:

    python3 tools/ulti/offline.py

It is idempotent and fails loudly if upstream moved the code it edits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCOUNT = ROOT / "launcher/src/account.rs"
OWNER_PAGE = ROOT / "launcher/src/owner_page.rs"


def edit(path: Path, old: str, new: str, *, done: str, what: str) -> bool:
    """Replace `old` with `new` once. `done` marks the edit as already applied."""
    text = path.read_text()
    if done in text:
        return False
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{path.relative_to(ROOT)}: expected one copy of {what}, found {count}. "
            "Upstream moved it; update tools/ulti/offline.py."
        )
    path.write_text(text.replace(old, new))
    return True


def regex_edit(path: Path, pattern: str, new: str, *, done: str, what: str) -> bool:
    """Like `edit`, for a block whose tail upstream rewrites now and then."""
    text = path.read_text()
    if done in text:
        return False
    replaced, count = re.subn(pattern, new, text, count=1, flags=re.M | re.S)
    if count != 1:
        raise SystemExit(
            f"{path.relative_to(ROOT)}: expected one copy of {what}, found {count}. "
            "Upstream moved it; update tools/ulti/offline.py."
        )
    path.write_text(replaced)
    return True


def patch_account() -> bool:
    changed = False
    # 1. An offline name no longer needs an account that owns the game.
    changed |= edit(
        ACCOUNT,
        """    /// [`Self::play_as`], where `offline_without_owner` (the window's hidden developer option,
    /// `backend::Settings::dev_offline`) lets an offline name play without an account that owns
    /// the game.
    pub fn play_as_with(
        &mut self,
        store: &dyn SecretStore,
        who: Player,
        offline_without_owner: bool,
    ) -> Result<(), String> {
        match who {
            Player::Microsoft(uuid) => {
                if !self.accounts.iter().any(|a| a.uuid == uuid) {
                    return Err("That account isn't signed in.".into());
                }
                self.selected = Some(uuid);
            }
            Player::Offline(name) => {
                if !offline_without_owner && !self.has_owner(store) {
                    return Err(OFFLINE_NEEDS_OWNER.into());
                }
                let name = self.add_offline(&name)?;
""",
        """    /// [`Self::play_as`]; offline names need no account (Horizon-ulti).
    pub fn play_as_with(
        &mut self,
        _store: &dyn SecretStore,
        who: Player,
        _offline_without_owner: bool,
    ) -> Result<(), String> {
        match who {
            Player::Microsoft(uuid) => {
                if !self.accounts.iter().any(|a| a.uuid == uuid) {
                    return Err("That account isn't signed in.".into());
                }
                self.selected = Some(uuid);
            }
            Player::Offline(name) => {
                let name = self.add_offline(&name)?;
""",
        done="        _store: &dyn SecretStore,\n        who: Player,\n        _offline_without_owner: bool,",
        what="the offline-name owner check in play_as_with",
    )

    # 2. The constant stays (the tests name it), but nothing reads it in the launcher now.
    changed |= edit(
        ACCOUNT,
        """const OFFLINE_NEEDS_OWNER: &str =
""",
        """#[allow(dead_code)] // Horizon-ulti: the gate is off, but the tests still name it.
const OFFLINE_NEEDS_OWNER: &str =
""",
        done="#[allow(dead_code)] // Horizon-ulti: the gate is off",
        what="the OFFLINE_NEEDS_OWNER constant",
    )

    # 3. launch() passes everyone: no owner means offline, not a refusal. The `Err` arm
    # grew a `keyring` field upstream, so match it loosely.
    changed |= regex_edit(
        ACCOUNT,
        r"^    if owned \{\n        Ok\(pass\)\n    \} else \{\n        Err\(NoOwner.*?\n    \}\n\}\n",
        """    // Horizon-ulti: offline play never needs an owner.
    let _ = owned;
    Ok(pass)
}
""",
        done="// Horizon-ulti: offline play never needs an owner.",
        what="the owner refusal at the end of launch",
    )

    # 4. The refusal was the only reader of the keyring message `launch` collects.
    changed |= edit(
        ACCOUNT,
        """/// The caller saves `accounts` (renewed names and skins).
pub fn launch(
""",
        """/// The caller saves `accounts` (renewed names and skins).
#[allow(unused_variables, unused_assignments)] // Horizon-ulti: the owner refusal is gone.
pub fn launch(
""",
        done="// Horizon-ulti: the owner refusal is gone.",
        what="the launch signature",
    )
    return changed


def patch_owner_page() -> bool:
    return edit(
        OWNER_PAGE,
        """    pub(crate) fn asking_owner(&self) -> bool {
        (self.owner_shown() == Some(false) || sign_in_preview())
            && (self.owner_screen_open || !self.settings.owner_notice_seen || sign_in_preview())
            && !self.asking_consent()
            && self.opening.is_none()
    }
""",
        """    pub(crate) fn asking_owner(&self) -> bool {
        // Horizon-ulti: the sign-in screen never covers the launcher on its own.
        false
    }
""",
        done="// Horizon-ulti: the sign-in screen never covers the launcher",
        what="the asking_owner condition",
    )


def main() -> int:
    changed = []
    if patch_account():
        changed.append("launcher/src/account.rs")
    if patch_owner_page():
        changed.append("launcher/src/owner_page.rs")
    if changed:
        print("patched: " + ", ".join(changed))
    else:
        print("already patched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
