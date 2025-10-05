#![allow(clippy::useless_conversion)]

use pyo3::prelude::*;
use rayon::prelude::*;
use regex::Regex;
use rustc_hash::{FxHashMap, FxHashSet};
use unicode_normalization::UnicodeNormalization;

#[derive(Clone)]
struct Document {
    #[allow(dead_code)]
    id: usize,
    tokens: Vec<String>,
    token_counts: FxHashMap<String, usize>,
}

#[pyclass]
pub struct TfIdfVectorizer {
    vocabulary: FxHashMap<String, usize>,
    idf_scores: Vec<f64>,
    documents: Vec<Document>,
    max_features: Option<usize>,
    min_df: usize,
    max_df: f64,
    ngram_range: (usize, usize),
    stop_words: FxHashSet<String>,
    tokenizer: Regex,
}

#[pymethods]
impl TfIdfVectorizer {
    #[new]
    #[pyo3(signature = (max_features = None, min_df = 1, max_df = 1.0, ngram_range = (1, 1), stop_words = None))]
    pub fn new(
        max_features: Option<usize>,
        min_df: usize,
        max_df: f64,
        ngram_range: (usize, usize),
        stop_words: Option<Vec<String>>,
    ) -> Self {
        let stop_words_set = stop_words
            .unwrap_or_else(|| DEFAULT_STOP_WORDS.iter().map(|s| s.to_string()).collect())
            .into_iter()
            .collect();

        Self {
            vocabulary: FxHashMap::default(),
            idf_scores: Vec::new(),
            documents: Vec::new(),
            max_features,
            min_df,
            max_df,
            ngram_range,
            stop_words: stop_words_set,
            tokenizer: Regex::new(r"\b\w+\b").unwrap(),
        }
    }

    pub fn fit_transform(&mut self, documents: Vec<String>) -> PyResult<Vec<Vec<f64>>> {
        self.fit(documents.clone())?;
        self.transform(documents)
    }

    pub fn fit(&mut self, documents: Vec<String>) -> PyResult<()> {
        // Tokenize and preprocess documents in parallel
        self.documents = documents
            .par_iter()
            .enumerate()
            .map(|(id, doc)| self.preprocess_document(id, doc))
            .collect();

        // Build vocabulary
        self.build_vocabulary();

        // Calculate IDF scores
        self.calculate_idf_scores();

        Ok(())
    }

    pub fn transform(&self, documents: Vec<String>) -> PyResult<Vec<Vec<f64>>> {
        let processed_docs: Vec<Document> = documents
            .par_iter()
            .enumerate()
            .map(|(id, doc)| self.preprocess_document(id, doc))
            .collect();

        let vectors: Vec<Vec<f64>> = processed_docs
            .par_iter()
            .map(|doc| self.document_to_vector(doc))
            .collect();

        Ok(vectors)
    }

    pub fn similarity(&self, query: String, documents: Vec<String>) -> PyResult<Vec<f64>> {
        let query_doc = self.preprocess_document(0, &query);
        let query_vector = self.document_to_vector(&query_doc);

        let doc_vectors: Vec<Vec<f64>> = documents
            .par_iter()
            .enumerate()
            .map(|(id, doc)| {
                let processed = self.preprocess_document(id, doc);
                self.document_to_vector(&processed)
            })
            .collect();

        let similarities: Vec<f64> = doc_vectors
            .par_iter()
            .map(|doc_vec| cosine_similarity(&query_vector, doc_vec))
            .collect();

        Ok(similarities)
    }

    pub fn get_feature_names(&self) -> Vec<String> {
        let mut vocab_vec: Vec<(String, usize)> = self
            .vocabulary
            .iter()
            .map(|(term, &idx)| (term.clone(), idx))
            .collect();
        vocab_vec.sort_by_key(|(_, idx)| *idx);
        vocab_vec.into_iter().map(|(term, _)| term).collect()
    }
}

impl TfIdfVectorizer {
    fn preprocess_document(&self, id: usize, text: &str) -> Document {
        // Normalize unicode and convert to lowercase
        let normalized: String = text.nfc().collect::<String>().to_lowercase();

        // Tokenize
        let tokens: Vec<String> = self
            .tokenizer
            .find_iter(&normalized)
            .map(|m| m.as_str().to_string())
            .filter(|token| !self.stop_words.contains(token) && token.len() > 1)
            .collect();

        // Generate n-grams
        let ngrams = self.generate_ngrams(&tokens);

        // Count tokens
        let mut token_counts = FxHashMap::default();
        for token in &ngrams {
            *token_counts.entry(token.clone()).or_insert(0) += 1;
        }

        Document {
            id,
            tokens: ngrams,
            token_counts,
        }
    }

