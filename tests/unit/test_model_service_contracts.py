"""Model-service storage, HTTP, embedding and adapter contracts without model downloads."""

import importlib
import json
import sqlite3
import subprocess
import sys
from contextlib import nullcontext
from datetime import datetime, timedelta
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
import requests
from click.testing import CliRunner
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def model_module(monkeypatch, tmp_path):
    """Replace only optional inference engines; run the real storage and API code."""
    prefix = "mcli.workflow.model_service"
    existing = set(sys.modules)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    torch = ModuleType("torch")
    torch.Tensor = type("Tensor", (), {})
    torch.cuda = SimpleNamespace(is_available=lambda: False, memory_allocated=lambda: 1024**2)
    torch.float32 = "float32"
    torch.float16 = "float16"
    torch.no_grad = nullcontext
    transformers = ModuleType("transformers")
    for name in ("AutoModel", "AutoModelForCausalLM", "AutoModelForSeq2SeqLM", "AutoTokenizer"):
        setattr(transformers, name, Mock())
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setenv("HOME", str(tmp_path))
    module = importlib.import_module(prefix + ".model_service")
    yield module
    for name in set(sys.modules) - existing:
        if name == prefix or name.startswith(prefix + "."):
            sys.modules.pop(name, None)


def test_model_database_roundtrip_updates_and_inference(model_module, tmp_path):
    module = model_module
    database = module.ModelDatabase(tmp_path / "models.sqlite")
    second = module.ModelInfo("b", "Zulu", "translation", "b.bin", created_at=None)
    first = module.ModelInfo("a", "Alpha", "text-generation", "a.bin", is_loaded=True)
    assert isinstance(second.created_at, datetime)
    assert database.add_model(second) == "b"
    assert database.add_model(first) == "a"
    assert [model.id for model in database.get_all_models()] == ["a", "b"]
    restored = database.get_model("a")
    assert restored.name == "Alpha" and restored.is_loaded is True
    restored.name = "Renamed"
    restored.memory_usage_mb = 12.5
    assert database.update_model(restored)
    assert database.get_model("a").memory_usage_mb == 12.5
    assert database.get_model("absent") is None
    missing = module.ModelInfo("absent", "Missing", "translation", "none")
    assert database.update_model(missing) is False
    with pytest.raises(sqlite3.IntegrityError):
        database.add_model(first)
    database.record_inference("a", "text-generation", "hello", "world", 12)
    with sqlite3.connect(database.db_path) as connection:
        assert connection.execute(
            "SELECT model_id, input_data, output_data, execution_time_ms FROM inferences"
        ).fetchone() == ("a", "hello", "world", 12)
    deleted = database.delete_model("a")
    assert deleted is True
    deleted_again = database.delete_model("a")
    assert deleted_again is False


@pytest.mark.parametrize("model_type", ["text-generation", "text-classification", "translation"])
def test_manager_load_and_unload_persists_metadata(model_module, tmp_path, monkeypatch, model_type):
    module = model_module
    manager = module.ModelManager(str(tmp_path / "models"), max_cache_size=2)
    info = module.ModelInfo("model", "Example", model_type, "weights", tokenizer_path="tokens")
    manager.db.add_model(info)
    model = Mock()
    model.to.return_value = model
    model.parameters.return_value = [SimpleNamespace(numel=lambda: 256)]
    for factory in (module.AutoModel, module.AutoModelForCausalLM, module.AutoModelForSeq2SeqLM):
        factory.from_pretrained.return_value = model
    module.AutoTokenizer.from_pretrained.return_value = "tokenizer"
    assert manager.load_model(info)
    assert manager.loaded_models["model"]["tokenizer"] == "tokenizer"
    assert manager.db.get_model("model").parameters_count == 256
    assert manager.db.get_model("model").is_loaded
    assert manager.load_model(info)  # existing entries are idempotent
    assert manager.unload_model("model")
    assert not manager.db.get_model("model").is_loaded
    assert not manager.unload_model("missing")
    assert manager._get_model_memory_usage(Mock(parameters=Mock(side_effect=ValueError))) == 0
    manager.device = "cuda"
    assert manager._get_model_memory_usage(model) == 1


