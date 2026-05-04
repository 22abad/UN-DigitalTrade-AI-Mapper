"""Cost estimator script for Technical Memo.

This script estimates the API costs for processing a 50-page legal document.
Requirement from Q&A: "Cost estimate per 50-page doc must be in the Memo."

Assumptions for a 50-page legal document:
- 50 pages * ~400 words/page = 20,000 words.
- Tokens: ~25,000 tokens per document.
- Chunks: ~50 articles/clauses.
- The classifier filters these down to ~10 relevant chunks.
- The 10 relevant chunks are sent to the LLM for feature extraction.
- Each extraction prompt is ~1,000 tokens. Output is ~150 tokens.
- Total input tokens to LLM: 10 * 1,000 = 10,000 tokens.
- Total output tokens from LLM: 10 * 150 = 1,500 tokens.

Pricing (per 1M tokens, hypothetical/approximate USD):
- Gemini 1.5 Flash: $0.35 Input / $1.05 Output
- Claude 3.5 Sonnet: $3.00 Input / $15.00 Output
- Llama 3 8B (Local): $0.00
"""

import os
from providers import get_provider

def estimate_cost(provider_name: str, input_tokens: int, output_tokens: int) -> float:
    try:
        p = get_provider(provider_name)
        return p.estimate_cost_usd(input_tokens, output_tokens)
    except Exception as e:
        print(f"Failed to load provider {provider_name}: {e}")
        return 0.0

def run_estimation():
    print("--- RDTII AI Mapper: 50-Page Document Cost Estimation ---")
    
    # Using the assumptions listed above
    input_tokens = 10000
    output_tokens = 1500
    
    print(f"Assumed Input Tokens: {input_tokens:,}")
    print(f"Assumed Output Tokens: {output_tokens:,}")
    print("-" * 50)
    
    providers_to_test = ["gemini", "claude", "llama-3-local"]
    
    for provider in providers_to_test:
        cost = estimate_cost(provider, input_tokens, output_tokens)
        print(f"Provider: {provider:<15} | Estimated Cost: ${cost:.6f}")

    print("-" * 50)
    print("Note: Copy these figures into your Technical Memo submission.")

if __name__ == "__main__":
    run_estimation()
