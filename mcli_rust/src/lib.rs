use pyo3::prelude::*;

mod command_parser;
mod file_watcher;
mod process_manager;
mod tfidf;

use command_parser::CommandMatcher;
use file_watcher::FileWatcher;
use process_manager::ProcessManager;
use tfidf::TfIdfVectorizer;

#[pymodule]
fn mcli_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TfIdfVectorizer>()?;
    m.add_class::<FileWatcher>()?;
    m.add_class::<CommandMatcher>()?;
    m.add_class::<ProcessManager>()?;
    Ok(())
}
