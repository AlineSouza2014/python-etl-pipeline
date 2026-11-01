# ProspectAI | Pipeline ETL Incremental com Python e SQLite

Projeto demonstrativo de **Engenharia de Dados**, com dados inteiramente fictícios. Implementa ingestão CSV, validação, rejeição de linhas inválidas e carga incremental com **upsert** em SQLite.

## Arquitetura

```text
CSV de pedidos (dados fictícios)
         |
         v
Validação de esquema e regras de negócio
         |
         v
Normalização de tipos e datas
         |
         v
SQLite | INSERT / UPSERT por pedido_id e updated_at
         |
         v
Métricas e logs de execução
```

## Tecnologias

- Python 3.10+ (biblioteca padrão; sem dependências externas)
- SQL / SQLite
- unittest para testes automatizados

## Executar

Na raiz do repositório:

```bash
python -m src.pipeline --source dados/pedidos.csv --target saida/pedidos.db
python -m unittest discover -s tests -v
```

O exemplo contém cinco linhas de entrada, incluindo uma atualização do mesmo pedido e um registro inválido. O destino esperado contém **3 pedidos distintos** e **1 registro rejeitado**.

## Regras de qualidade

- `pedido_id` precisa ser um inteiro positivo.
- `valor` não pode ser negativo.
- `cliente` não pode estar vazio.
- Datas precisam estar em formato ISO válido.
- Um registro só atualiza o destino se seu `updated_at` for **mais recente** do que o armazenado.
- Reprocessar o mesmo arquivo não duplica pedidos.

## Estrutura

```text
.
├── dados/pedidos.csv
├── src/__init__.py
├── src/pipeline.py
├── tests/test_pipeline.py
├── .gitignore
└── README.md
```

## Limitações e evolução

Este é um projeto demonstrativo local, não uma solução implantada em produção. Próximos passos possíveis: PostgreSQL ou Delta Lake como destino, tabela de quarentena, métricas estruturadas e orquestração.

**ProspectAI** — Engenharia de Dados, BI e Automação  
Contato: prospectai.solucoes@gmail.com
