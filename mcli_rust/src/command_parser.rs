#![allow(clippy::useless_conversion)]

use pyo3::prelude::*;
use regex::Regex;
use rustc_hash::{FxHashMap, FxHashSet};
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use unicode_normalization::UnicodeNormalization;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct Command {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub description: String,
    #[pyo3(get, set)]
    pub code: String,
    #[pyo3(get, set)]
    pub language: String,
    #[pyo3(get, set)]
    pub group: Option<String>,
    #[pyo3(get, set)]
    pub tags: Vec<String>,
    #[pyo3(get, set)]
    pub execution_count: i32,
}

#[pymethods]
impl Command {
    #[new]
    #[pyo3(signature = (id, name, description, code, language, group=None, tags=None, execution_count=None))]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        id: String,
        name: String,
        description: String,
        code: String,
        language: String,
        group: Option<String>,
        tags: Option<Vec<String>>,
        execution_count: Option<i32>,
    ) -> Self {
        Self {
            id,
            name,
            description,
            code,
            language,
            group,
            tags: tags.unwrap_or_default(),
            execution_count: execution_count.unwrap_or(0),
        }
    }
}

#[derive(Debug, Clone)]
#[pyclass]
pub struct MatchResult {
    #[pyo3(get)]
    pub command: Command,
    #[pyo3(get)]
    pub score: f64,
    #[pyo3(get)]
    pub match_type: String,
    #[pyo3(get)]
    pub matched_fields: Vec<String>,
}

#[pymethods]
impl MatchResult {
    #[new]
    pub fn new(
        command: Command,
        score: f64,
        match_type: String,
        matched_fields: Vec<String>,
    ) -> Self {
        Self {
            command,
            score,
            match_type,
            matched_fields,
        }
    }
}

#[pyclass]
pub struct CommandMatcher {
    commands: Vec<Command>,
    name_index: FxHashMap<String, Vec<usize>>,
    tag_index: FxHashMap<String, Vec<usize>>,
    word_index: FxHashMap<String, Vec<usize>>,
    tokenizer: Regex,
    fuzzy_threshold: f64,
}

#[pymethods]
impl CommandMatcher {
    #[new]
    #[pyo3(signature = (fuzzy_threshold = 0.3))]
    pub fn new(fuzzy_threshold: f64) -> Self {
        Self {
            commands: Vec::new(),
            name_index: FxHashMap::default(),
            tag_index: FxHashMap::default(),
            word_index: FxHashMap::default(),
            tokenizer: Regex::new(r"\b\w+\b").unwrap(),
            fuzzy_threshold,
        }
    }

    #[allow(clippy::useless_conversion)]
    pub fn add_commands(&mut self, commands: Vec<Command>) -> PyResult<()> {
        for command in commands {
            self.add_command(command)?;
        }
        Ok(())
    }

    #[allow(clippy::useless_conversion)]
    pub fn add_command(&mut self, command: Command) -> PyResult<()> {
        let index = self.commands.len();

        // Index by name
        let normalized_name = normalize_text(&command.name);
        self.name_index
            .entry(normalized_name)
            .or_default()
            .push(index);

        // Index by tags
        for tag in &command.tags {
            let normalized_tag = normalize_text(tag);
            self.tag_index
                .entry(normalized_tag)
                .or_default()
                .push(index);
        }

        // Index by words in name and description
        let text = format!("{} {}", command.name, command.description);
        let words = self.extract_words(&text);
        for word in words {
            self.word_index.entry(word).or_default().push(index);
        }

        self.commands.push(command);
        Ok(())
    }

