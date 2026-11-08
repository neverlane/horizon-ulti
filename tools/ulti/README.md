# Horizon-ulti

A fork of [ludovic111/horizon](https://github.com/ludovic111/horizon) where the launcher
plays without a Microsoft account.

## What changes

One patch, `tools/ulti/offline.py`:

- `account::launch` never refuses Play for want of an owner. No account means an offline
  game with the name the game makes up; an account that owns Java still gets its session.
- `Accounts::play_as_with` keeps an offline name without an owner.
- The sign-in screen never covers the launcher on its own.

Microsoft sign-in is still there for online-mode servers. The game binary is untouched.

## How it stays current

`upstream-sync.yml` runs every 30 minutes:

1. fetch `ludovic111/horizon`'s `main`;
2. `git reset --hard upstream/main` (no merge, so no conflicts);
3. copy this folder and the two fork workflows back in;
4. run `tools/ulti/offline.py`;
5. run the launcher tests;
6. commit and force-push `main`.

If upstream moves the code the patch edits, step 4 fails loudly and `main` is not
touched; update `offline.py` then.

`ulti-build.yml` builds the launcher for Linux x86_64, macOS arm64 and Windows x64 after
each push and uploads the binaries as workflow artifacts.

The tests that pin the owner gate are skipped in both workflows: they assert the
behaviour this fork removes. The skip list is `GATE_TESTS` in each workflow:

- `a_no_from_the_services_blocks_at_once`
- `any_owner_opens_the_gate_and_the_one_who_plays_brings_the_session`
- `no_network_never_blocks_a_past_owner`
- `offline_names_play_only_beside_an_owner`
- `the_developer_option_off_is_the_owner_gate`
- `a_keyring_that_never_answers_ends_play_with_what_is_wrong`
- `the_cli_refuses_to_play_without_an_owner`
- `the_mcp_server_refuses_to_play_without_an_owner`

## Running it

```sh
cd launcher
cargo run --release
```

Offline name: `cargo run --release -- account offline NAME`. Building the game still
needs the player's own Minecraft files (`.local/horizon-client/26.3`).
