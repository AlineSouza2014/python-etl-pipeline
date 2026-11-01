"""ProspectAI Retail Data Platform: deterministic, auditable local ELT."""
import argparse
import csv
import hashlib
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random

SCHEMAS = {
    'customers': ('customer_id', 'customer_name', 'region', 'updated_at'),
    'products': ('product_id', 'category', 'unit_price', 'updated_at'),
    'orders': ('order_id', 'customer_id', 'product_id', 'quantity', 'ordered_at', 'status', 'updated_at'),
    'payments': ('payment_id', 'order_id', 'amount', 'payment_status', 'updated_at'),
}
KEYS = {'customers': 'customer_id', 'products': 'product_id', 'orders': 'order_id', 'payments': 'payment_id'}
VALID_STATUS = {'approved', 'pending', 'cancelled'}
LOG = logging.getLogger('retail')


def generate(folder: Path, n: int = 50000, seed: int = 42) -> None:
    """Generate deterministic, entirely synthetic data, including controlled defects."""
    if n < 1:
        raise ValueError('n must be positive')
    folder.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    start = datetime(2024, 1, 1)
    def save(entity, rows):
        with (folder / f'{entity}.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=SCHEMAS[entity]); writer.writeheader(); writer.writerows(rows)
    customers = [{'customer_id':str(i),'customer_name':f'Customer {i:05d}', 'region':rng.choice(['SP','RJ','MG','BA','PR']), 'updated_at':'2025-01-01T00:00:00'} for i in range(1,5001)]
    products = [{'product_id':str(i),'category':rng.choice(['Electronics','Home','Fashion','Sports']), 'unit_price':f'{rng.uniform(15,1200):.2f}', 'updated_at':'2025-01-01T00:00:00'} for i in range(1,201)]
    orders=[]; payments=[]
    for i in range(1,n+1):
        dt=start+timedelta(days=rng.randrange(730), hours=rng.randrange(24))
        product=rng.randrange(1,201); qty=rng.randrange(1,5)
        status=rng.choices(['approved','pending','cancelled'],weights=[80,12,8])[0]
        orders.append({'order_id':str(i),'customer_id':str(rng.randrange(1,5001)), 'product_id':str(product), 'quantity':str(qty), 'ordered_at':dt.isoformat(timespec='seconds'), 'status':status,'updated_at':(dt+timedelta(hours=2)).isoformat(timespec='seconds')})
        payments.append({'payment_id':str(i),'order_id':str(i),'amount':f'{float(products[product-1]["unit_price"])*qty:.2f}', 'payment_status':'paid' if status=='approved' else 'unpaid', 'updated_at':(dt+timedelta(hours=3)).isoformat(timespec='seconds')})
    orders.append(dict(orders[0], status='pending', updated_at='2023-01-01T00:00:00'))
    orders.append(dict(orders[1], quantity='-3', updated_at='2026-01-01T00:00:00'))
    for entity, rows in [('customers',customers),('products',products),('orders',orders),('payments',payments)]: save(entity,rows)


def connect(db: Path):
    db.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(db)
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript("""
    CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT, status TEXT NOT NULL, raw_count INTEGER DEFAULT 0, rejected_count INTEGER DEFAULT 0, details TEXT);
    CREATE TABLE IF NOT EXISTS bronze(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, entity TEXT NOT NULL, source_file TEXT NOT NULL, line_number INTEGER NOT NULL, payload TEXT NOT NULL, payload_hash TEXT NOT NULL, loaded_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS rejects(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, entity TEXT NOT NULL, line_number INTEGER NOT NULL, reason TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS silver_customers(customer_id INTEGER PRIMARY KEY, customer_name TEXT NOT NULL, region TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS silver_products(product_id INTEGER PRIMARY KEY, category TEXT NOT NULL, unit_price REAL NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS silver_orders(order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, ordered_at TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS silver_payments(payment_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, amount REAL NOT NULL, payment_status TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE VIEW IF NOT EXISTS gold_daily_sales AS SELECT substr(o.ordered_at,1,10) AS sale_date, COUNT(*) AS orders, ROUND(SUM(p.amount),2) AS revenue FROM silver_orders o JOIN silver_payments p ON p.order_id=o.order_id AND p.payment_status='paid' WHERE o.status='approved' GROUP BY substr(o.ordered_at,1,10);
    CREATE VIEW IF NOT EXISTS gold_category_sales AS SELECT pr.category, COUNT(*) AS orders, ROUND(SUM(pa.amount),2) AS revenue FROM silver_orders o JOIN silver_products pr ON pr.product_id=o.product_id JOIN silver_payments pa ON pa.order_id=o.order_id AND pa.payment_status='paid' WHERE o.status='approved' GROUP BY pr.category;
    CREATE VIEW IF NOT EXISTS gold_region_sales AS SELECT c.region, COUNT(*) AS orders, ROUND(SUM(pa.amount),2) AS revenue FROM silver_orders o JOIN silver_customers c ON c.customer_id=o.customer_id JOIN silver_payments pa ON pa.order_id=o.order_id AND pa.payment_status='paid' WHERE o.status='approved' GROUP BY c.region;
    """)
    return con


def normalize(entity, row):
    """Validate source row and return typed record for Silver."""
    if any(row.get(k) is None or not str(row[k]).strip() for k in SCHEMAS[entity]): raise ValueError('missing_required_value')
    key=int(row[KEYS[entity]])
    if key <= 0: raise ValueError('invalid_primary_key')
    updated=datetime.fromisoformat(row['updated_at']).isoformat(timespec='seconds')
    if entity=='customers': return (key,row['customer_name'].strip(),row['region'].strip(),updated)
    if entity=='products':
        price=float(row['unit_price'])
        if price <= 0: raise ValueError('invalid_unit_price')
        return (key,row['category'].strip(),price,updated)
    if entity=='orders':
        customer=int(row['customer_id']); product=int(row['product_id']); qty=int(row['quantity'])
        ordered=datetime.fromisoformat(row['ordered_at']).isoformat(timespec='seconds')
        if customer<=0 or product<=0 or qty<=0 or row['status'] not in VALID_STATUS: raise ValueError('invalid_order')
        return (key,customer,product,qty,ordered,row['status'],updated)
    order=int(row['order_id']); amount=float(row['amount'])
    if order<=0 or amount<0 or row['payment_status'] not in {'paid','unpaid'}: raise ValueError('invalid_payment')
    return (key,order,amount,row['payment_status'],updated)


def load(folder: Path, db: Path):
    """Atomic run: persist Bronze, quarantine invalid rows and upsert newer Silver records."""
    run_id=uuid.uuid4().hex
    started=datetime.now(timezone.utc).isoformat()
    counts={'raw':0,'rejected':0,'accepted':0}
    con=connect(db)
    try:
        with con:
            con.execute('INSERT INTO runs(run_id,started_at,status) VALUES(?,?,?)',(run_id,started,'running'))
            for entity, fields in SCHEMAS.items():
                path=folder/f'{entity}.csv'
                with path.open(newline='',encoding='utf-8-sig') as f:
                    reader=csv.DictReader(f)
                    if set(reader.fieldnames or [])!=set(fields): raise ValueError(f'{entity}: invalid schema')
                    for line,row in enumerate(reader,start=2):
                        counts['raw']+=1
                        payload=json.dumps(row,sort_keys=True,ensure_ascii=False)
                        digest=hashlib.sha256(payload.encode()).hexdigest()
                        con.execute('INSERT INTO bronze(run_id,entity,source_file,line_number,payload,payload_hash,loaded_at) VALUES(?,?,?,?,?,?,?)',(run_id,entity,path.name,line,payload,digest,started))
                        try:
                            record=normalize(entity,row)
                        except (ValueError,TypeError,OverflowError) as exc:
                            counts['rejected']+=1
                            con.execute('INSERT INTO rejects(run_id,entity,line_number,reason,payload) VALUES(?,?,?,?,?)',(run_id,entity,line,str(exc),payload))
                            continue
                        cols=fields
                        sql=f"""INSERT INTO silver_{entity} ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)}) ON CONFLICT({KEYS[entity]}) DO UPDATE SET {','.join(f'{c}=excluded.{c}' for c in cols if c!=KEYS[entity])} WHERE excluded.updated_at > silver_{entity}.updated_at"""
                        con.execute(sql,record)
                        counts['accepted']+=1
            con.execute('UPDATE runs SET ended_at=?,status=?,raw_count=?,rejected_count=?,details=? WHERE run_id=?',(datetime.now(timezone.utc).isoformat(),'success',counts['raw'],counts['rejected'],json.dumps(counts),run_id))
        LOG.info('run=%s %s',run_id,counts)
        return counts
    finally:
        con.close()


def main():
    parser=argparse.ArgumentParser(description='ProspectAI Retail Data Platform')
    sub=parser.add_subparsers(dest='command',required=True)
    g=sub.add_parser('generate');g.add_argument('--rows',type=int,default=50000);g.add_argument('--folder',type=Path,default=Path('data/synthetic'))
    l=sub.add_parser('load');l.add_argument('--folder',type=Path,default=Path('data/synthetic'));l.add_argument('--db',type=Path,default=Path('output/retail.db'))
    args=parser.parse_args();logging.basicConfig(level=logging.INFO)
    if args.command=='generate':generate(args.folder,args.rows);print(f'Generated {args.rows} synthetic orders')
    else:print(json.dumps(load(args.folder,args.db),indent=2))


if __name__=='__main__':main()
