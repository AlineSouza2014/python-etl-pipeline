"""Gerador reproduzivel de 50 mil pedidos inteiramente ficticios."""
import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

FIELDS = ["pedido_id", "data_pedido", "cliente", "valor", "status", "updated_at"]


def generate(output: Path, count: int = 50000, seed: int = 42) -> None:
    """Cria pedidos sinteticos deterministas, sem dados pessoais reais."""
    if count < 1:
        raise ValueError("count deve ser positivo")
    rng = random.Random(seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2024, 1, 1)
    statuses = ("aprovado", "pendente", "cancelado", "entregue")
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(FIELDS)
        for order_id in range(1, count + 1):
            day = start + timedelta(days=rng.randrange(731))
            updated = day + timedelta(hours=rng.randrange(1, 72))
            writer.writerow([
                order_id,
                day.date().isoformat(),
                f"Cliente {rng.randrange(1, 5001):05d}",
                f"{rng.uniform(20, 10000):.2f}",
                rng.choice(statuses),
                updated.isoformat(timespec="seconds"),
            ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera pedidos sinteticos")
    parser.add_argument("--count", type=int, default=50000)
    parser.add_argument("--output", type=Path, default=Path("dados/pedidos_50k.csv"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate(args.output, args.count, args.seed)
    print(f"Gerados {args.count} pedidos ficticios em {args.output}")
