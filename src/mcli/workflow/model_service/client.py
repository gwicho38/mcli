import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import click
import requests

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class ModelServiceClient:
    """Client for interacting with the model service daemon"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a request to the model service"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Could not connect to model service at {self.base_url}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError("Resource not found")
            elif e.response.status_code == 500:
                error_detail = e.response.json().get("detail", "Unknown error")
                raise RuntimeError(f"Server error: {error_detail}")
            else:
                raise RuntimeError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return self._make_request("GET", "/")

    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return self._make_request("GET", "/health")

    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models"""
        return self._make_request("GET", "/models")

    def load_model(
        self,
        name: str,
        model_type: str,
        model_path: str,
        tokenizer_path: Optional[str] = None,
        device: str = "auto",
        max_length: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
    ) -> str:
        """Load a new model"""
        data = {
            "name": name,
            "model_type": model_type,
            "model_path": model_path,
            "tokenizer_path": tokenizer_path,
            "device": device,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }

        result = self._make_request("POST", "/models", data)
        return result["model_id"]

    def unload_model(self, model_id: str) -> bool:
        """Unload a model"""
        try:
            self._make_request("DELETE", f"/models/{model_id}")
            return True
        except ValueError:
            return False

    def update_model(self, model_id: str, updates: Dict[str, Any]) -> bool:
        """Update model configuration"""
        try:
            self._make_request("PUT", f"/models/{model_id}", updates)
            return True
        except ValueError:
            return False

    def remove_model(self, model_id: str) -> bool:
        """Remove a model from the database"""
        try:
            self._make_request("DELETE", f"/models/{model_id}/remove")
            return True
        except ValueError:
            return False

    def generate_text(
        self,
        model_id: str,
        prompt: str,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate text using a model"""
        data = {
            "prompt": prompt,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        return self._make_request("POST", f"/models/{model_id}/generate", data)

    def classify_text(self, model_id: str, text: str) -> Dict[str, Any]:
        """Classify text using a model"""
        data = {"text": text}
        return self._make_request("POST", f"/models/{model_id}/classify", data)

    def translate_text(
        self, model_id: str, text: str, source_lang: str = "en", target_lang: str = "fr"
    ) -> Dict[str, Any]:
        """Translate text using a model"""
        data = {"text": text, "source_lang": source_lang, "target_lang": target_lang}
        return self._make_request("POST", f"/models/{model_id}/translate", data)


# CLI Commands
@click.group(name="model-client")
def model_client():
    """Client for interacting with the model service daemon"""
    pass


@model_client.command()
@click.option("--url", default="http://localhost:8000", help="Model service URL")
def status(url: str):
    """Get model service status"""
    try:
        client = ModelServiceClient(url)
        status_info = client.get_status()
        health_info = client.get_health()

        click.echo("=" * 60)
        click.echo(click.style("Model Service Status", fg="bright_blue", bold=True))
        click.echo("=" * 60)
        click.echo(f"Service: {status_info['service']}")
        click.echo(f"Version: {status_info['version']}")
        click.echo(f"Status: {status_info['status']}")
        click.echo(f"Models Loaded: {status_info['models_loaded']}")
        click.echo(f"Memory Usage: {health_info.get('memory_usage_mb', 0):.1f} MB")
        click.echo(f"API URL: {url}")
        click.echo("=" * 60)

    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg="red"))


@model_client.command()
@click.option("--url", default="http://localhost:8000", help="Model service URL")
def list_models(url: str):
    """List all available models"""
    try:
        client = ModelServiceClient(url)
        models = client.list_models()

        if not models:
            click.echo("No models available")
            return

        click.echo("=" * 80)
        click.echo(click.style("Available Models", fg="bright_blue", bold=True))
        click.echo("=" * 80)

        for i, model in enumerate(models, 1):
            status_icon = "✅" if model.get("is_loaded") else "⏳"
            click.echo(f"{i}. {status_icon} {model['name']}")
            click.echo(f"   Type: {model['model_type']}")
            click.echo(f"   Path: {model['model_path']}")
            click.echo(f"   Device: {model['device']}")
            if model.get("is_loaded"):
                click.echo(f"   Memory: {model.get('memory_usage_mb', 0):.1f} MB")
                click.echo(f"   Parameters: {model.get('parameters_count', 0):,}")
            click.echo()

        click.echo("=" * 80)

    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg="red"))


@model_client.command()
@click.argument("model_path")
@click.option("--url", default="http://localhost:8000", help="Model service URL")
@click.option("--name", required=True, help="Model name")
@click.option("--type", "model_type", required=True, help="Model type")
@click.option("--tokenizer-path", help="Path to tokenizer")
@click.option("--device", default="auto", help="Device to use")
@click.option("--max-length", default=512, help="Maximum sequence length")
@click.option("--temperature", default=0.7, help="Sampling temperature")
@click.option("--top-p", default=0.9, help="Top-p sampling")
@click.option("--top-k", default=50, help="Top-k sampling")
def load_model(
    model_path: str,
    url: str,
    name: str,
    model_type: str,
    tokenizer_path: str = None,
    device: str = "auto",
    max_length: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 50,
):
    """Load a model into the service"""
    try:
        client = ModelServiceClient(url)

        click.echo(f"Loading model '{name}'...")
        model_id = client.load_model(
            name=name,
            model_type=model_type,
            model_path=model_path,
            tokenizer_path=tokenizer_path,
            device=device,
            max_length=max_length,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )

        click.echo(click.style(f"✅ Model '{name}' loaded successfully!", fg="green"))
        click.echo(f"Model ID: {model_id}")

    except Exception as e:
        click.echo(click.style(f"❌ Error loading model: {e}", fg="red"))


@model_client.command()
@click.argument("model_id")
@click.option("--url", default="http://localhost:8000", help="Model service URL")
def unload_model(model_id: str, url: str):
    """Unload a model from the service"""
    try:
        client = ModelServiceClient(url)

        click.echo(f"Unloading model {model_id}...")
        success = client.unload_model(model_id)

        if success:
            click.echo(click.style(f"✅ Model {model_id} unloaded successfully!", fg="green"))
        else:
            click.echo(click.style(f"❌ Model {model_id} not found", fg="red"))

    except Exception as e:
        click.echo(click.style(f"❌ Error unloading model: {e}", fg="red"))


@model_client.command()
@click.argument("model_id")
@click.option("--url", default="http://localhost:8000", help="Model service URL")
@click.option("--name", help="New model name")
@click.option("--temperature", type=float, help="New temperature value")
@click.option("--max-length", type=int, help="New max length value")
@click.option("--top-p", type=float, help="New top-p value")
@click.option("--top-k", type=int, help="New top-k value")
@click.option("--device", help="New device setting")
def update_model(
    model_id: str,
    url: str,
    name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_length: Optional[int] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    device: Optional[str] = None,
):
    """Update model configuration"""
    try:
        client = ModelServiceClient(url)

        # Build updates dictionary
        updates = {}
        if name is not None:
            updates["name"] = name
        if temperature is not None:
            updates["temperature"] = temperature
        if max_length is not None:
            updates["max_length"] = max_length
        if top_p is not None:
            updates["top_p"] = top_p
        if top_k is not None:
            updates["top_k"] = top_k
        if device is not None:
            updates["device"] = device

        if not updates:
            click.echo(
                click.style(
                    "❌ No updates specified. Use --help to see available options.", fg="red"
                )
            )
            return

        click.echo(f"Updating model {model_id}...")
        success = client.update_model(model_id, updates)

        if success:
            click.echo(click.style(f"✅ Model {model_id} updated successfully!", fg="green"))
            click.echo("Updated parameters:")
            for key, value in updates.items():
                click.echo(f"  {key}: {value}")
        else:
            click.echo(click.style(f"❌ Model {model_id} not found", fg="red"))

    except Exception as e:
        click.echo(click.style(f"❌ Error updating model: {e}", fg="red"))


@model_client.command()
@click.argument("model_id")
@click.option("--url", default="http://localhost:8000", help="Model service URL")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def remove_model(model_id: str, url: str, force: bool = False):
    """Remove a model from the database"""
    try:
        client = ModelServiceClient(url)

        if not force:
            # Get model info first
            models = client.list_models()
            model_info = None
            for model in models:
                if model["id"] == model_id:
                    model_info = model
                    break

            if model_info:
                click.echo(f"Model to remove:")
                click.echo(f"  Name: {model_info['name']}")
                click.echo(f"  Type: {model_info['model_type']}")
                click.echo(f"  Path: {model_info['model_path']}")
                click.echo(f"  Loaded: {'Yes' if model_info.get('is_loaded') else 'No'}")

                if not click.confirm("Are you sure you want to remove this model?"):
                    click.echo("Operation cancelled.")
                    return
            else:
                click.echo(click.style(f"❌ Model {model_id} not found", fg="red"))
                return

        click.echo(f"Removing model {model_id}...")
        success = client.remove_model(model_id)

        if success:
            click.echo(click.style(f"✅ Model {model_id} removed successfully!", fg="green"))
        else:
            click.echo(click.style(f"❌ Model {model_id} not found", fg="red"))

    except Exception as e:
        click.echo(click.style(f"❌ Error removing model: {e}", fg="red"))


@model_client.command()
@click.argument("model_id")
@click.argument("prompt")
@click.option("--url", default="http://localhost:8000", help="Model service URL")
@click.option("--max-length", type=int, help="Maximum sequence length")
@click.option("--temperature", type=float, help="Sampling temperature")
@click.option("--top-p", type=float, help="Top-p sampling")
@click.option("--top-k", type=int, help="Top-k sampling")
def generate(
    model_id: str,
    prompt: str,
    url: str,
    max_length: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
):
    """Generate text using a model"""
    try:
        client = ModelServiceClient(url)

        click.echo(f"Generating text with model {model_id}...")
        click.echo(f"Prompt: {prompt}")
        click.echo("-" * 50)

        result = client.generate_text(
            model_id=model_id,
            prompt=prompt,
            max_length=max_length,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )

        click.echo(click.style("Generated Text:", fg="bright_green", bold=True))
        click.echo(result["generated_text"])
        click.echo()
        click.echo(f"Execution time: {result['execution_time_ms']} ms")

    except Exception as e:
        click.echo(click.style(f"❌ Error generating text: {e}", fg="red"))


@model_client.command()
@click.argument("model_id")
@click.argument("text")
@click.option("--url", default="http://localhost:8000", help="Model service URL")
def classify(model_id: str, text: str, url: str):
    """Classify text using a model"""
    try:
        client = ModelServiceClient(url)

        click.echo(f"Classifying text with model {model_id}...")
        click.echo(f"Text: {text}")
        click.echo("-" * 50)

        result = client.classify_text(model_id=model_id, text=text)

        click.echo(click.style("Classifications:", fg="bright_green", bold=True))
        for class_name, probability in result["classifications"].items():
            click.echo(f"{class_name}: {probability:.4f}")

        click.echo()
        click.echo(f"Execution time: {result['execution_time_ms']} ms")

    except Exception as e:
        click.echo(click.style(f"❌ Error classifying text: {e}", fg="red"))


@model_client.command()
@click.argument("model_id")
@click.argument("text")
@click.option("--url", default="http://localhost:8000", help="Model service URL")
@click.option("--source-lang", default="en", help="Source language")
@click.option("--target-lang", default="fr", help="Target language")
def translate(model_id: str, text: str, url: str, source_lang: str = "en", target_lang: str = "fr"):
    """Translate text using a model"""
    try:
        client = ModelServiceClient(url)

        click.echo(f"Translating text with model {model_id}...")
        click.echo(f"Text ({source_lang}): {text}")
        click.echo("-" * 50)

        result = client.translate_text(
            model_id=model_id, text=text, source_lang=source_lang, target_lang=target_lang
        )

        click.echo(click.style("Translation:", fg="bright_green", bold=True))
        click.echo(f"({target_lang}): {result['translated_text']}")
        click.echo()
        click.echo(f"Execution time: {result['execution_time_ms']} ms")

    except Exception as e:
        click.echo(click.style(f"❌ Error translating text: {e}", fg="red"))


@model_client.command()
@click.option("--url", default="http://localhost:8000", help="Model service URL")
@click.option("--model-id", required=True, help="Model ID to test")
@click.option("--prompt", default="Hello, how are you?", help="Test prompt")
def test_model(url: str, model_id: str, prompt: str):
    """Test a model with a simple prompt"""
    try:
        client = ModelServiceClient(url)

        click.echo("Testing model...")
        click.echo(f"Model ID: {model_id}")
        click.echo(f"Test prompt: {prompt}")
        click.echo("-" * 50)

        # Test text generation
        result = client.generate_text(model_id=model_id, prompt=prompt)

        click.echo(click.style("Test Result:", fg="bright_green", bold=True))
        click.echo(f"Generated: {result['generated_text']}")
        click.echo(f"Time: {result['execution_time_ms']} ms")

        click.echo(click.style("✅ Model test successful!", fg="green"))

    except Exception as e:
        click.echo(click.style(f"❌ Model test failed: {e}", fg="red"))


@model_client.command()
@click.option("--url", default="http://localhost:8000", help="Model service URL")
@click.option("--file", type=click.Path(exists=True), help="File with prompts to test")
@click.option("--model-id", required=True, help="Model ID to test")
@click.option("--output", type=click.Path(), help="Output file for results")
def batch_test(
    url: str,
    file: Optional[str] = None,
    model_id: Optional[str] = None,
    output: Optional[str] = None,
):
    """Run batch tests on a model"""
    try:
        client = ModelServiceClient(url)

        if file:
            # Read prompts from file
            with open(file, "r") as f:
                prompts = [line.strip() for line in f if line.strip()]
        else:
            # Use default test prompts
            prompts = [
                "Hello, how are you?",
                "What is the capital of France?",
                "Explain quantum computing in simple terms.",
                "Write a short poem about technology.",
            ]

        click.echo(f"Running batch test with {len(prompts)} prompts...")
        click.echo(f"Model ID: {model_id}")
        click.echo("-" * 50)

        results = []
        total_time = 0

        for i, prompt in enumerate(prompts, 1):
            click.echo(f"Test {i}/{len(prompts)}: {prompt[:50]}...")

            try:
                result = client.generate_text(model_id=model_id, prompt=prompt)
                results.append(
                    {
                        "prompt": prompt,
                        "generated": result["generated_text"],
                        "time_ms": result["execution_time_ms"],
                        "success": True,
                    }
                )
                total_time += result["execution_time_ms"]

            except Exception as e:
                results.append({"prompt": prompt, "error": str(e), "success": False})

        # Display summary
        click.echo("\n" + "=" * 60)
        click.echo(click.style("Batch Test Results", fg="bright_blue", bold=True))
        click.echo("=" * 60)

        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful

        click.echo(f"Total tests: {len(results)}")
        click.echo(f"Successful: {successful}")
        click.echo(f"Failed: {failed}")
        click.echo(f"Total time: {total_time} ms")
        click.echo(f"Average time: {total_time/len(results):.1f} ms")

        # Save results if output file specified
        if output:
            with open(output, "w") as f:
                json.dump(results, f, indent=2)
            click.echo(f"Results saved to: {output}")

    except Exception as e:
        click.echo(click.style(f"❌ Batch test failed: {e}", fg="red"))


if __name__ == "__main__":
    model_client()