@pytest.mark.parametrize("model_type", ["unsupported", "image-generation"])
def test_manager_failed_load_does_not_register_model(model_module, tmp_path, model_type):
    manager = model_module.ModelManager(str(tmp_path / "models"))
    info = model_module.ModelInfo("bad", "Bad", model_type, "weights")
    assert manager.load_model(info) is False
    assert not manager.loaded_models
    with pytest.raises(ValueError):
        manager.generate_text("bad", "hello")
    manager._evict_oldest_model()  # empty cache is a no-op


def test_manager_summary_and_oldest_eviction(model_module, tmp_path, monkeypatch):
    manager = model_module.ModelManager(str(tmp_path / "models"))
    a = model_module.ModelInfo("a", "A", "translation", "a", is_loaded=True, memory_usage_mb=4)
    b = model_module.ModelInfo("b", "B", "translation", "b")
    manager.db.add_model(a)
    manager.db.add_model(b)
    summary = manager.get_models_summary()
    assert summary["total_models"] == 2 and summary["loaded_models"] == 1
    assert summary["models_by_type"]["translation"] == {"count": 2, "loaded": 1, "memory_mb": 4}
    now = datetime.now()
    manager.loaded_models = {"b": {"loaded_at": now}, "a": {"loaded_at": now - timedelta(days=1)}}
    manager._evict_oldest_model()
    assert set(manager.loaded_models) == {"b"}


def test_model_service_routes_use_real_database(model_module, tmp_path, monkeypatch):
    service = model_module.ModelService(
        {"models_dir": str(tmp_path / "models"), "enable_cors": False}
    )
    monkeypatch.setattr(service.model_manager, "load_model", lambda info: True)
    with TestClient(service.app) as client:
        assert client.get("/").json()["service"] == "MCLI Model Service"
        assert client.get("/health").json()["status"] == "healthy"
        body = {"name": "Example", "model_type": "translation", "model_path": "weights"}
        response = client.post("/models", json=body)
        assert response.status_code == 200
        model_id = response.json()["model_id"]
        assert client.get("/models").json()[0]["name"] == "Example"
        assert client.get("/models/summary").json()["total_models"] == 1
        assert (
            client.put(f"/models/{model_id}", json={"name": "Updated", "unknown": 3}).json()[
                "status"
            ]
            == "updated"
        )
        assert service.model_manager.db.get_model(model_id).name == "Updated"
        assert client.put("/models/missing", json={"name": "No"}).status_code == 404
        assert client.delete(f"/models/{model_id}/remove").json()["status"] == "removed"
        assert client.delete(f"/models/{model_id}/remove").status_code == 404
        monkeypatch.setattr(service.model_manager, "load_model", lambda info: False)
        assert client.post("/models", json=body).status_code == 500
        assert client.get("/models").json() == []


@pytest.mark.parametrize(
    "operation,payload,result_key,output",
    [
        ("generate", {"prompt": "hello"}, "generated_text", "answer"),
        ("classify", {"text": "hello"}, "classifications", [{"label": "ok"}]),
        ("translate", {"text": "hello"}, "translated_text", "bonjour"),
    ],
)
def test_model_service_inference_records_success_and_failure(
    model_module, tmp_path, monkeypatch, operation, payload, result_key, output
):
    service = model_module.ModelService({"models_dir": str(tmp_path / "models")})
    method = {
        "generate": "generate_text",
        "classify": "classify_text",
        "translate": "translate_text",
    }[operation]
    inference = Mock(return_value=output)
    monkeypatch.setattr(service.model_manager, method, inference, raising=False)
    with TestClient(service.app) as client:
        response = client.post(f"/models/example/{operation}", json=payload)
        assert response.status_code == 200 and response.json()[result_key] == output
        inference.side_effect = ValueError("inference rejected")
        response = client.post(f"/models/example/{operation}", json=payload)
        assert response.status_code == 500 and "inference rejected" in response.json()["detail"]
    with sqlite3.connect(service.model_manager.db.db_path) as connection:
        rows = connection.execute(
            "SELECT input_data,error_message FROM inferences ORDER BY rowid"
        ).fetchall()
    assert rows == [("hello", ""), ("hello", "inference rejected")]


