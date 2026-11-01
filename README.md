# ProspectAI | Pipeline ETL Incremental com Python e SQLite

Projeto demonstrativo de **Engenharia de Dados**, com dados inteiramente fictícios. Implementa ingestão CSV, validação de esquema, rejeição de linhas inválidas e carga incremental com **upsert** em SQLite.

## Volume de dados

O repositório contém um exemplo pequeno para testes de regras e um **gerador determinístico de 50.000 pedidos fictícios**, distribuídos por 24 meses (2024–2025). A base grande é gerada localmente, evitando versionar arquivos volumosos.

## Arquitetura

```text
Gerador de dados sintéticos -> CSV
                               |
                               v
                   Validação de esquema e regras
                               |
                               v
                     Conversão de tipos/datas
                               |
                               v
                   SQLite: UPSERT por pedido_id
                   (somente updated_at mais recente)
                               |
                               v
                     Logs e métricas da carga
```

## Tecnologias

Python 3.10+, SQL, SQLite, biblioteca padrão Python e unittest. Não requer dependências externas.

## Executar com 50 mil pedidos

Na raiz do repositório:

```bash
python -m src.generate_data --count 50000 --output dados/pedidos_50k.csv
python -m src.pipeline --source dados/pedidos_50k.csv --target saida/pedidos.db
python -m unittest discover -s tests -v
```

O resultado esperado é **50.000 pedidos distintos** no destino. Execute o pipeline novamente para demonstrar que o reprocessamento não duplica registros.

Para testar as regras de rejeição e atualização de pedidos, utilize também o CSV pequeno:

```bash
python -m src.pipeline --source dados/pedidos.csv --target saida/teste.db
```

O exemplo pequeno possui cinco linhas, incluindo uma atualização de pedido e um valor inválido: o resultado esperado são 3 pedidos distintos e 1 registro rejeitado.

## Regras de qualidade

- `pedido_id` deve ser um inteiro positivo.
- `valor` não pode ser negativo.
- `cliente` não pode estar vazio.
- Datas devem ser válidas em formato ISO.
- O registro de origem só atualiza o destino se `updated_at` for mais recente.
- Reprocessar a mesma entrada não duplica pedidos.

## Estrutura

```text
dados/pedidos.csv          Exemplo de testes
src/generate_data.py       Gerador de 50 mil pedidos
src/pipeline.py            Validação e UPSERT
tests/test_pipeline.py     Testes automatizados
.gitignore                 Arquivos temporários ignorados
```

## Escopo e limitações

Este é um projeto demonstrativo local, não uma implantação de produção. O fluxo demonstra ingestão em lote e UPSERT; ainda não possui orquestração, monitoramento centralizado ou controle persistente de watermark para captura incremental na origem. Evoluções possíveis incluem PostgreSQL, Delta Lake, quarentena de registros e observabilidade.

**ProspectAI** — Engenharia de Dados, BI e Automação  
Contato: prospectai.solucoes@gmail.com
