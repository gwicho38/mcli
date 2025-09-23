import json
import logging
from typing import Any, Dict, Optional

import ollama

from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml

logger = get_logger(__name__)


class GitCommitAIService:
    """AI service for generating intelligent git commit messages"""

    def __init__(self):
        self.config = self._load_config()
        self.model_name = self.config.get("model", "phi3-mini")
        self.temperature = float(
            self.config.get("temperature", 0.3)
        )  # Lower temp for more consistent commits
        self.ollama_base_url = self.config.get("ollama_base_url", "http://localhost:11434")

    def _load_config(self) -> Dict[str, Any]:
        """Load LLM configuration from config.toml"""
        try:
            config = read_from_toml("config.toml", "llm") or {}

            if not config:
                # Default configuration for git commits
                config = {
                    "provider": "local",
                    "model": "phi3-mini",
                    "temperature": 0.3,
                    "ollama_base_url": "http://localhost:11434",
                }

            return config
        except Exception as e:
            logger.warning(f"Could not load config, using defaults: {e}")
            return {
                "provider": "local",
                "model": "phi3-mini",
                "temperature": 0.3,
                "ollama_base_url": "http://localhost:11434",
            }

    def _analyze_file_patterns(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze file patterns to understand the scope of changes"""
        analysis = {"languages": set(), "categories": set(), "scope": "unknown", "confidence": 0.0}

        all_files = (
            changes["changes"]["added"]
            + changes["changes"]["modified"]
            + changes["changes"]["deleted"]
            + changes["changes"]["renamed"]
        )

        # Language detection
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".html": "html",
            ".css": "css",
            ".scss": "sass",
            ".md": "markdown",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".json": "json",
            ".toml": "toml",
            ".dockerfile": "docker",
            ".sql": "sql",
        }

        # Category detection
        category_patterns = {
            "tests": ["test_", "_test", "tests/", "/test/", ".test.", "spec_", "_spec"],
            "docs": [".md", "README", "CHANGELOG", "docs/", "/doc/"],
            "config": [".toml", ".yml", ".yaml", ".json", "config", ".env", "settings"],
            "build": [
                "Dockerfile",
                "requirements",
                "package.json",
                "cargo.toml",
                "pom.xml",
                "build",
                "makefile",
            ],
            "frontend": [
                ".html",
                ".css",
                ".scss",
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
                "assets/",
                "static/",
            ],
            "backend": [".py", ".go", ".rs", ".java", ".cpp", "api/", "server/", "backend/"],
            "database": [".sql", "migration", "schema", "models/", "db/"],
            "infra": ["docker", "deploy", "infrastructure", ".tf", "kubernetes", "helm"],
        }

        for file in all_files:
            file_lower = file.lower()

            # Detect languages
            for ext, lang in language_map.items():
                if file_lower.endswith(ext):
                    analysis["languages"].add(lang)
                    break

            # Detect categories
            for category, patterns in category_patterns.items():
                if any(pattern in file_lower for pattern in patterns):
                    analysis["categories"].add(category)

        # Determine scope
        if len(all_files) == 1:
            analysis["scope"] = "single"
            analysis["confidence"] = 0.9
        elif len(all_files) <= 5:
            analysis["scope"] = "focused"
            analysis["confidence"] = 0.8
        elif len(all_files) <= 15:
            analysis["scope"] = "moderate"
            analysis["confidence"] = 0.7
        else:
            analysis["scope"] = "broad"
            analysis["confidence"] = 0.6

        # Convert sets to lists for JSON serialization
        analysis["languages"] = list(analysis["languages"])
        analysis["categories"] = list(analysis["categories"])

        return analysis

    def _create_commit_prompt(
        self, changes: Dict[str, Any], diff_content: str, analysis: Dict[str, Any]
    ) -> str:
        """Create a detailed prompt for AI commit message generation"""

        # Truncate diff if too long (keep first 2000 chars)
        truncated_diff = diff_content[:2000] + "..." if len(diff_content) > 2000 else diff_content

        prompt = f"""You are an expert software developer writing git commit messages following conventional commit standards.

CHANGE ANALYSIS:
- Files changed: {changes['total_files']}
- New files: {len(changes['changes']['added'])}  
- Modified files: {len(changes['changes']['modified'])}
- Deleted files: {len(changes['changes']['deleted'])}
- Languages: {', '.join(analysis['languages']) if analysis['languages'] else 'unknown'}
- Categories: {', '.join(analysis['categories']) if analysis['categories'] else 'general'}
- Scope: {analysis['scope']}

FILE DETAILS:
Added: {', '.join(changes['changes']['added'][:10])}{'...' if len(changes['changes']['added']) > 10 else ''}
Modified: {', '.join(changes['changes']['modified'][:10])}{'...' if len(changes['changes']['modified']) > 10 else ''}
Deleted: {', '.join(changes['changes']['deleted'][:10])}{'...' if len(changes['changes']['deleted']) > 10 else ''}

CODE DIFF SAMPLE:
{truncated_diff}

Generate a conventional commit message following this format:
<type>[optional scope]: <description>

[optional body]

Types: feat, fix, docs, style, refactor, test, chore, build, ci, perf
Scope: component/module affected (optional)
Description: imperative, lowercase, no period, max 50 chars
Body: explain what and why, not how (optional, max 72 chars per line)

Guidelines:
1. Use imperative mood ("add" not "added" or "adds")
2. Be specific but concise 
3. Focus on WHAT changed and WHY
4. Don't describe HOW (that's in the diff)
5. Use conventional commit types appropriately
6. Add scope when changes are focused on specific area
7. Include body only if necessary for context

