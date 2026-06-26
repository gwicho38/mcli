## Rust Extensions

### Performance-critical code lives in mcli_rust/ (PyO3)
Performance-critical components (TF-IDF, file watching) are implemented in `mcli_rust/` as a PyO3 extension module: crate-type `cdylib`, Rust edition 2021, pyo3 0.22 with `extension-module`. Key deps: tokio (full), notify, serde/serde_json, rayon, regex. Build locally with `maturin develop` in `mcli_rust/`. Confidence 80.
