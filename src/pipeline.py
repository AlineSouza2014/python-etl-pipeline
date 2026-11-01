"""Pipeline demonstrativo: CSV -> SQLite com validacao e upsert idempotente."""
import argparse
import csv
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

LOG = logging.getLogger("prospectai_etl")


def run(source: Path, target: Path) -> dict:
    """Valida pedidos e faz upsert sem substituir registros por versoes antigas."""
    target.parent.mkdir(parents=True, exist_ok=True)
    valid = []
    rejected = 0
    with source.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"pedido_id", "data_pedido", "cliente", "valor", "status", "updated_at"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Colunas obrigatorias ausentes: {sorted(missing)}")
        for row in reader:
            try:
                order_id = int(row["pedido_id"])
                amount = round(float(row["valor"]), 2)
                date = datetime.fromisoformat(row["data_pedido"]).date().isoformat()
                updated = datetime.fromisoformat(row["updated_at"]).isoformat()
                customer = row["cliente"].strip()
                if order_id <= 0 or amount < 0 or not customer:
                    raise ValueError("Valores invalidos")
                valid.append((order_id, date, customer, amount, row["status"].strip(), updated))
            except (ValueError, TypeError, KeyError, AttributeError):
                rejected += 1

    with sqlite3.connect(target) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS pedidos (
            pedido_id INTEGER PRIMARY KEY,
            data_pedido TEXT NOT NULL,
            cliente TEXT NOT NULL,
            valor REAL NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        conn.executemany("""INSERT INTO pedidos VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(pedido_id) DO UPDATE SET
                data_pedido=excluded.data_pedido,
                cliente=excluded.cliente,
                valor=excluded.valor,
                status=excluded.status,
                updated_at=excluded.updated_at
            WHERE excluded.updated_at > pedidos.updated_at""", valid)
        total = conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    LOG.info("Recebidos=%d validos=%d rejeitados=%d total_destino=%d", len(valid)+rejected, len(valid), rejected, total)
    return {"validos": len(valid), "rejeitados": rejected, "total_destino": total}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline ETL demonstrativo ProspectAI")
    parser.add_argument("--source", type=Path, default=Path("dados/pedidos.csv"))
    parser.add_argument("--target", type=Path, default=Path("saida/pedidos.db"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(run(args.source, args.target))