def test_embedder_normalization_chunking_and_search(tmp_path, monkeypatch):
    from mcli.workflow.model_service.lightweight_embedder import LightweightEmbedder

    embedder = LightweightEmbedder(str(tmp_path))
    monkeypatch.setattr(embedder, "get_embedding_method", lambda: "simple_hash")
    result = embedder.embed_text("alpha alpha beta", "simple_hash")
    vector = np.array(result["embedding"])
    assert result["dimensions"] == 128 and np.isclose(vector.sum(), 1)
    assert result["unique_words"] == 2
    assert embedder.embed_text("a to", "simple_hash")["embedding"] == [0.0] * 128
    assert embedder.chunk_text("abcdefghij", chunk_size=5, overlap=2) == [
        "abcde",
        "defgh",
        "ghij",
        "j",
    ]
    document = embedder.embed_document("alpha beta gamma", chunk_size=1000)
    assert document["success"] and document["document_embedding"]["total_text_length"] == 16
    assert embedder.embed_document("")["document_embedding"]["total_chunks"] == 0
    matching = {
        "document_id": "match",
        "chunk_embeddings": [{"embedding": result}],
        "total_text_length": 16,
    }
    other = {"document_id": "empty", "chunk_embeddings": []}
    hits = embedder.search_similar("alpha alpha beta", [other, matching], top_k=1)
    assert hits[0]["document_id"] == "match" and hits[0]["similarity"] > 0
    assert embedder.get_status()["available_methods"]["simple_hash"]


