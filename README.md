# ProspectAI | Retail Data Platform

**Portfólio de Engenharia de Dados | Python + SQL + SQLite | Sem Docker e sem custos cloud**

Projeto demonstrativo completo para um **e-commerce fictício**. Consolida clientes, produtos, pedidos e pagamentos, aplica regras de qualidade e produz indicadores comerciais auditáveis. **Todos os dados são sintéticos; nenhum cliente real está representado.**

## Problema de negócio

O varejista recebe quatro arquivos diariamente, com atualizações atrasadas, pedidos duplicados e valores inválidos. O negócio precisa de uma base confiável para analisar receita, produtos e regiões, sem contar vendas canceladas ou pagamentos pendentes.

## Arquitetura

```text
4 CSVs sintéticos (customers, products, orders, payments)
                    |
             Python ingest
                    |
         Bronze: linhas brutas + hash + origem + run_id
                    |
         Validação: tipos, chaves, domínio e datas
               /                \
    Silver: UPSERT         Quarentena: rejects
    por chave e updated_at
               |
         Gold: views SQL
         receita por dia / categoria / região
               |
          Power BI (próximo projeto)
```

**Bronze** é append-only e preserva o histórico de cada execução. **Silver** mantém a versão mais recente de cada chave de negócio. **Gold** usa views SQL sobre Silver e considera apenas pedidos aprovados com pagamento confirmado. **Auditoria** registra início, fim, status e contagens por execução.

## Executar (Python 3.10+)

```bash
python -m src.retail generate --rows 50000
python -m src.retail load
python -m unittest discover -s tests -v
```

Não há dependências externas. O gerador cria 5.000 clientes, 200 produtos, **50.000 pedidos**, 50.000 pagamentos, uma duplicidade antiga e um pedido inválido para demonstrar quarentena. A execução completa deve registrar **105.202 linhas brutas** e **1 rejeição**; Silver deve conter 50.000 pedidos distintos.

Consulte a base gerada com SQLite, DBeaver ou Python:

```python
import sqlite3
with sqlite3.connect('output/retail.db') as db:
    print(db.execute('SELECT * FROM gold_category_sales ORDER BY revenue DESC').fetchall())
    print(db.execute('SELECT * FROM runs ORDER BY started_at DESC LIMIT 1').fetchone())
```

## Cenários de qualidade e reprocessamento

- Reexecução idempotente em Silver (não duplica chaves).
- Registro antigo não substitui uma atualização mais recente.
- Pedido com quantidade negativa vai para quarentena.
- Mudança indevida de cabeçalho aborta a execução com rollback transacional.
- Bronze armazena payload original, hash, arquivo e número da linha.

## Estrutura

```text
src/retail.py                 geração, ingestão, validação e carga
src/__init__.py              pacote Python
tests/test_retail.py          testes de integração locais
.github/workflows/tests.yml  CI de testes
.gitignore                   exclusões de artefatos locais
```

## Decisões técnicas e limitações

- **SQLite** foi escolhido para executar em qualquer notebook sem infraestrutura. O padrão pode ser adaptado para PostgreSQL ou Delta Lake.
- A carga incremental é implementada como **UPSERT por chave de negócio e `updated_at`**, e não como CDC ou extração por watermark na origem.
- Bronze é append-only: reprocessamentos repetem os registros brutos intencionalmente; Silver permanece idempotente.
- A transação é atômica para cada execução; em caso de erro estrutural, a carga é revertida.
- As regras de relacionamento entre fontes não aplicam quarentena de chaves órfãs nesta versão. Esse é um ponto de evolução.
- As métricas são registradas em `runs`, sem monitoramento externo ou agendador.

## Contato

**ProspectAI** — Engenharia de Dados, BI e Automação  
prospectai.solucoes@gmail.com
