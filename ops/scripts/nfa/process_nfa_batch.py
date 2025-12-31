#!/usr/bin/env python3
"""
NFA Batch Processor - Processa lotes de NFAs a partir de dados compartilhados.

Este script aceita:
- Lista de números NFA (JSON, CSV, TXT)
- Range de datas (processa todas as NFAs do período)
- Dados estruturados em qualquer formato

Usage:
    # Processar lista de números NFA
    python3 process_nfa_batch.py --input nfa_list.json --mode numbers

    # Processar por range de datas
    python3 process_nfa_batch.py --from-date 01/12/2025 --to-date 31/12/2025 --mode date-range

    # Processar arquivo CSV com coluna NFA
    python3 process_nfa_batch.py --input nfa_batch.csv --mode csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

try:
    from app.services.logging_utils import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        return logger

logger = get_logger(__name__)

# Import NFA automation
sys.path.insert(0, str(SCRIPT_DIR))
from nfa_atf import NFAATFAutomation

OUTPUT_DIR = Path("/Users/dnigga/Downloads/NFA_Outputs")
BATCH_RESULTS_FILE = OUTPUT_DIR / "batch_results.jsonl"


def load_nfa_numbers_from_json(file_path: Path) -> List[str]:
    """Carrega lista de números NFA de arquivo JSON."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Suporta múltiplos formatos:
    # 1. Lista simples: ["400123456", "400123457", ...]
    # 2. Objeto com chave "nfa_numbers": {"nfa_numbers": [...]}
    # 3. Lista de objetos: [{"nfa": "400123456"}, ...]
    
    if isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], str):
            # Formato 1: Lista simples de strings
            return data
        elif len(data) > 0 and isinstance(data[0], dict):
            # Formato 3: Lista de objetos
            nfa_numbers = []
            for item in data:
                # Tenta várias chaves comuns
                nfa = item.get("nfa") or item.get("nfa_number") or item.get("numero") or item.get("NFA")
                if nfa:
                    nfa_numbers.append(str(nfa))
            return nfa_numbers
    elif isinstance(data, dict):
        # Formato 2: Objeto com chave
        nfa_numbers = data.get("nfa_numbers") or data.get("nfas") or data.get("numbers")
        if nfa_numbers:
            return [str(n) for n in nfa_numbers]
    
    raise ValueError(f"Formato JSON não reconhecido em {file_path}")


def load_nfa_numbers_from_csv(file_path: Path, nfa_column: str = "NFA") -> List[str]:
    """Carrega lista de números NFA de arquivo CSV."""
    nfa_numbers = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Tenta várias variações do nome da coluna
            nfa = (
                row.get(nfa_column) or
                row.get("nfa") or
                row.get("nfa_number") or
                row.get("numero") or
                row.get("NFA_NUMBER")
            )
            if nfa:
                nfa_numbers.append(str(nfa).strip())
    
    return nfa_numbers


