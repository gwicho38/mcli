#![allow(clippy::useless_conversion)]
#![allow(clippy::uninlined_format_args)]

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::{mpsc, Mutex};
use tokio::time::{timeout, Duration};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[allow(dead_code)]
pub enum ProcessStatus {
    Created,
    Running,
    Completed,
    Failed,
    Killed,
    Timeout,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct ProcessInfo {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub command: String,
    #[pyo3(get, set)]
    pub args: Vec<String>,
    #[pyo3(get, set)]
    pub working_dir: Option<String>,
    #[pyo3(get, set)]
    pub environment: Option<HashMap<String, String>>,
    #[pyo3(get, set)]
    pub status: String,
    #[pyo3(get, set)]
    pub pid: Option<u32>,
    #[pyo3(get, set)]
    pub exit_code: Option<i32>,
    #[pyo3(get, set)]
    pub stdout: Vec<String>,
    #[pyo3(get, set)]
    pub stderr: Vec<String>,
    #[pyo3(get, set)]
    pub created_at: String,
    #[pyo3(get, set)]
    pub started_at: Option<String>,
    #[pyo3(get, set)]
    pub finished_at: Option<String>,
}

#[pymethods]
impl ProcessInfo {
    #[new]
    #[pyo3(signature = (name, command, args, working_dir=None, environment=None))]
    pub fn new(
        name: String,
        command: String,
        args: Vec<String>,
        working_dir: Option<String>,
        environment: Option<HashMap<String, String>>,
    ) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            name,
            command,
            args,
            working_dir,
            environment,
            status: "Created".to_string(),
            pid: None,
            exit_code: None,
            stdout: Vec::new(),
            stderr: Vec::new(),
            created_at: chrono::Utc::now().to_rfc3339(),
            started_at: None,
            finished_at: None,
        }
    }

    pub fn get_status(&self) -> String {
        self.status.clone()
    }

    pub fn is_running(&self) -> bool {
        self.status == "Running"
    }

    pub fn is_finished(&self) -> bool {
        matches!(
            self.status.as_str(),
            "Completed" | "Failed" | "Killed" | "Timeout"
        )
    }
}

struct ManagedProcess {
    info: Arc<Mutex<ProcessInfo>>,
    child: Option<Child>,
    #[allow(dead_code)]
    stdout_receiver: Option<mpsc::Receiver<String>>,
    #[allow(dead_code)]
    stderr_receiver: Option<mpsc::Receiver<String>>,
}

#[pyclass]
pub struct ProcessManager {
    processes: Arc<Mutex<HashMap<String, ManagedProcess>>>,
    runtime: Arc<tokio::runtime::Runtime>,
}

