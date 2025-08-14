use pyo3::prelude::*;

mod tfidf;
mod file_watcher;
mod command_parser;
mod process_manager;

use tfidf::TfIdfVectorizer;
use file_watcher::FileWatcher;
use command_parser::CommandMatcher;
use process_manager::ProcessManager;

#[pymodule]
fn mcli_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TfIdfVectorizer>()?;
    m.add_class::<FileWatcher>()?;
    m.add_class::<CommandMatcher>()?;
    m.add_class::<ProcessManager>()?;
    Ok(())
}