    #[pyo3(signature = (query, limit=None))]
    #[allow(clippy::useless_conversion)]
    pub fn search(&self, query: String, limit: Option<usize>) -> PyResult<Vec<MatchResult>> {
        if self.commands.is_empty() {
            return Ok(Vec::new());
        }

        let normalized_query = normalize_text(&query);
        let query_words = self.extract_words(&query);
        let limit = limit.unwrap_or(10);

        let mut results: Vec<MatchResult> = Vec::new();

        // 1. Exact name matches (highest priority)
        if let Some(indices) = self.name_index.get(&normalized_query) {
            for &idx in indices {
                results.push(MatchResult::new(
                    self.commands[idx].clone(),
                    1.0,
                    "exact_name".to_string(),
                    vec!["name".to_string()],
                ));
            }
        }

        // 2. Prefix name matches
        for (name, indices) in &self.name_index {
            if name.starts_with(&normalized_query) && name != &normalized_query {
                for &idx in indices {
                    results.push(MatchResult::new(
                        self.commands[idx].clone(),
                        0.9,
                        "prefix_name".to_string(),
                        vec!["name".to_string()],
                    ));
                }
            }
        }

        // 3. Tag matches
        if let Some(indices) = self.tag_index.get(&normalized_query) {
            for &idx in indices {
                results.push(MatchResult::new(
                    self.commands[idx].clone(),
                    0.8,
                    "tag_match".to_string(),
                    vec!["tags".to_string()],
                ));
            }
        }

        // 4. Word-based matches
        let mut word_scores: FxHashMap<usize, f64> = FxHashMap::default();
        for word in &query_words {
            if let Some(indices) = self.word_index.get(word) {
                for &idx in indices {
                    *word_scores.entry(idx).or_insert(0.0) += 1.0 / query_words.len() as f64;
                }
            }
        }

        for (idx, score) in word_scores {
            if score >= self.fuzzy_threshold {
                let mut matched_fields = Vec::new();
                let command = &self.commands[idx];

                // Check which fields matched
                let name_words = self.extract_words(&command.name);
                let desc_words = self.extract_words(&command.description);

                for word in &query_words {
                    if name_words.contains(word) {
                        matched_fields.push("name".to_string());
                    }
                    if desc_words.contains(word) {
                        matched_fields.push("description".to_string());
                    }
                }

                matched_fields.sort();
                matched_fields.dedup();

                results.push(MatchResult::new(
                    command.clone(),
                    score * 0.7, // Lower priority than exact matches
                    "word_match".to_string(),
                    matched_fields,
                ));
            }
        }

        // 5. Fuzzy string matching for partial matches
        let fuzzy_matches = self.fuzzy_match(&normalized_query, limit * 2);
        results.extend(fuzzy_matches);

        // Remove duplicates and sort by score
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));

        // Remove duplicates by command ID
        let mut seen_ids: FxHashSet<String> = FxHashSet::default();
        results.retain(|result| seen_ids.insert(result.command.id.clone()));

        // Apply limit
        results.truncate(limit);

        Ok(results)
    }

    #[pyo3(signature = (tags, limit=None))]
    #[allow(clippy::useless_conversion)]
    pub fn search_by_tags(
        &self,
        tags: Vec<String>,
        limit: Option<usize>,
    ) -> PyResult<Vec<MatchResult>> {
        let limit = limit.unwrap_or(10);
        let mut results: Vec<MatchResult> = Vec::new();
        let mut command_scores: FxHashMap<usize, (f64, Vec<String>)> = FxHashMap::default();

        for tag in &tags {
            let normalized_tag = normalize_text(tag);
            if let Some(indices) = self.tag_index.get(&normalized_tag) {
                for &idx in indices {
                    let (score, matched_tags) =
                        command_scores.entry(idx).or_insert((0.0, Vec::new()));
                    *score += 1.0 / tags.len() as f64;
                    matched_tags.push(tag.clone());
                }
            }
        }

        for (idx, (score, matched_tags)) in command_scores {
            results.push(MatchResult::new(
                self.commands[idx].clone(),
                score,
                "tag_search".to_string(),
                matched_tags,
            ));
        }

        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        results.truncate(limit);

        Ok(results)
    }

    #[pyo3(signature = (group, limit=None))]
    #[allow(clippy::useless_conversion)]
    pub fn search_by_group(
        &self,
        group: String,
        limit: Option<usize>,
    ) -> PyResult<Vec<MatchResult>> {
        let limit = limit.unwrap_or(10);
        let normalized_group = normalize_text(&group);

        let results: Vec<MatchResult> = self
            .commands
            .iter()
            .filter(|cmd| {
                cmd.group
                    .as_ref()
                    .map(|g| normalize_text(g) == normalized_group)
                    .unwrap_or(false)
            })
            .take(limit)
            .map(|cmd| {
                MatchResult::new(
                    cmd.clone(),
                    1.0,
                    "group_match".to_string(),
                    vec!["group".to_string()],
                )
            })
            .collect();

        Ok(results)
    }

    #[pyo3(signature = (limit=None))]
    #[allow(clippy::useless_conversion)]
    pub fn get_popular_commands(&self, limit: Option<usize>) -> PyResult<Vec<MatchResult>> {
        let limit = limit.unwrap_or(10);
        let mut commands_with_scores: Vec<_> = self
            .commands
            .iter()
            .map(|cmd| (cmd, cmd.execution_count as f64))
            .collect();

        commands_with_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal));

        let results: Vec<MatchResult> = commands_with_scores
            .into_iter()
            .take(limit)
            .map(|(cmd, score)| {
                MatchResult::new(
                    cmd.clone(),
                    score / 100.0, // Normalize score
                    "popularity".to_string(),
                    vec!["execution_count".to_string()],
                )
            })
            .collect();

        Ok(results)
    }

    #[allow(clippy::useless_conversion)]
    pub fn clear(&mut self) -> PyResult<()> {
        self.commands.clear();
        self.name_index.clear();
        self.tag_index.clear();
        self.word_index.clear();
        Ok(())
    }

    pub fn get_command_count(&self) -> usize {
        self.commands.len()
    }

    pub fn get_all_tags(&self) -> Vec<String> {
        self.tag_index.keys().cloned().collect()
    }

    pub fn get_all_groups(&self) -> Vec<String> {
        let mut groups: FxHashSet<String> = FxHashSet::default();
        for cmd in &self.commands {
            if let Some(group) = &cmd.group {
                groups.insert(normalize_text(group));
            }
        }
        groups.into_iter().collect()
    }
}

