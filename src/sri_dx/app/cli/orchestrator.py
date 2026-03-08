# src/sri_dx/app/cli/orchestrator.py
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Orchestrator")

def run_cmd(cmd: list[str], desc: str) -> bool:
    logger.info(f"=== INICIANDO: {desc} ===")
    logger.info(f"Comando: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        logger.info(f"=== COMPLETO: {desc} ===\n")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Fallo en: {desc}. Código de salida: {e.returncode}")
        return False
    except FileNotFoundError:
        logger.error("Comando no encontrado. Ejecuta dentro de 'uv run'.")
        return False

def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta de principio a fin el pipeline SRI-DX.")
    parser.add_argument("--skip-acquisition", action="store_true", help="Salta la Fase 1 (Scraping)")
    parser.add_argument("--skip-docs", action="store_true", help="Salta la Fase 2 (Docs OpenSearch)")
    parser.add_argument("--skip-chunks", action="store_true", help="Salta la Fase 3 (Chunks OpenSearch)")
    parser.add_argument("--skip-embeddings", action="store_true", help="Salta la Fase 4 (Vector DB)")
    args = parser.parse_args()

    steps = [
        {"desc": "Fase 1: Adquisición", "cmd": ["uv", "run", "python", "src/sri_dx/scripts/run_acquisition.py"], "skip": args.skip_acquisition},
        {"desc": "Fase 2: Indexación Docs", "cmd": ["uv", "run", "python", "src/sri_dx/app/cli/index_opensearch.py"], "skip": args.skip_docs},
        {"desc": "Fase 3: Indexación Chunks", "cmd": ["uv", "run", "python", "src/sri_dx/app/cli/index_chunks_cli.py"], "skip": args.skip_chunks},
        {"desc": "Fase 4: Embeddings", "cmd": ["uv", "run", "python", "src/sri_dx/app/embed_cli.py"], "skip": args.skip_embeddings},
    ]

    for step in steps:
        if step["skip"]:
            logger.info(f"[*] SALTADO: {step['desc']}\n")
            continue
        if not run_cmd(step["cmd"], step["desc"]):
            sys.exit(1)

    logger.info("🎉 Pipeline completado existosamente.")

if __name__ == "__main__":
    main()
