# Testing Guide: Orchestrator & CLIs

This document explains how to use the CLI scripts developed for the **Diagnosis Retrieval System (SRI-DX)**. It focuses on executing the full processing pipeline and testing the lexical, semantic, and hybrid search methods.

## 1. Orchestrator CLI (`src/sri_dx/app/cli/orchestrator.py`)

The orchestrator is responsible for executing the complete data pipeline sequentially. It coordinates four major phases:

1. **Acquisition (Scraping)**: Polls guidelines and raw text.
2. **Document Indexing (OpenSearch)**: Indexes the full acquired documents natively using BM25.
3. **Chunk Indexing (OpenSearch)**: Applies semantic/sliding window chunking and extracts concepts/NER entities.
4. **Vector Generation (Embeddings)**: Batches chunks and calculates dense vectors using `Bio_ClinicalBERT`, persisting them back.

### Pre-descarga de Modelos (Recomendado para mala conexión)

Para evitar descargas inesperadas durante las pruebas, puedes bajar todos los modelos de una vez:

```bash
uv run download-models
```

Este comando descargará y cacheará localmente los modelos de Embeddings, Re-ranking y NER.

### Usage

To run the complete pipeline from scratch:

```bash
uv run python src/sri_dx/app/cli/orchestrator.py
```

### Skipping Phases

If you have already acquired data and only want to test the vector generation or text chunking, you can skip earlier phases:

```bash
# Skip acquiring new documents from the web
uv run python src/sri_dx/app/cli/orchestrator.py --skip-acquisition

# Re-run only the vector embedding generation
uv run python src/sri_dx/app/cli/orchestrator.py --skip-acquisition --skip-docs --skip-chunks
```

Available flags:

- `--skip-acquisition`
- `--skip-docs`
- `--skip-chunks`
- `--skip-embeddings`

---

## 2. Search CLI (`src/sri_dx/app/cli/search_cli.py`)

The search CLI allows you to directly query the OpenSearch ecosystem using either BM25 (Lexical), Dense Vectors (Semantic), or a combination of both (Hybrid).

### Basic Lexical Search (BM25)

This search runs exclusively over the `clinical_docs` index.

```bash
uv run python src/sri_dx/app/cli/search_cli.py --q "Diabetes Type 2 symptoms" --type lexical --k 5
```

### Semantic Search (kNN)

This search embeds the user query using `Bio_ClinicalBERT` and computes cosine similarity against all indexed chunks within `clinical_embeddings_v1`.

```bash
uv run python src/sri_dx/app/cli/search_cli.py --q "High blood pressure treatment" --type semantic --k 5
```

### Hybrid Search (Semantic + Lexical)

This search queries both backends concurrently and merges the rankings. By default, it uses **Reciprocal Rank Fusion (RRF)**.

```bash
uv run python src/sri_dx/app/cli/search_cli.py --q "Chikungunya and fever" --type hybrid --k 10
```

#### Advanced Hybrid Options

You can tweak the fusion strategy or semantic thresholds:

- `--fusion rrf` (Default): Uses mathematical rank positions to merge lists.
- `--fusion weighted_sum`: Uses actual score points (requires normalized scores across both strategies to work optimally).
- `--min-score 0.7`: Defines the minimum cosine-similarity score to consider a semantic result valid.

Example:

```bash
uv run python src/sri_dx/app/cli/search_cli.py --q "Chikungunya" --type hybrid --fusion weighted_sum --min-score 0.5
```

### Hybrid Search with Reranking (Cross-Encoder)

The system supports a second stage of refinement using a Cross-Encoder model. This is significantly more accurate as it evaluates the query and document together.

```bash
# Enable reranking (Top-10 by default)
uv run python src/sri_dx/app/cli/search_cli.py --q "Diabetes" --type hybrid --rerank

# Custom model and score threshold
uv run python src/sri_dx/app/cli/search_cli.py --q "Diabetes" --type hybrid --rerank --rerank-model "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1" --rerank-threshold 0.4
```

---

## 3. Standalone CLI Tools

While the orchestrator is recommended, you can run individual phases for granular testing:

### Indexing Chunks (`src/sri_dx/app/cli/index_chunks_cli.py`)
Processes raw JSONL documents into semantic chunks and extracts concepts.
```bash
uv run python src/sri_dx/app/cli/index_chunks_cli.py --max-chars 1000 --overlap 200
```

### Generating Embeddings (`src/sri_dx/app/cli/embed_cli.py`)
Generates dense vectors for existing chunks.
```bash
uv run python src/sri_dx/app/cli/embed_cli.py --batch-size 32 --chunks-index clinical_chunks_v1
```

## Internal Dependencies

- **Hardware**: Cross-Encoder and Embedding generation are CPU-intensive. Use `--device cuda` if a GPU is available (supports `cpu`, `cuda`, `mps`).
- **Models**: The first execution will download models from HuggingFace (ClinicalBERT and Cross-Encoder). Ensure internet access or pre-cached models in `~/.cache/huggingface`.
- **OpenSearch**: Must be running and healthy (see [docker_setup.md](file:///home/jean/School/SRI/Diagnosis-Retrieval-System/doc/dev/testing/docker_setup.md)).
