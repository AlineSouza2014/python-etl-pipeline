import csv
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from src.retail import generate, load

class RetailPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.data=self.root/'data';self.db=self.root/'retail.db'
        generate(self.data,n=200,seed=42)

    def tearDown(self):self.tmp.cleanup()

    def test_full_load_quality_and_gold(self):
        result=load(self.data,self.db)
        self.assertEqual(result['raw'],5602)
        self.assertEqual(result['rejected'],1)
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute('select count(*) from silver_orders').fetchone()[0],200)
            self.assertEqual(con.execute('select count(*) from rejects').fetchone()[0],1)
            self.assertGreater(con.execute('select count(*) from gold_daily_sales').fetchone()[0],0)

    def test_reprocessing_is_idempotent(self):
        load(self.data,self.db);load(self.data,self.db)
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute('select count(*) from silver_orders').fetchone()[0],200)
            self.assertEqual(con.execute('select count(*) from runs where status="success"').fetchone()[0],2)

    def test_late_arriving_older_update_does_not_overwrite(self):
        load(self.data,self.db)
        with (self.data/'orders.csv').open(newline='',encoding='utf-8') as f:
            rows=list(csv.DictReader(f));columns=list(rows[0])
        rows[0]['status']='cancelled';rows[0]['updated_at']='2023-01-01T00:00:00'
        with (self.data/'orders.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(rows)
        load(self.data,self.db)
        with closing(sqlite3.connect(self.db)) as con:
            status=con.execute('select status from silver_orders where order_id=1').fetchone()[0]
            self.assertNotEqual(status,'cancelled')

    def test_schema_failure_rolls_back(self):
        (self.data/'products.csv').write_text('wrong,columns\n1,2\n',encoding='utf-8')
        with self.assertRaises(ValueError):load(self.data,self.db)
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute('select count(*) from runs').fetchone()[0],0)
            self.assertEqual(con.execute('select count(*) from bronze').fetchone()[0],0)

if __name__=='__main__':unittest.main()