def test_invalid_embedding_chunks_fail_before_looping(tmp_path):
    """The child handshake proves import finished before the timeout starts."""
    code = (
        "import sys\n"
        "from mcli.workflow.model_service.lightweight_embedder import LightweightEmbedder\n"
        "obj = LightweightEmbedder(sys.argv[1])\n"
        "print('READY', flush=True)\n"
        "try:\n"
        "    obj.chunk_text('nonempty text', chunk_size=100)\n"
        "except ValueError:\n"
        "    print('REJECTED')\n"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", code, str(tmp_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout.readline().strip() == "READY"
        try:
            output, error = child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            pytest.fail("chunk_size <= overlap did not terminate")
        assert child.returncode == 0, error
        assert output.strip() == "REJECTED"
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate()


@pytest.mark.parametrize("size,overlap", [(0, 0), (-1, 0), (200, 200), (100, 200), (500, -1)])
def test_chunk_size_and_overlap_require_forward_progress(tmp_path, size, overlap):
    from mcli.workflow.model_service.lightweight_embedder import LightweightEmbedder

    with pytest.raises(ValueError, match="chunk_size"):
        LightweightEmbedder(str(tmp_path)).chunk_text("nonempty", size, overlap)


def test_embedder_fallback_and_tfidf_reuse(tmp_path, monkeypatch):
    from mcli.workflow.model_service import lightweight_embedder as module

    embedder = module.LightweightEmbedder(str(tmp_path))
    monkeypatch.setattr(module, "HAS_SKLEARN", False)
    assert embedder.get_embedding_method() == "simple_hash"
    monkeypatch.setattr(module, "HAS_SENTENCE_TRANSFORMERS", True)
    assert embedder.get_embedding_method() == "sentence_transformers"
    monkeypatch.setattr(
        embedder, "_embed_with_sentence_transformers", Mock(side_effect=RuntimeError("offline"))
    )
    assert embedder.embed_text("alpha beta")["method"] == "simple_hash"
    a = embedder.embed_text("alpha beta gamma", "tfid")
    assert a["method"] == "tfid"
    vectorizer = embedder.vectorizer
    b = embedder.embed_text("alpha gamma", "tfid")
    assert b["dimensions"] == a["dimensions"] and embedder.vectorizer is vectorizer


@pytest.mark.parametrize(
    "status,expected", [(404, ValueError), (500, RuntimeError), (403, RuntimeError)]
)
def test_model_http_client_maps_remote_errors(status, expected):
    from mcli.workflow.model_service.client import ModelServiceClient

    client = ModelServiceClient("http://model.invalid/")
    response = Mock(status_code=status, text="denied")
    response.json.return_value = {"detail": "failure"}
    response.raise_for_status.side_effect = requests.HTTPError(response=response)
    client.session.get = Mock(return_value=response)
    with pytest.raises(expected):
        client.get_status()
    client.session.get.assert_called_once_with("http://model.invalid/")


def test_model_http_client_payloads_and_transport_failures():
    from mcli.workflow.model_service.client import ModelServiceClient

    client = ModelServiceClient("http://model.invalid")
    response = Mock()
    response.json.return_value = {"model_id": "m"}
    client.session.post = Mock(return_value=response)
    assert client.load_model("Name", "translation", "weights") == "m"
    client.generate_text("m", "hello", temperature=0.5)
    client.session.post.assert_called_with(
        "http://model.invalid/models/m/generate", json={"prompt": "hello", "temperature": 0.5}
    )
    client.classify_text("m", "hello")
    client.session.post.assert_called_with(
        "http://model.invalid/models/m/classify", json={"text": "hello"}
    )
    client.translate_text("m", "hello", target_lang="es")
    assert client.session.post.call_args.kwargs["json"]["target_lang"] == "es"
    client.session.delete = Mock(return_value=response)
    assert client.unload_model("m") and client.remove_model("m")
    client.session.get = Mock(side_effect=requests.ConnectionError("offline"))
    with pytest.raises(ConnectionError, match="Could not connect"):
        client.get_health()
    with pytest.raises(RuntimeError, match="Unsupported HTTP method"):
        client._make_request("PATCH", "/models")


def test_adapter_authentication_and_response_contracts():
    from mcli.workflow.model_service.openai_adapter import create_openai_adapter

    manager = SimpleNamespace(loaded_models={"example": {}})
    adapter = create_openai_adapter(manager)
    adapter.api_key_manager.add_key("test-token", "contract")
    app = FastAPI()
    app.include_router(adapter.router)
    with TestClient(app) as client:
        for authorization in (None, "Basic test-token", "Bearer invalid", "bad format extra"):
            headers = {"Authorization": authorization} if authorization else {}
            assert client.get("/v1/models", headers=headers).status_code == 401
        headers = {"Authorization": "Bearer test-token"}
        assert client.get("/v1/models", headers=headers).json()["data"][0]["id"] == "example"
        payload = {
            "model": "example",
            "messages": [
                {"role": "system", "content": "Be short"},
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
        }
        body = client.post("/v1/chat/completions", headers=headers, json=payload).json()
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert "User: hello" in body["choices"][0]["message"]["content"]
        assert (
            body["usage"]["total_tokens"]
            == body["usage"]["prompt_tokens"] + body["usage"]["completion_tokens"]
        )
        stream = client.post(
            "/v1/chat/completions", headers=headers, json={**payload, "stream": True}
        )
        assert stream.headers["content-type"].startswith("text/event-stream")
        events = [line[6:] for line in stream.text.splitlines() if line.startswith("data: ")]
        assert events[-1] == "[DONE]"
        assert json.loads(events[-2])["choices"][0]["finish_reason"] == "stop"
    assert adapter.api_key_manager.list_keys()[0]["usage_count"] == 3
    adapter.api_key_manager.remove_key("test-token")
    adapter.api_key_manager.remove_key("absent")
    assert not adapter.api_key_manager.validate_key("test-token")


@pytest.fixture
def model_client_cli(monkeypatch):
    module = importlib.import_module("mcli.workflow.model_service.client")
    client = Mock()
    client.get_status.return_value = {
        "service": "Contract",
        "version": "1",
        "status": "running",
        "models_loaded": 1,
    }
    client.get_health.return_value = {"memory_usage_mb": 2}
    client.list_models.return_value = [
        {
            "id": "m",
            "name": "Example",
            "model_type": "translation",
            "model_path": "weights",
            "device": "cpu",
            "is_loaded": True,
        }
    ]
    client.load_model.return_value = "m"
    client.generate_text.return_value = {"generated_text": "answer", "execution_time_ms": 12}
    client.classify_text.return_value = {"classifications": {"ok": 0.9}, "execution_time_ms": 3}
    client.translate_text.return_value = {"translated_text": "bonjour", "execution_time_ms": 5}
    monkeypatch.setattr(module, "ModelServiceClient", lambda url: client)
    return module, client, CliRunner()


@pytest.mark.parametrize(
    "args,expected",
    [
        (["status"], "Contract"),
        (["list-models"], "Example"),
        (["load-model", "weights", "--name", "Example", "--type", "translation"], "Model ID: m"),
        (["unload-model", "m"], "unloaded successfully"),
        (
            [
                "update-model",
                "m",
                "--name",
                "New",
                "--temperature",
                "0.2",
                "--max-length",
                "100",
                "--top-p",
                "0.7",
                "--top-k",
                "10",
                "--device",
                "cpu",
            ],
            "Updated parameters",
        ),
        (["remove-model", "m", "--force"], "removed successfully"),
        (["generate", "m", "hello"], "answer"),
        (["classify", "m", "hello"], "0.9000"),
        (["translate", "m", "hello"], "bonjour"),
        (["test-model", "--model-id", "m"], "test successful"),
    ],
)
def test_model_client_cli_reports_service_results(model_client_cli, args, expected):
    module, client, runner = model_client_cli
    result = runner.invoke(module.model_client, args)
    assert result.exit_code == 0, result.output
    assert expected in result.output
    assert "Error" not in result.output


def test_model_client_batch_records_partial_failure(model_client_cli, tmp_path):
    module, client, runner = model_client_cli
    prompts = tmp_path / "prompts.txt"
    prompts.write_text("first\n\nsecond\n")
    output = tmp_path / "results.json"
    client.generate_text.side_effect = [
        {"generated_text": "answer", "execution_time_ms": 12},
        ValueError("rejected"),
    ]
    result = runner.invoke(
        module.model_client,
        ["batch-test", "--model-id", "m", "--file", str(prompts), "--output", str(output)],
    )
    assert (
        result.exit_code == 0 and "Successful: 1" in result.output and "Failed: 1" in result.output
    )
    saved = json.loads(output.read_text())
    assert saved[0]["generated"] == "answer" and saved[1]["error"] == "rejected"
    assert [call.kwargs["prompt"] for call in client.generate_text.call_args_list] == [
        "first",
        "second",
    ]


def test_model_client_cli_absent_models_and_confirmation(model_client_cli):
    module, client, runner = model_client_cli
    assert (
        "cancelled" in runner.invoke(module.model_client, ["remove-model", "m"], input="n\n").output
    )
    client.remove_model.assert_not_called()
    assert (
        "removed successfully"
        in runner.invoke(module.model_client, ["remove-model", "m"], input="y\n").output
    )
    client.list_models.return_value = []
    assert "No models" in runner.invoke(module.model_client, ["list-models"]).output
    assert "not found" in runner.invoke(module.model_client, ["remove-model", "missing"]).output
    assert "No updates" in runner.invoke(module.model_client, ["update-model", "m"]).output
    client.unload_model.return_value = False
    assert "not found" in runner.invoke(module.model_client, ["unload-model", "missing"]).output
    client.get_status.side_effect = ConnectionError("offline")
    assert "offline" in runner.invoke(module.model_client, ["status"]).output


def test_pdf_processor_extracts_and_analyzes_without_inference_downloads(
    model_module, tmp_path, monkeypatch
):
    module = importlib.import_module("mcli.workflow.model_service.pdf_processor")
    processor = module.PDFProcessor(str(tmp_path / "models"))
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"fixture")
    text = "Research analysis studies charging. Charging research helps drivers. More research."
    monkeypatch.setattr(processor, "_extract_pdf_text_enhanced", lambda path: text)
    processor.lightweight_server.loaded_models = {"test": {}}
    result = processor.process_pdf_with_ai(str(source), "test")
    assert result["success"]
    analysis = result["pdf_analysis"]["ai_analysis"]
    assert analysis["document_type"] == "report"
    assert analysis["character_count"] == len(text)
    assert "research" in analysis["key_topics"]
    assert 0 <= analysis["complexity_score"] <= 1
    assert "not found" in processor.extract_text_from_pdf(str(tmp_path / "missing.pdf"))["error"]
    monkeypatch.setattr(processor, "_extract_pdf_text_enhanced", lambda path: "  ")
    assert "No text" in processor.extract_text_from_pdf(str(source))["error"]
    assert not processor.process_pdf_with_ai(str(source), "test").get("success")
    assert processor._generate_summary("Short text") == "Short text"
    assert processor._generate_summary("x" * 510).endswith("...")
    assert processor._calculate_complexity_score("") == 0
    assert processor._calculate_complexity_score("longword " * 500) == 1
    for text, expected in [
        ("contract", "legal_document"),
        ("guide", "manual"),
        ("invoice", "financial"),
        ("resume", "resume"),
        ("hello", "general"),
    ]:
        assert processor._classify_document_type(text) == expected
    assert processor.get_service_status()["models_loaded"] == ["test"]
    monkeypatch.setattr(processor.lightweight_server, "start_server", Mock())
    assert processor.start_pdf_processing_service(9001)
    assert processor.lightweight_server.port == 9001
    processor.lightweight_server.start_server.side_effect = RuntimeError("unavailable")
    assert not processor.start_pdf_processing_service()


def test_model_service_pid_lifecycle_cleans_up_after_server_interrupt(
    model_module, tmp_path, monkeypatch
):
    module = model_module
    service = module.ModelService({"models_dir": str(tmp_path / "models")})
    signals = Mock()
    monkeypatch.setattr(module.signal, "signal", signals)
    server = Mock(side_effect=KeyboardInterrupt)
    monkeypatch.setattr(module.uvicorn, "run", server)
    assert not service.status()["running"]
    service.start()
    assert not service.running and not service.pid_file.exists()
    server.assert_called_once_with(service.app, host="0.0.0.0", port=8000, log_level="info")
    assert signals.call_count == 2
    service.running = True
    service.start()  # an active service must not start another server
    assert server.call_count == 1
    service.model_manager.loaded_models["example"] = {}
    unload = Mock(side_effect=lambda model_id: service.model_manager.loaded_models.pop(model_id))
    monkeypatch.setattr(service.model_manager, "unload_model", unload)
    service.pid_file.write_text("42")
    service.stop()
    unload.assert_called_once_with("example")
    assert not service.pid_file.exists() and not service.running
    service.stop()
    service.pid_file.write_text("42")
    monkeypatch.setattr(module.psutil, "pid_exists", lambda pid: pid == 42)
    assert service.status()["running"]
    service.start()
    assert server.call_count == 1
    service.pid_file.write_text("invalid pid")
    assert service.status()["running"] is False


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_manager_inference_passes_parameters_and_decodes_outputs(
    model_module, tmp_path, monkeypatch, device
):
    module = model_module
    manager = module.ModelManager(str(tmp_path / "models"))
    manager.device = device
    tensor = Mock()
    tensor.to.return_value = tensor
    tokenizer = Mock(return_value={"input_ids": tensor})
    tokenizer.eos_token_id = 7
    tokenizer.decode.return_value = "hello answer"
    model = Mock()
    model.generate.return_value = [[1, 2]]
    info = module.ModelInfo("model", "Example", "text-generation", "weights", max_length=99)
    manager.loaded_models["model"] = {"model": model, "tokenizer": tokenizer, "model_info": info}
    assert manager.generate_text("model", "hello") == "answer"
    assert model.generate.call_args.kwargs["max_length"] == 99
    assert model.generate.call_args.kwargs["pad_token_id"] == 7
    if device == "cuda":
        tensor.to.assert_called_with("cuda")
    model.generate.side_effect = RuntimeError("inference unavailable")
    with pytest.raises(RuntimeError, match="inference unavailable"):
        manager.generate_text("model", "hello")
    model.generate.side_effect = None
    probabilities = Mock()
    probabilities.__getitem__ = Mock(return_value=probabilities)
    probabilities.cpu.return_value.numpy.return_value = np.array([0.2, 0.8])
    monkeypatch.setattr(module.torch, "softmax", Mock(return_value=probabilities), raising=False)
    assert manager.classify_text("model", "hello") == {"class_0": 0.2, "class_1": 0.8}
    with pytest.raises(ValueError):
        manager.classify_text("missing", "hello")