    fn generate_ngrams(&self, tokens: &[String]) -> Vec<String> {
        let mut ngrams = Vec::new();

        for n in self.ngram_range.0..=self.ngram_range.1 {
            if tokens.len() >= n {
                for window in tokens.windows(n) {
                    ngrams.push(window.join(" "));
                }
            }
        }

        ngrams
    }

    fn build_vocabulary(&mut self) {
        // Count document frequencies
        let mut doc_frequencies: FxHashMap<String, usize> = FxHashMap::default();

        for doc in &self.documents {
            let unique_tokens: FxHashSet<String> = doc.tokens.iter().cloned().collect();
            for token in unique_tokens {
                *doc_frequencies.entry(token).or_insert(0) += 1;
            }
        }

        // Filter by min_df and max_df
        let num_docs = self.documents.len() as f64;
        let max_df_count = (self.max_df * num_docs) as usize;

        let mut valid_terms: Vec<(String, usize)> = doc_frequencies
            .into_iter()
            .filter(|(_, freq)| *freq >= self.min_df && *freq <= max_df_count)
            .collect();

        // Sort by document frequency (descending) for feature selection
        valid_terms.sort_by(|(_, freq1), (_, freq2)| freq2.cmp(freq1));

        // Apply max_features limit
        if let Some(max_feat) = self.max_features {
            valid_terms.truncate(max_feat);
        }

        // Build vocabulary mapping
        self.vocabulary = valid_terms
            .into_iter()
            .enumerate()
            .map(|(idx, (term, _))| (term, idx))
            .collect();
    }

    fn calculate_idf_scores(&mut self) {
        let num_docs = self.documents.len() as f64;
        self.idf_scores = vec![0.0; self.vocabulary.len()];

        for (term, &idx) in &self.vocabulary {
            let doc_freq = self
                .documents
                .iter()
                .filter(|doc| doc.token_counts.contains_key(term))
                .count() as f64;

            // IDF = log(N / df) + 1 (smooth IDF)
            self.idf_scores[idx] = (num_docs / doc_freq).ln() + 1.0;
        }
    }

    fn document_to_vector(&self, doc: &Document) -> Vec<f64> {
        let mut vector = vec![0.0; self.vocabulary.len()];
        let total_tokens = doc.tokens.len() as f64;

        for (term, &count) in &doc.token_counts {
            if let Some(&idx) = self.vocabulary.get(term) {
                // TF = (term frequency) / (total terms in document)
                let tf = count as f64 / total_tokens;
                let idf = self.idf_scores[idx];
                vector[idx] = tf * idf;
            }
        }

        // L2 normalization
        let norm = vector.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm > 0.0 {
            for val in &mut vector {
                *val /= norm;
            }
        }

        vector
    }
}

fn cosine_similarity(vec1: &[f64], vec2: &[f64]) -> f64 {
    let dot_product: f64 = vec1.iter().zip(vec2.iter()).map(|(a, b)| a * b).sum();
    let norm1: f64 = vec1.iter().map(|x| x * x).sum::<f64>().sqrt();
    let norm2: f64 = vec2.iter().map(|x| x * x).sum::<f64>().sqrt();

    if norm1 == 0.0 || norm2 == 0.0 {
        0.0
    } else {
        dot_product / (norm1 * norm2)
    }
}

// Common English stop words
const DEFAULT_STOP_WORDS: &[&str] = &[
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from", "has", "he", "in",
    "is", "it", "its", "of", "on", "that", "the", "to", "was", "will", "with", "the", "this",
    "but", "they", "have", "had", "what", "said", "each", "which", "their", "time", "if", "up",
    "out", "many", "then", "them", "these", "so", "some", "her", "would", "make", "like", "into",
    "him", "has", "two", "more", "very", "after", "our", "just", "first", "all", "any", "my",
    "now", "such", "before", "here", "through", "when", "where", "how", "your", "most", "other",
    "take", "than", "only", "think", "also", "back", "could", "good", "should", "still", "being",
    "made", "much", "new", "way", "well", "own", "see", "get", "may", "say", "come", "use",
    "during", "without",
];
