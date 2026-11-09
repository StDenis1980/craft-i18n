//! The checker and craft-libs' `craft-i18n` runtime crate agree on how many plural forms each
//! locale in `locales/` takes. They disagreeing means a catalog CI passes has `@plural` rows the
//! apps skip, or the reverse. The checker takes the count from the crate (`locale::plural_forms`);
//! these check it from two other directions.

use craft_i18n::{Embedded, I18n};
use craft_i18n_tests::locale::plural_forms;

fn leak(text: String) -> &'static str {
    Box::leak(text.into_boxed_str())
}

/// Every locale directory in `locales/`.
fn locales() -> Vec<String> {
    let dir = craft_i18n_tests::repo_root().join("locales");
    let mut locales: Vec<String> = std::fs::read_dir(&dir)
        .unwrap()
        .map(|e| e.unwrap())
        .filter(|e| e.path().is_dir())
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .collect();
    locales.sort();
    assert!(locales.len() > 40, "{locales:?}");
    locales
}

/// The runtime crate's problems with one `@plural` row of `forms` forms for `locale`.
fn runtime_problems(locale: &str, forms: usize) -> Vec<String> {
    let translation = vec!["{n} x"; forms].join("|");
    let catalog = leak(format!("@plural\t{{n}} a|{{n}} b\t{translation}\n"));
    let embedded: &'static Embedded = Box::leak(Box::new([(leak(locale.to_owned()), catalog, "")]));
    let (i18n, mut problems) = I18n::new(embedded, &[]);
    problems.extend(i18n.check_all());
    problems
}

#[test]
fn plural_form_counts_match_the_runtime_crate() {
    let mut disagree = Vec::new();
    for locale in locales() {
        let Ok(n) = plural_forms(&locale) else {
            disagree.push(format!("{locale}: {:?}", plural_forms(&locale)));
            continue;
        };
        // The crate takes exactly `n` forms: `n` passes, one fewer and one more don't.
        let ok = runtime_problems(&locale, n);
        let fewer = n > 1 && runtime_problems(&locale, n - 1).is_empty();
        let more = runtime_problems(&locale, n + 1).is_empty();
        if !ok.is_empty() || fewer || more {
            disagree.push(format!("{locale}: checker {n}, runtime {ok:?}"));
        }
    }
    assert_eq!(disagree, Vec::<String>::new());
}

/// The crate, given the repository's own catalogs (`common.tsv` with each app's), skips no
/// `@plural` row the checker passed.
#[test]
fn the_runtime_crate_accepts_every_plural_row() {
    let root = craft_i18n_tests::repo_root().join("locales");
    let mut problems = Vec::new();
    for locale in locales() {
        let dir = root.join(&locale);
        let common = leak(std::fs::read_to_string(dir.join("common.tsv")).unwrap_or_default());
        let mut apps: Vec<_> = std::fs::read_dir(&dir)
            .unwrap()
            .map(|e| e.unwrap().path())
            .filter(|p| p.extension().is_some_and(|x| x == "tsv") && !p.ends_with("common.tsv"))
            .collect();
        apps.sort();
        for app in apps {
            let text = leak(std::fs::read_to_string(&app).unwrap());
            let embedded: &'static Embedded =
                Box::leak(Box::new([(leak(locale.clone()), common, text)]));
            let (i18n, new_problems) = I18n::new(embedded, &[]);
            problems.extend(new_problems);
            problems.extend(
                i18n.check_all()
                    .into_iter()
                    .filter(|p| p.contains("plural"))
                    .map(|p| format!("{}: {p}", app.display())),
            );
        }
    }
    assert_eq!(problems, Vec::<String>::new());
}

/// The comparison itself catches a wrong count.
#[test]
fn a_wrong_count_is_caught() {
    assert!(runtime_problems("fr", 2).is_empty());
    assert!(!runtime_problems("fr", 3).is_empty());
    assert!(!runtime_problems("ru", 2).is_empty());
    assert!(!runtime_problems("ckb", 1).is_empty());
    assert!(
        !runtime_problems("tlh", 1).is_empty(),
        "no CLDR plural rules"
    );
}
