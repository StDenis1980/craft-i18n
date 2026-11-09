# AGENTS.md

Shared translations for the Craft Apps: TSV catalogs in `locales/` and the checker CI runs.

- **Data, not code.** The lookup code is the `craft-i18n` crate in craft-libs
  ([ADR 0002](docs/adr/0002-runtime-in-craft-libs-data-in-craft-i18n.md)). This repo holds only
  data (the catalogs and Language data) and the checker (`crates/craft-i18n-tests`).
- **Catalogs:** the format and every rule CI checks are in `docs/catalog-format.md`; the words in
  `GLOSSARY.md`. Shared rows in `common.tsv` only grow, except for a correction
  ([ADR 0003](docs/adr/0003-shared-catalog-grows-additively.md)); an app changes one's wording with
  an override in its own `<app>.tsv`.
- **Clean room:** every translation is written from the plain meaning of the English. Never consult
  or copy another product's localisation, string table or translated interface. Language data
  (spelling dictionaries, hyphenation patterns) is the exception: unchanged open-licensed upstream
  files ([ADR 0004](docs/adr/0004-third-party-language-data.md)).
- **Credit:** new translations and migrated catalogs are recorded in `ATTRIBUTION.md`, including
  AI assistance and whether a native speaker reviewed them.
- **Never crash.** The checker's `lib.rs` denies `unwrap`, `expect`, `panic` and friends; the
  workspace forbids `unsafe`.
- **Before merging:** `cargo fmt --all --check`,
  `cargo clippy --workspace --all-targets --all-features -- -D warnings`, `cargo test --workspace`,
  `python3 -m unittest discover -s tools` (catalog sync/rekey helpers; always write/read TSV as UTF-8).
