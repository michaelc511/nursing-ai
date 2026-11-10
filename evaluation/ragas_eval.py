"""RAGAS scoring for AI Assist answers (live evals only; needs ANTHROPIC_API_KEY).

Metrics: faithfulness (claims supported by the retrieved contexts), answer relevancy, and context
precision without a reference. Grader LLM: Claude (JUDGE_MODEL, default claude-opus-5-5) through
LangChain; embeddings: the same local MiniLM model the app uses (no patient data leaves for embeddings).
Kept out of the app's requirements: install with  pip install -r ../evaluation/requirements.txt
"""
import os
import warnings


def build():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from langchain_anthropic import ChatAnthropic
    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness, LLMContextPrecisionWithoutReference, ResponseRelevancy
    llm = LangchainLLMWrapper(ChatAnthropic(model=os.environ.get("JUDGE_MODEL") or "claude-opus-5-5",
                                            max_tokens=4000),
                              bypass_temperature=True)  # current Claude models reject a temperature setting
    emb = LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(
        model_name=os.environ.get("EMBED_MODEL") or "sentence-transformers/all-MiniLM-L6-v2"))
    return [Faithfulness(llm=llm), ResponseRelevancy(llm=llm, embeddings=emb),
            LLMContextPrecisionWithoutReference(llm=llm)]


def dataset(samples: list[dict]):
    from ragas import EvaluationDataset
    return EvaluationDataset.from_list([{"user_input": s["question"], "response": s["answer"],
                                         "retrieved_contexts": s["contexts"]} for s in samples])


def score(samples: list[dict]) -> dict:
    from ragas import evaluate
    if not samples:
        return {}
    res = evaluate(dataset(samples), metrics=build(), show_progress=False)
    df = res.to_pandas()
    return {c: round(float(df[c].mean()), 3) for c in df.columns
            if c not in ("user_input", "response", "retrieved_contexts") and df[c].dtype.kind == "f"}