#[pymethods]
impl ProcessManager {
    #[new]
    pub fn new() -> PyResult<Self> {
        let runtime = tokio::runtime::Runtime::new().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to create async runtime: {}",
                e
            ))
        })?;

        Ok(Self {
            processes: Arc::new(Mutex::new(HashMap::new())),
            runtime: Arc::new(runtime),
        })
    }

    #[pyo3(signature = (name, command, args, working_dir=None, environment=None, timeout_seconds=None))]
    pub fn start_process(
        &self,
        name: String,
        command: String,
        args: Vec<String>,
        working_dir: Option<String>,
        environment: Option<HashMap<String, String>>,
        timeout_seconds: Option<u64>,
    ) -> PyResult<String> {
        let process_info = ProcessInfo::new(name, command, args, working_dir, environment);
        let _process_id = process_info.id.clone();

        let processes = self.processes.clone();
        let timeout_duration = timeout_seconds.map(Duration::from_secs);

        self.runtime.block_on(async move {
            Self::start_process_async(processes, process_info, timeout_duration).await
        })
    }

    pub fn kill_process(&self, process_id: String) -> PyResult<bool> {
        let processes = self.processes.clone();

        self.runtime.block_on(async move {
            let mut processes = processes.lock().await;

            if let Some(managed_process) = processes.get_mut(&process_id) {
                if let Some(ref mut child) = managed_process.child {
                    match child.kill().await {
                        Ok(_) => {
                            let mut info = managed_process.info.lock().await;
                            info.status = "Killed".to_string();
                            info.finished_at = Some(chrono::Utc::now().to_rfc3339());
                            Ok(true)
                        }
                        Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                            "Failed to kill process: {}",
                            e
                        ))),
                    }
                } else {
                    Ok(false)
                }
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                    "Process not found: {}",
                    process_id
                )))
            }
        })
    }

    pub fn get_process_info(&self, process_id: String) -> PyResult<ProcessInfo> {
        let processes = self.processes.clone();

        self.runtime.block_on(async move {
            let processes = processes.lock().await;

            if let Some(managed_process) = processes.get(&process_id) {
                let info = managed_process.info.lock().await;
                Ok(info.clone())
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                    "Process not found: {}",
                    process_id
                )))
            }
        })
    }

    pub fn list_processes(&self) -> PyResult<Vec<ProcessInfo>> {
        let processes = self.processes.clone();

        self.runtime.block_on(async move {
            let processes = processes.lock().await;
            let mut result = Vec::new();

            for managed_process in processes.values() {
                let info = managed_process.info.lock().await;
                result.push(info.clone());
            }

            Ok(result)
        })
    }

    #[pyo3(signature = (process_id, timeout_seconds=None))]
    pub fn wait_for_process(
        &self,
        process_id: String,
        timeout_seconds: Option<u64>,
    ) -> PyResult<ProcessInfo> {
        let processes = self.processes.clone();
        let timeout_duration = timeout_seconds.map(Duration::from_secs);

        self.runtime.block_on(async move {
            let mut processes = processes.lock().await;

            if let Some(managed_process) = processes.get_mut(&process_id) {
                if let Some(ref mut child) = managed_process.child {
                    let wait_future = child.wait();

                    let result = if let Some(timeout_dur) = timeout_duration {
                        timeout(timeout_dur, wait_future).await
                    } else {
                        Ok(wait_future.await)
                    };

                    match result {
                        Ok(Ok(exit_status)) => {
                            let mut info = managed_process.info.lock().await;
                            info.exit_code = exit_status.code();
                            info.status = if exit_status.success() {
                                "Completed".to_string()
                            } else {
                                "Failed".to_string()
                            };
                            info.finished_at = Some(chrono::Utc::now().to_rfc3339());
                            Ok(info.clone())
                        }
                        Ok(Err(e)) => {
                            let mut info = managed_process.info.lock().await;
                            info.status = "Failed".to_string();
                            info.finished_at = Some(chrono::Utc::now().to_rfc3339());
                            Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                                "Process failed: {}",
                                e
                            )))
                        }
                        Err(_) => {
                            let mut info = managed_process.info.lock().await;
                            info.status = "Timeout".to_string();
                            info.finished_at = Some(chrono::Utc::now().to_rfc3339());
                            Err(PyErr::new::<pyo3::exceptions::PyTimeoutError, _>(
                                "Process timed out",
                            ))
                        }
                    }
                } else {
                    let info = managed_process.info.lock().await;
                    Ok(info.clone())
                }
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                    "Process not found: {}",
                    process_id
                )))
            }
        })
    }

    pub fn cleanup_finished(&self) -> PyResult<Vec<String>> {
        let processes = self.processes.clone();

        self.runtime.block_on(async move {
            let mut processes = processes.lock().await;
            let mut removed_ids = Vec::new();

            let finished_ids: Vec<String> = {
                let mut finished = Vec::new();
                for (id, managed_process) in processes.iter() {
                    let info = managed_process.info.lock().await;
                    if info.is_finished() {
                        finished.push(id.clone());
                    }
                }
                finished
            };

            for id in finished_ids {
                processes.remove(&id);
                removed_ids.push(id);
            }

            Ok(removed_ids)
        })
    }

    pub fn get_running_count(&self) -> PyResult<usize> {
        let processes = self.processes.clone();

        self.runtime.block_on(async move {
            let processes = processes.lock().await;
            let mut count = 0;

            for managed_process in processes.values() {
                let info = managed_process.info.lock().await;
                if info.is_running() {
                    count += 1;
                }
            }

            Ok(count)
        })
    }
}