impl CommandMatcher {
    fn extract_words(&self, text: &str) -> Vec<String> {
        let normalized = normalize_text(text);
        self.tokenizer
            .find_iter(&normalized)
            .map(|m| m.as_str().to_string())
            .filter(|word| word.len() > 1) // Filter out single characters
            .collect()
    }

    fn fuzzy_match(&self, query: &str, limit: usize) -> Vec<MatchResult> {
        let query_chars: Vec<char> = query.chars().collect();
        let mut matches = Vec::new();

        for command in self.commands.iter() {
            let name_score = fuzzy_score(&query_chars, &command.name);
            let desc_score = fuzzy_score(&query_chars, &command.description);

            let max_score = name_score.max(desc_score);

            if max_score >= self.fuzzy_threshold {
                let matched_fields = if name_score >= desc_score {
                    vec!["name".to_string()]
                } else {
                    vec!["description".to_string()]
                };

                matches.push(MatchResult::new(
                    command.clone(),
                    max_score * 0.5, // Lower priority for fuzzy matches
                    "fuzzy_match".to_string(),
                    matched_fields,
                ));
            }
        }

        matches.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        matches.truncate(limit);
        matches
    }
}

fn normalize_text(text: &str) -> String {
    text.nfc()
        .collect::<String>()
        .to_lowercase()
        .chars()
        .filter(|c| c.is_alphanumeric() || c.is_whitespace())
        .collect()
}

fn fuzzy_score(query_chars: &[char], target: &str) -> f64 {
    let target_chars: Vec<char> = normalize_text(target).chars().collect();

    if query_chars.is_empty() || target_chars.is_empty() {
        return 0.0;
    }

    let mut query_idx = 0;
    let mut matches = 0;

    for target_char in &target_chars {
        if query_idx < query_chars.len() && *target_char == query_chars[query_idx] {
            matches += 1;
            query_idx += 1;
        }
    }

    if query_idx == query_chars.len() {
        // All query characters found in order
        matches as f64 / target_chars.len() as f64
    } else {
        0.0
    }
}
