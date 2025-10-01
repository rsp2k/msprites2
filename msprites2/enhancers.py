"""Transcript enhancement module for post-processing Whisper output.

This module provides enhancers that improve raw transcriptions by fixing grammar,
adding punctuation, formatting, and applying domain-specific corrections using LLMs.

Example:
    >>> from msprites2.enhancers import OllamaTextEnhancer
    >>> from msprites2 import AudioTranscriber
    >>>
    >>> enhancer = OllamaTextEnhancer(model="llama3.1:8b")
    >>> transcriber = AudioTranscriber(enhancer=enhancer)
    >>> segments, enhanced = await transcriber.transcribe_enhanced("video.mp4", context="technical")
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict
import asyncio

# Check if ollama is available
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None


class TranscriptEnhancer(ABC):
    """Base class for transcript enhancement.

    Subclasses should implement the enhance() method to process raw transcripts
    and return improved versions with proper grammar, punctuation, and formatting.
    """

    @abstractmethod
    async def enhance(self, text: str, context: str = "general") -> str:
        """Enhance raw transcript text.

        Args:
            text: Raw transcript text from Whisper
            context: Domain context ("technical", "educational", "general", etc.)

        Returns:
            Enhanced transcript text with improvements
        """
        pass


class OllamaTextEnhancer(TranscriptEnhancer):
    """Enhance transcripts using Ollama text models.

    This enhancer uses Ollama's LLMs to fix grammar, add punctuation,
    improve formatting, and apply domain-specific corrections.

    Attributes:
        host: Ollama server hostname
        port: Ollama server port
        model: Ollama model name to use for enhancement

    Example:
        >>> enhancer = OllamaTextEnhancer(
        ...     host="localhost",
        ...     port=11434,
        ...     model="llama3.1:8b"
        ... )
        >>> enhanced = await enhancer.enhance(
        ...     "um so like the function takes uh two parameters",
        ...     context="technical"
        ... )
        >>> print(enhanced)
        "The function takes two parameters."
    """

    DEFAULT_PROMPTS = {
        "technical": (
            "You are an expert technical editor. Clean up this technical transcript "
            "by fixing grammar, adding proper punctuation, removing filler words "
            "(um, uh, like), and ensuring technical terminology is correctly formatted. "
            "Preserve all technical details and code references. Return only the cleaned text.\n\n"
            "Transcript:\n{text}"
        ),
        "educational": (
            "You are an educational content editor. Improve this educational transcript "
            "for clarity and readability. Fix grammar, add punctuation, remove filler words, "
            "and structure the content logically. Make it suitable for students. "
            "Return only the cleaned text.\n\n"
            "Transcript:\n{text}"
        ),
        "medical": (
            "You are a medical transcription editor. Clean up this medical transcript "
            "ensuring medical terminology is accurate, grammar is correct, and "
            "punctuation is proper. Remove filler words while preserving all medical details. "
            "Return only the cleaned text.\n\n"
            "Transcript:\n{text}"
        ),
        "legal": (
            "You are a legal transcription editor. Improve this legal transcript "
            "with proper grammar, punctuation, and formal language. Remove filler words "
            "while maintaining the exact meaning and all legal references. "
            "Return only the cleaned text.\n\n"
            "Transcript:\n{text}"
        ),
        "general": (
            "You are a professional transcript editor. Clean up this transcript by "
            "fixing grammar errors, adding proper punctuation, removing filler words "
            "(um, uh, like, you know), and improving readability. Keep the meaning exact. "
            "Return only the cleaned text.\n\n"
            "Transcript:\n{text}"
        ),
    }

    def __init__(
        self,
        host: str = "localhost",
        port: int = 11434,
        model: str = "llama3.1:8b",
        custom_prompts: Optional[Dict[str, str]] = None,
    ):
        """Initialize the Ollama text enhancer.

        Args:
            host: Ollama server hostname (default: "localhost")
            port: Ollama server port (default: 11434)
            model: Ollama model name (default: "llama3.1:8b")
            custom_prompts: Optional custom prompts for different contexts

        Raises:
            ImportError: If ollama package is not installed
        """
        if not OLLAMA_AVAILABLE:
            raise ImportError(
                "ollama is required for OllamaTextEnhancer. "
                "Install it with: pip install msprites2[ai]"
            )

        self.host = host
        self.port = port
        self.model = model
        self.client = ollama.Client(host=f"http://{host}:{port}")

        # Merge custom prompts with defaults
        self.prompts = self.DEFAULT_PROMPTS.copy()
        if custom_prompts:
            self.prompts.update(custom_prompts)

    async def enhance(self, text: str, context: str = "general") -> str:
        """Enhance transcript with domain-specific context.

        Args:
            text: Raw transcript text
            context: Domain context (technical, educational, medical, legal, general)

        Returns:
            Enhanced transcript text

        Raises:
            RuntimeError: If Ollama request fails
        """
        prompt = self._get_context_prompt(context, text)

        try:
            # Run Ollama request in thread pool to avoid blocking
            response = await asyncio.to_thread(
                self.client.chat,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )

            return response["message"]["content"].strip()

        except Exception as e:
            raise RuntimeError(
                f"Failed to enhance transcript with Ollama: {str(e)}"
            ) from e

    def _get_context_prompt(self, context: str, text: str) -> str:
        """Get the appropriate prompt for the given context.

        Args:
            context: Domain context
            text: Raw transcript text

        Returns:
            Formatted prompt string
        """
        prompt_template = self.prompts.get(context, self.prompts["general"])
        return prompt_template.format(text=text)

    def add_custom_context(self, context_name: str, prompt_template: str):
        """Add a custom context with its prompt template.

        Args:
            context_name: Name of the custom context
            prompt_template: Prompt template (use {text} placeholder for transcript)

        Example:
            >>> enhancer.add_custom_context(
            ...     "podcast",
            ...     "Clean up this podcast transcript for publication:\\n\\n{text}"
            ... )
        """
        self.prompts[context_name] = prompt_template


class SimpleEnhancer(TranscriptEnhancer):
    """Simple rule-based transcript enhancer without LLM dependency.

    This enhancer applies basic text cleaning rules:
    - Removes common filler words
    - Capitalizes sentences
    - Adds basic punctuation

    Useful for quick enhancements without requiring Ollama.
    """

    FILLER_WORDS = {
        "um",
        "uh",
        "like",
        "you know",
        "i mean",
        "sort of",
        "kind of",
        "basically",
        "actually",
        "literally",
    }

    async def enhance(self, text: str, context: str = "general") -> str:
        """Apply simple rule-based enhancements.

        Args:
            text: Raw transcript text
            context: Ignored for simple enhancer

        Returns:
            Enhanced transcript text
        """
        # Remove filler words
        words = text.lower().split()
        cleaned_words = [w for w in words if w not in self.FILLER_WORDS]
        text = " ".join(cleaned_words)

        # Basic capitalization
        sentences = text.split(".")
        sentences = [s.strip().capitalize() for s in sentences if s.strip()]
        text = ". ".join(sentences) + "."

        return text


def create_enhancer(
    enhancer_type: str = "ollama",
    **kwargs,
) -> TranscriptEnhancer:
    """Factory function to create transcript enhancers.

    Args:
        enhancer_type: Type of enhancer ("ollama", "simple")
        **kwargs: Additional arguments passed to enhancer constructor

    Returns:
        TranscriptEnhancer instance

    Example:
        >>> enhancer = create_enhancer("ollama", model="llama3.1:8b")
        >>> simple = create_enhancer("simple")
    """
    if enhancer_type == "ollama":
        return OllamaTextEnhancer(**kwargs)
    elif enhancer_type == "simple":
        return SimpleEnhancer()
    else:
        raise ValueError(
            f"Unknown enhancer type: {enhancer_type}. "
            "Valid options: 'ollama', 'simple'"
        )