impl ProcessManager {
    async fn start_process_async(
        processes: Arc<Mutex<HashMap<String, ManagedProcess>>>,
        mut process_info: ProcessInfo,
        timeout_duration: Option<Duration>,
    ) -> PyResult<String> {
        let process_id = process_info.id.clone();

        // Build command
        let mut cmd = Command::new(&process_info.command);
        cmd.args(&process_info.args);

        if let Some(ref wd) = process_info.working_dir {
            cmd.current_dir(PathBuf::from(wd));
        }

        if let Some(ref env) = process_info.environment {
            cmd.envs(env);
        }

        // Configure stdio
        cmd.stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped());

        // Start process
        let mut child = cmd.spawn().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to spawn process: {}",
                e
            ))
        })?;

        process_info.pid = child.id();
        process_info.status = "Running".to_string();
        process_info.started_at = Some(chrono::Utc::now().to_rfc3339());

        // Setup stdout/stderr capture
        let stdout = child.stdout.take().unwrap();
        let stderr = child.stderr.take().unwrap();

        let (stdout_tx, stdout_rx) = mpsc::channel(1000);
        let (stderr_tx, stderr_rx) = mpsc::channel(1000);

        let process_info_arc = Arc::new(Mutex::new(process_info));
        let info_clone = process_info_arc.clone();

        // Spawn stdout reader
        let stdout_info = info_clone.clone();
        tokio::spawn(async move {
            let mut reader = BufReader::new(stdout);
            let mut line = String::new();

            while let Ok(n) = reader.read_line(&mut line).await {
                if n == 0 {
                    break;
                }

                let line_trimmed = line.trim_end().to_string();
                let _ = stdout_tx.send(line_trimmed.clone()).await;

                // Store in process info
                let mut info = stdout_info.lock().await;
                info.stdout.push(line_trimmed);

                line.clear();
            }
        });

        // Spawn stderr reader
        let stderr_info = info_clone.clone();
        tokio::spawn(async move {
            let mut reader = BufReader::new(stderr);
            let mut line = String::new();

            while let Ok(n) = reader.read_line(&mut line).await {
                if n == 0 {
                    break;
                }

                let line_trimmed = line.trim_end().to_string();
                let _ = stderr_tx.send(line_trimmed.clone()).await;

                // Store in process info
                let mut info = stderr_info.lock().await;
                info.stderr.push(line_trimmed);

                line.clear();
            }
        });

        // Create managed process
        let managed_process = ManagedProcess {
            info: process_info_arc.clone(),
            child: Some(child),
            stdout_receiver: Some(stdout_rx),
            stderr_receiver: Some(stderr_rx),
        };

        // Store in processes map
        let mut processes_guard = processes.lock().await;
        processes_guard.insert(process_id.clone(), managed_process);

        // If timeout is specified, spawn a task to handle it
        if let Some(timeout_dur) = timeout_duration {
            let processes_timeout = processes.clone();
            let process_id_timeout = process_id.clone();

            tokio::spawn(async move {
                tokio::time::sleep(timeout_dur).await;

                let mut processes = processes_timeout.lock().await;
                if let Some(managed_process) = processes.get_mut(&process_id_timeout) {
                    let info = managed_process.info.lock().await;
                    if info.is_running() {
                        drop(info); // Release lock before killing

                        if let Some(ref mut child) = managed_process.child {
                            let _ = child.kill().await;
                        }

                        let mut info = managed_process.info.lock().await;
                        info.status = "Timeout".to_string();
                        info.finished_at = Some(chrono::Utc::now().to_rfc3339());
                    }
                }
            });
        }

        Ok(process_id)
    }
}