def load_nfa_numbers_from_txt(file_path: Path) -> List[str]:
    """Carrega lista de números NFA de arquivo TXT (um por linha)."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    nfa_numbers = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):  # Ignora linhas vazias e comentários
            # Remove espaços e caracteres especiais, mantém apenas números
            nfa = "".join(c for c in line if c.isdigit())
            if nfa:
                nfa_numbers.append(nfa)
    
    return nfa_numbers


def load_nfa_numbers(input_file: Path, mode: str) -> List[str]:
    """Carrega números NFA do arquivo de entrada."""
    if not input_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_file}")
    
    extension = input_file.suffix.lower()
    
    if extension == ".json":
        return load_nfa_numbers_from_json(input_file)
    elif extension == ".csv":
        return load_nfa_numbers_from_csv(input_file)
    elif extension == ".txt":
        return load_nfa_numbers_from_txt(input_file)
    else:
        raise ValueError(f"Formato não suportado: {extension}. Use .json, .csv ou .txt")


async def process_nfa_batch(
    nfa_numbers: List[str],
    from_date: str,
    to_date: str,
    matricula: str,
    headless: bool = True,
    max_retries: int = 2,
) -> List[Dict[str, Any]]:
    """
    Processa lote de NFAs.
    
    Args:
        nfa_numbers: Lista de números NFA para processar
        from_date: Data inicial (dd/mm/yyyy)
        to_date: Data final (dd/mm/yyyy)
        matricula: Matrícula
        headless: Executar browser em modo headless
        max_retries: Número máximo de tentativas por NFA
    
    Returns:
        Lista de resultados (um por NFA)
    """
    results = []
    total = len(nfa_numbers)
    
    logger.info(f"Iniciando processamento de lote: {total} NFAs")
    
    # Inicializa automação uma vez (reutiliza sessão)
    username = os.getenv("NFA_USERNAME")
    password = os.getenv("NFA_PASSWORD")
    
    if not username or not password:
        raise RuntimeError("NFA_USERNAME e NFA_PASSWORD devem estar definidos")
    
    automation = NFAATFAutomation(
        username=username,
        password=password,
        from_date=from_date,
        to_date=to_date,
        matricula=matricula,
        output_dir=str(OUTPUT_DIR),
        headless=headless,
    )
    
    try:
        # Setup e login uma vez
        await automation.setup()
        await automation.login()
        await automation.navigate_to_fis_308()
        await automation.fill_filters()
        
        # Processa cada NFA
        for idx, nfa_number in enumerate(nfa_numbers, 1):
            logger.info(f"Processando NFA {idx}/{total}: {nfa_number}")
            
            result = {
                "nfa_number": nfa_number,
                "status": "error",
                "danfe_path": None,
                "dar_path": None,
                "error": None,
                "started_at": datetime.utcnow().isoformat(),
                "finished_at": None,
            }
            
            try:
                # Seleciona NFA específica
                await automation.select_nfa_result(nfa_number=nfa_number, index=0)
                
                # Download DANFE
                danfe_path = await automation.download_danfe()
                result["danfe_path"] = danfe_path
                
                # Download Taxa Serviço
                dar_path = await automation.download_dar()
                result["dar_path"] = dar_path
                
                result["status"] = "success"
                logger.info(f"NFA {nfa_number} processada com sucesso")
                
            except Exception as e:
                result["error"] = str(e)
                logger.error(f"Erro ao processar NFA {nfa_number}: {e}", exc_info=True)
            
            finally:
                result["finished_at"] = datetime.utcnow().isoformat()
                results.append(result)
                
                # Salva resultado incrementalmente
                with open(BATCH_RESULTS_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
        
    finally:
        # Cleanup (fecha browser)
        await automation.cleanup()
    
    return results


async def process_date_range(
    from_date: str,
    to_date: str,
    matricula: str,
    max_nfas: int = 100,
    headless: bool = True,
) -> Dict[str, Any]:
    """
    Processa todas as NFAs de um range de datas.
    
    Args:
        from_date: Data inicial (dd/mm/yyyy)
        to_date: Data final (dd/mm/yyyy)
        matricula: Matrícula
        max_nfas: Número máximo de NFAs para processar
        headless: Executar browser em modo headless
    
    Returns:
        Resultado completo com todas as NFAs processadas
    """
    username = os.getenv("NFA_USERNAME")
    password = os.getenv("NFA_PASSWORD")
    
    if not username or not password:
        raise RuntimeError("NFA_USERNAME e NFA_PASSWORD devem estar definidos")
    
    automation = NFAATFAutomation(
        username=username,
        password=password,
        from_date=from_date,
        to_date=to_date,
        matricula=matricula,
        output_dir=str(OUTPUT_DIR),
        headless=headless,
    )
    
    # Usa o método run() que já processa múltiplas NFAs
    result = await automation.run(nfa_number=None, max_nfas=max_nfas, download_dar=True)
    
    return result


async def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NFA Batch Processor - Processa lotes de NFAs"
    )
    
    parser.add_argument(
        "--input",
        type=Path,
        help="Arquivo de entrada (JSON, CSV ou TXT) com números NFA",
    )
    parser.add_argument(
        "--mode",
        choices=["numbers", "date-range", "csv"],
        default="numbers",
        help="Modo de processamento: numbers (lista), date-range (por datas), csv (CSV)",
    )
    parser.add_argument(
        "--from-date",
        help="Data inicial (dd/mm/yyyy) - obrigatório para date-range",
    )
    parser.add_argument(
        "--to-date",
        help="Data final (dd/mm/yyyy) - obrigatório para date-range",
    )
    parser.add_argument(
        "--matricula",
        default="1595504",
        help="Matrícula (padrão: 1595504)",
    )
    parser.add_argument(
        "--max-nfas",
        type=int,
        default=100,
        help="Número máximo de NFAs para processar (modo date-range, padrão: 100)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Executar browser em modo headless (padrão: True)",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Executar browser com interface visível",
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "date-range":
            # Modo: processar por range de datas
            if not args.from_date or not args.to_date:
                parser.error("--from-date e --to-date são obrigatórios no modo date-range")
            
            logger.info(f"Processando NFAs por range de datas: {args.from_date} a {args.to_date}")
            result = await process_date_range(
                from_date=args.from_date,
                to_date=args.to_date,
                matricula=args.matricula,
                max_nfas=args.max_nfas,
                headless=args.headless,
            )
            
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result.get("status") == "success" else 1
        
        elif args.mode in ["numbers", "csv"]:
            # Modo: processar lista de números NFA
            if not args.input:
                parser.error("--input é obrigatório no modo numbers/csv")
            
            if not args.from_date or not args.to_date:
                parser.error("--from-date e --to-date são obrigatórios no modo numbers/csv")
            
            # Carrega números NFA do arquivo
            nfa_numbers = load_nfa_numbers(args.input, args.mode)
            logger.info(f"Carregados {len(nfa_numbers)} números NFA de {args.input}")
            
            if not nfa_numbers:
                logger.error("Nenhum número NFA encontrado no arquivo")
                return 1
            
            # Processa lote
            results = await process_nfa_batch(
                nfa_numbers=nfa_numbers,
                from_date=args.from_date,
                to_date=args.to_date,
                matricula=args.matricula,
                headless=args.headless,
            )
            
            # Estatísticas
            success_count = sum(1 for r in results if r["status"] == "success")
            error_count = len(results) - success_count
            
            summary = {
                "total": len(results),
                "success": success_count,
                "errors": error_count,
                "results": results,
            }
            
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            return 0 if error_count == 0 else 1
        
        else:
            parser.error(f"Modo não suportado: {args.mode}")
    
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        error_result = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
