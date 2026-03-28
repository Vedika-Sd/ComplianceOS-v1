"""
core/llm_provider.py
Centralised LLM setup.
Primary  : Groq  (llama-3.1-70b-versatile) — free tier, very fast
Fallback : Ollama (local, no API key)
"""
import os
from dotenv import load_dotenv

load_dotenv()


def get_llm(temperature: float = 0.1):
    groq_key = os.getenv("GROQ_API_KEY", "")

    if groq_key and groq_key != "your_groq_api_key_here":
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                api_key=groq_key,
                model=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
                temperature=temperature,
                max_tokens=2048,
            )
            return llm
        except Exception as e:
            print(f"⚠️  Groq init failed: {e}")

    try:
        from langchain_community.llms import Ollama
        return Ollama(model="llama3.1", temperature=temperature)
    except Exception:
        pass

    raise EnvironmentError(
        "\n❌ No LLM configured!\n"
        "Get a FREE Groq key at https://console.groq.com\n"
        "Then set GROQ_API_KEY in your .env file\n"
    )


def get_embeddings():
    from langchain_community.embeddings import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def call_llm_simple(prompt: str, temperature: float = 0.1) -> str:
    """Simple string in → string out LLM call. Used by agents."""
    try:
        llm = get_llm(temperature)
        result = llm.invoke(prompt)
        if hasattr(result, "content"):
            return result.content
        return str(result)
    except Exception as e:
        return f"[LLM unavailable: {e}]"