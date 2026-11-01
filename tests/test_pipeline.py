import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.pipeline import run


class PipelineTests(unittest.TestCase):
    def test_idempotencia_e_validacao(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "test.db"
            source = Path(__file__).resolve().parents[1] / "dados" / "pedidos.csv"
            first = run(source, db)
            second = run(source, db)
            self.assertEqual(first["rejeitados"], 1)
            self.assertEqual(first["total_destino"], 3)
            self.assertEqual(second["total_destino"], 3)
            with sqlite3.connect(db) as conn:
                status = conn.execute("SELECT status FROM pedidos WHERE pedido_id=2").fetchone()[0]
                self.assertEqual(status, "aprovado")

    def test_registro_antigo_nao_sobrescreve_novo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "test.db"
            recent = root / "recent.csv"
            older = root / "older.csv"
            header = "pedido_id,data_pedido,cliente,valor,status,updated_at\n"
            recent.write_text(header + "7,2026-01-01,Cliente X,100,aprovado,2026-01-03T10:00:00\n", encoding="utf-8")
            older.write_text(header + "7,2026-01-01,Cliente X,100,pendente,2026-01-02T10:00:00\n", encoding="utf-8")
            run(recent, db)
            run(older, db)
            with sqlite3.connect(db) as conn:
                status = conn.execute("SELECT status FROM pedidos WHERE pedido_id=7").fetchone()[0]
                self.assertEqual(status, "aprovado")


if __name__ == "__main__":
    unittest.main()
