import json
from pathlib import Path
from typing import Any


class TransformerToxicityModel:
    """Hugging Face sequence-classification adapter for Sentinel inference."""

    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        device: Any,
        version: str,
        max_length: int = 256,
    ) -> None:
        self._model = model
        self._tokenizer = tokenizer
        self._device = device
        self._version = version
        self._max_length = max_length

    @property
    def version(self) -> str:
        return self._version

    @classmethod
    def load(cls, path: Path) -> "TransformerToxicityModel":
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = AutoTokenizer.from_pretrained(path)
        model = AutoModelForSequenceClassification.from_pretrained(path)
        model.to(device)
        model.eval()

        metadata_path = path / "sentinel_metadata.json"
        metadata = (
            json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata_path.exists()
            else {}
        )
        return cls(
            model=model,
            tokenizer=tokenizer,
            device=device,
            version=metadata.get("model_version", "distilbert-toxicity-v1"),
            max_length=int(metadata.get("max_length", 256)),
        )

    def predict_score(self, text: str) -> float:
        import torch

        encoded = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self._max_length,
        )
        encoded = {name: tensor.to(self._device) for name, tensor in encoded.items()}
        with torch.inference_mode():
            logits = self._model(**encoded).logits
            probability = torch.softmax(logits, dim=-1)[0, 1]
        return float(probability.cpu().item())