Examples:
- "feat(auth): add JWT token validation"
- "fix: resolve memory leak in user session cleanup" 
- "docs: update API documentation for new endpoints"
- "refactor(database): optimize query performance"
- "test: add unit tests for payment processing"

Generate ONLY the commit message, nothing else:"""

        return prompt

    def generate_commit_message(self, changes: Dict[str, Any], diff_content: str) -> str:
        """Generate an AI-powered commit message"""
        try:
            # Analyze the changes first
            analysis = self._analyze_file_patterns(changes)

            # Create the prompt
            prompt = self._create_commit_prompt(changes, diff_content, analysis)

            # Generate using Ollama
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "top_p": 0.9,
                    "max_tokens": 200,  # Keep commit messages concise
                },
            )

            commit_message = response.get("response", "").strip()

            # Clean up the response
            commit_message = self._clean_commit_message(commit_message)

            # Validate and provide fallback
            if not commit_message or len(commit_message.split("\n")[0]) > 100:
                logger.warning("AI generated invalid commit message, using fallback")
                return self._generate_fallback_message(changes, analysis)

            logger.info(f"Generated AI commit message: {commit_message}")
            return commit_message

        except Exception as e:
            logger.error(f"AI commit message generation failed: {e}")
            # Fallback to rule-based generation
            return self._generate_fallback_message(
                changes,
                analysis if "analysis" in locals() else self._analyze_file_patterns(changes),
            )

    def _clean_commit_message(self, message: str) -> str:
        """Clean up AI generated commit message"""
        lines = message.strip().split("\n")

        # Remove any introductory text
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith(("here", "commit message:", "the commit", "generated")):
                continue
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            if line.startswith("'") and line.endswith("'"):
                line = line[1:-1]
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines) if cleaned_lines else ""

    def _generate_fallback_message(self, changes: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate fallback commit message using rules"""
        summary_parts = []

        # Determine commit type based on analysis
        if "tests" in analysis["categories"]:
            commit_type = "test"
        elif "docs" in analysis["categories"]:
            commit_type = "docs"
        elif "config" in analysis["categories"]:
            commit_type = "chore"
        elif "build" in analysis["categories"]:
            commit_type = "build"
        elif changes["changes"]["added"] and not changes["changes"]["modified"]:
            commit_type = "feat"
        elif changes["changes"]["deleted"] and not changes["changes"]["added"]:
            commit_type = "refactor"
        else:
            commit_type = "chore"

        # Create scope if languages are focused
        scope = ""
        if len(analysis["languages"]) == 1:
            scope = f"({analysis['languages'][0]})"
        elif len(analysis["categories"]) == 1 and analysis["categories"][0] not in [
            "general",
            "config",
        ]:
            scope = f"({analysis['categories'][0]})"

        # Generate description
        if changes["changes"]["added"] and len(changes["changes"]["added"]) == 1:
            description = f"add {changes['changes']['added'][0].split('/')[-1]}"
        elif changes["changes"]["modified"] and len(changes["changes"]["modified"]) == 1:
            description = f"update {changes['changes']['modified'][0].split('/')[-1]}"
        elif changes["changes"]["deleted"] and len(changes["changes"]["deleted"]) == 1:
            description = f"remove {changes['changes']['deleted'][0].split('/')[-1]}"
        else:
            total = changes["total_files"]
            description = f"update {total} files"

        return f"{commit_type}{scope}: {description}"

    def test_ai_service(self) -> bool:
        """Test if the AI service is working properly"""
        try:
            # Test with minimal changes
            test_changes = {
                "total_files": 1,
                "changes": {"added": ["test.py"], "modified": [], "deleted": [], "renamed": []},
            }

            test_diff = """
            +def hello_world():
            +    print("Hello, World!")
            """

            message = self.generate_commit_message(test_changes, test_diff)
            logger.info(f"AI service test successful: {message}")
            return True

        except Exception as e:
            logger.error(f"AI service test failed: {e}")
            return False
