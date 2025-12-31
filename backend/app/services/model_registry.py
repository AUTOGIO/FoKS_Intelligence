from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.services.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ModelInfo:
    """Metadata describing a local LM Studio model."""

    name: str
    category: str
    model_path: Path
    format: str
    quantization: str
    max_context: int
    supports_vision: bool = False
    supports_tools: bool = False
    description: str = ""
    tags: Sequence[str] = field(default_factory=list)


class ModelRegistry:
    """Registry of local MLX/GGUF models available for FoKS orchestration."""

    def __init__(self, search_paths: Iterable[Path] | None = None) -> None:
        directories = search_paths or (Path(path) for path in settings.model_directories)
        self.directories: list[Path] = [Path(path).expanduser() for path in directories]
        self._models: dict[str, ModelInfo] = {}
        self._load_static_entries()

    def _resolve_path(self, relative_path: str) -> Path:
        for directory in self.directories:
            candidate = directory / relative_path
            if candidate.exists():
                return candidate
        default_base = self.directories[0] if self.directories else Path("/Volumes/MICRO/LM_STUDIO_MODELS")
        resolved = default_base / relative_path
        logger.debug("Model path not found, defaulting", extra={"payload": {"relative_path": relative_path, "resolved": str(resolved)}})
        return resolved

    def _load_static_entries(self) -> None:
        """Populate registry with the user's current local collection."""
        entries: list[ModelInfo] = [
            ModelInfo(
                name="hermes-3-llama-3.2-3b-mlx",
                category="chat",
                model_path=self._resolve_path("bitznbrewz/Hermes-3-Llama-3.2-3B.Q4_K_M-MLX"),
                format="mlx",
                quantization="Q4_K_M",
                max_context=16384,
                description="Hermes 3 (Llama 3.2 3B) fine-tuned for helpful chat on MLX",
            ),
            ModelInfo(
                name="deepseek-r1-qwen3-8b-mlx",
                category="reasoning",
                model_path=self._resolve_path("lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-MLX-4bit"),
                format="mlx",
                quantization="4bit",
                max_context=131072,
                supports_tools=True,
                description="DeepSeek-R1 distilled reasoning model (Qwen3 8B) with long context.",
            ),
            ModelInfo(
                name="gemma-3n-e4b-it-mlx",
                category="chat",
                model_path=self._resolve_path("lmstudio-community/gemma-3n-E4B-it-MLX-4bit"),
                format="mlx",
                quantization="4bit",
                max_context=8192,
                description="Google Gemma 3 nano instruction-tuned for lightweight chat and drafting.",
            ),
            ModelInfo(
                name="granite-3.1-8b-gguf",
                category="chat",
                model_path=self._resolve_path("lmstudio-community/granite-3.1-8b-instruct-GGUF"),
                format="gguf",
                quantization="Q4_K_M",
                max_context=32768,
                description="IBM Granite 3.1 8B instruct GGUF for privacy-first assistants.",
            ),
            ModelInfo(
                name="phi-4-mini-mlx",
                category="reasoning",
                model_path=self._resolve_path("lmstudio-community/Phi-4-mini-reasoning-MLX-4bit"),
                format="mlx",
                quantization="4bit",
                max_context=131072,
                description="Phi-4 mini reasoning-focused MLX build optimized for ANE.",
            ),
            ModelInfo(
                name="phi-4-reasoning-plus-mlx",
                category="scientific",
                model_path=self._resolve_path("lmstudio-community/Phi-4-reasoning-plus-MLX-4bit"),
                format="mlx",
                quantization="4bit",
                max_context=65536,
                description="Phi-4 reasoning plus variant suited for analytical/scientific workflows.",
            ),
            ModelInfo(
                name="qwen3-4b-thinking-mlx",
                category="reasoning",
                model_path=self._resolve_path("lmstudio-community/Qwen3-4B-Thinking-2507-MLX-4bit"),
                format="mlx",
                quantization="4bit",
                max_context=65536,
                supports_tools=True,
                description="Qwen3 4B thinking tuned for deliberate reasoning and tool use.",
            ),
            ModelInfo(
                name="qwen3-14b-mlx",
                category="chat",
                model_path=self._resolve_path("lmstudio-community/Qwen3-14B-MLX-4bit"),
                format="mlx",
                quantization="4bit",
                max_context=131072,
                supports_tools=True,
                description="Qwen3 14B MLX general-purpose assistant with long context.",
            ),
            ModelInfo(
                name="qwen3-vision-mlx",
                category="vision",
                model_path=self._resolve_path("qwen/qwen3-14b"),
                format="mlx",
                quantization="full",
                max_context=65536,
                supports_vision=True,
                supports_tools=True,
                description="Qwen3-VL 14B vision-language model for multimodal tasks.",
            ),
            ModelInfo(
                name="qwen3-embedding-0.6b-gguf",
                category="embeddings",
                model_path=self._resolve_path("mlx-community/Qwen3-Embedding-0.6B-8bit"),
                format="mlx",
                quantization="8bit",
                max_context=8192,
                description="Qwen3 embedding 0.6B for semantic search and memory indexing.",
            ),
            ModelInfo(
                name="qwen3-embedding-4b-mlx",
                category="embeddings",
                model_path=self._resolve_path("mlx-community/Qwen3-Embedding-4B-4bit-DWQ"),
                format="mlx",
                quantization="4bit-DWQ",
                max_context=32768,
                description="Qwen3 4B embeddings high-accuracy variant.",
            ),
            ModelInfo(
                name="granite-3.1-8b-mlx",
                category="scientific",
                model_path=self._resolve_path("ibm/granite-3.1-8b"),
                format="mlx",
                quantization="full",
                max_context=16384,
                description="Granite 3.1 8B Core ML build for enterprise analytics and governance.",
            ),
            ModelInfo(
                name="lfm2-1.2b-mlx",
                category="chat",
                model_path=self._resolve_path("lmstudio-community/LFM2-1.2B-MLX-8bit"),
                format="mlx",
                quantization="8bit",
                max_context=8192,
                description="Local fine-tuned mini assistant for low-latency responses.",
            ),
            ModelInfo(
                name="lfm2-1.2b-liquid",
                category="chat",
                model_path=self._resolve_path("liquid/lfm2-1.2b"),
                format="gguf",
                quantization="Q4_K_M",
                max_context=8192,
                description="Liquid fine-tuned mini assistant variant.",
            ),
        ]

        for entry in entries:
            self._models[entry.name] = entry

    # Public API -----------------------------------------------------------------
    def list_models(self, category: str | None = None) -> list[ModelInfo]:
        if category:
            normalized = category.lower()
            return [model for model in self._models.values() if model.category == normalized]
        return list(self._models.values())

    def resolve_model(self, name: str) -> ModelInfo:
        try:
            return self._models[name]
        except KeyError:
            raise ValueError(f"Model '{name}' is not registered. Available: {list(self._models)})") from None

    def get_default_model(self, task_type: str) -> ModelInfo:
        normalized = task_type.lower()
        default_name = DEFAULT_MODELS.get(normalized)
        if not default_name:
            raise ValueError(
                f"Unsupported task type '{task_type}'. Expected one of {sorted(DEFAULT_MODELS)}"
            )
        return self.resolve_model(default_name)

    def refresh(self) -> None:
        self._models.clear()
        self._load_static_entries()


def _get_locked_defaults() -> dict[str, str]:
    """
    Build default models dict from locked settings.

    This ensures model selection is config-driven and deterministic,
    reading from FOKS_LOCKED_*_MODEL environment variables.
    """
    return {
        "chat": settings.locked_chat_model,
        "reasoning": settings.locked_reasoning_model,
        "embeddings": settings.locked_embedding_model,
        "vision": settings.locked_vision_model,
        "scientific": settings.locked_scientific_model,
    }


# Default models are now config-driven via locked settings
DEFAULT_MODELS: dict[str, str] = _get_locked_defaults()


# Singleton registry instance ----------------------------------------------------
registry = ModelRegistry()


def list_models(category: str | None = None) -> list[ModelInfo]:
    return registry.list_models(category)


def resolve_model(name: str) -> ModelInfo:
    return registry.resolve_model(name)


def get_default_model(task_type: str) -> ModelInfo:
    return registry.get_default_model(task_type)


def refresh_registry() -> None:
    registry.refresh()

