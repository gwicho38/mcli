#![allow(clippy::useless_conversion)]
#![allow(clippy::uninlined_format_args)]

use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, Mutex};
use std::time::Duration;

#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum FileEventType {
    Created,
    Modified,
    Deleted,
    Renamed,
}

#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileEvent {
    #[pyo3(get)]
    pub event_type: FileEventType,
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub old_path: Option<String>, // For rename events
}

#[pyclass]
pub struct FileWatcher {
    watcher: Option<RecommendedWatcher>,
    event_receiver: Arc<Mutex<Option<Receiver<FileEvent>>>>,
    is_watching: bool,
    watch_paths: Vec<PathBuf>,
}

impl Default for FileWatcher {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl FileWatcher {
    #[new]
    pub fn new() -> Self {
        Self {
            watcher: None,
            event_receiver: Arc::new(Mutex::new(None)),
            is_watching: false,
            watch_paths: Vec::new(),
        }
    }

    #[pyo3(signature = (paths, recursive=None))]
    pub fn start_watching(&mut self, paths: Vec<String>, recursive: Option<bool>) -> PyResult<()> {
        if self.is_watching {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                "Watcher is already running",
            ));
        }

        let (tx, rx): (Sender<FileEvent>, Receiver<FileEvent>) = mpsc::channel();
        let tx = Arc::new(Mutex::new(tx));

        // Create watcher with optimized configuration
        let config = Config::default()
            .with_poll_interval(Duration::from_millis(100))
            .with_compare_contents(false); // Fast mode - only check metadata

        let mut watcher = RecommendedWatcher::new(
            move |res: Result<Event, notify::Error>| match res {
                Ok(event) => {
                    if let Some(file_event) = convert_notify_event(event) {
                        if let Ok(sender) = tx.lock() {
                            let _ = sender.send(file_event);
                        }
                    }
                }
                Err(e) => eprintln!("File watcher error: {:?}", e),
            },
            config,
        )
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to create watcher: {}",
                e
            ))
        })?;

        // Watch specified paths
        let recursive_mode = if recursive.unwrap_or(true) {
            RecursiveMode::Recursive
        } else {
            RecursiveMode::NonRecursive
        };

        for path_str in &paths {
            let path = Path::new(path_str);
            if !path.exists() {
                return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
                    format!("Path does not exist: {}", path_str),
                ));
            }

            watcher.watch(path, recursive_mode).map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "Failed to watch path {}: {}",
                    path_str, e
                ))
            })?;

            self.watch_paths.push(path.to_path_buf());
        }

        self.watcher = Some(watcher);
        *self.event_receiver.lock().unwrap() = Some(rx);
        self.is_watching = true;

        Ok(())
    }

    pub fn stop_watching(&mut self) -> PyResult<()> {
        if !self.is_watching {
            return Ok(());
        }

        self.watcher = None;
        *self.event_receiver.lock().unwrap() = None;
        self.is_watching = false;
        self.watch_paths.clear();

        Ok(())
    }

    #[pyo3(signature = (timeout_ms=None))]
    pub fn get_events(&self, timeout_ms: Option<u64>) -> PyResult<Vec<FileEvent>> {
        if !self.is_watching {
            return Ok(Vec::new());
        }

        let receiver = self.event_receiver.lock().unwrap();
        let rx = match receiver.as_ref() {
            Some(rx) => rx,
            None => return Ok(Vec::new()),
        };

        let mut events = Vec::new();
        let timeout = Duration::from_millis(timeout_ms.unwrap_or(100));

        // Collect all available events
        match rx.recv_timeout(timeout) {
            Ok(event) => {
                events.push(event);

                // Collect any additional events without blocking
                while let Ok(event) = rx.try_recv() {
                    events.push(event);
                }
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {
                // No events within timeout - this is normal
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Event receiver disconnected",
                ));
            }
        }

        Ok(events)
    }

    pub fn is_watching(&self) -> bool {
        self.is_watching
    }

    pub fn get_watched_paths(&self) -> Vec<String> {
        self.watch_paths
            .iter()
            .map(|p| p.to_string_lossy().to_string())
            .collect()
    }

    // Batch event processing for high-throughput scenarios
    #[pyo3(signature = (max_events=None, timeout_ms=None))]
    pub fn get_events_batch(
        &self,
        max_events: Option<usize>,
        timeout_ms: Option<u64>,
    ) -> PyResult<Vec<FileEvent>> {
        if !self.is_watching {
            return Ok(Vec::new());
        }

        let receiver = self.event_receiver.lock().unwrap();
        let rx = match receiver.as_ref() {
            Some(rx) => rx,
            None => return Ok(Vec::new()),
        };

        let mut events = Vec::new();
        let max_events = max_events.unwrap_or(1000);
        let timeout = Duration::from_millis(timeout_ms.unwrap_or(100));

        // Collect events up to max_events limit
        match rx.recv_timeout(timeout) {
            Ok(event) => {
                events.push(event);

                // Collect additional events without blocking
                while events.len() < max_events {
                    match rx.try_recv() {
                        Ok(event) => events.push(event),
                        Err(_) => break,
                    }
                }
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {
                // No events within timeout
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Event receiver disconnected",
                ));
            }
        }

        Ok(events)
    }

    // Filter events by file extension
    #[pyo3(signature = (extensions, timeout_ms=None))]
    pub fn get_filtered_events(
        &self,
        extensions: Vec<String>,
        timeout_ms: Option<u64>,
    ) -> PyResult<Vec<FileEvent>> {
        let all_events = self.get_events(timeout_ms)?;

        if extensions.is_empty() {
            return Ok(all_events);
        }

        let filtered_events: Vec<FileEvent> = all_events
            .into_iter()
            .filter(|event| {
                let path = Path::new(&event.path);
                if let Some(ext) = path.extension() {
                    let ext_str = ext.to_string_lossy().to_lowercase();
                    extensions.iter().any(|filter_ext| {
                        filter_ext.to_lowercase() == ext_str
                            || filter_ext.to_lowercase() == format!(".{}", ext_str)
                    })
                } else {
                    false
                }
            })
            .collect();

        Ok(filtered_events)
    }
}

fn convert_notify_event(event: Event) -> Option<FileEvent> {
    let paths = event.paths;
    if paths.is_empty() {
        return None;
    }

    let primary_path = paths[0].to_string_lossy().to_string();

    match event.kind {
        EventKind::Create(_) => Some(FileEvent {
            event_type: FileEventType::Created,
            path: primary_path,
            old_path: None,
        }),
        EventKind::Modify(_) => Some(FileEvent {
            event_type: FileEventType::Modified,
            path: primary_path,
            old_path: None,
        }),
        EventKind::Remove(_) => Some(FileEvent {
            event_type: FileEventType::Deleted,
            path: primary_path,
            old_path: None,
        }),
        EventKind::Other => {
            // Handle rename events
            if paths.len() == 2 {
                Some(FileEvent {
                    event_type: FileEventType::Renamed,
                    path: paths[1].to_string_lossy().to_string(),
                    old_path: Some(paths[0].to_string_lossy().to_string()),
                })
            } else {
                None
            }
        }
        _ => None,
    }
}

impl Drop for FileWatcher {
    fn drop(&mut self) {
        let _ = self.stop_watching();
    }
}
