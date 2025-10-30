# Execution Tracking - Quick Start

## O que foi implementado

Sistema completo de rastreamento de execução para o pipeline HiPS que:
- ✅ Registra automaticamente todos os jobs do Slurm
- ✅ Calcula tempo de execução entre fases (index, regions, concat)
- ✅ Gera relatórios detalhados com estatísticas
- ✅ Usa `sacct` do Slurm para obter informações precisas

## Uso Básico

### 1. Executar o pipeline (tracking automático)

```bash
bin/hips-creator -c config.yaml
```

O tracking acontece automaticamente! Ao final, você verá um relatório no terminal.

### 2. Consultar status depois

```bash
# Ver relatório atual
bin/hips-execution-status -d /path/to/output_dir

# Atualizar com dados mais recentes do Slurm
bin/hips-execution-status -d /path/to/output_dir -u

# Salvar relatório em arquivo
bin/hips-execution-status -d /path/to/output_dir -u -o report.txt
```

### 3. Análise avançada (opcional)

```bash
python examples/analyze_execution.py /path/to/output_dir
```

## Arquivos Gerados

- `output_dir/execution_tracking.json` - Dados brutos do tracking
- `output_dir/execution_report.txt` - Relatório legível

## Informações Capturadas

Para cada fase (index, regions, concat):
- ⏱️ Tempo de início e fim
- 📊 Lista de todos os job IDs do Slurm
- ✅ Status de cada job (COMPLETED, FAILED, etc.)
- ⚡ Tempo de execução individual
- 💾 Uso de memória (MaxRSS)
- 📈 Estatísticas agregadas (média, total, etc.)

## Exemplo de Saída

```
================================================================================
HiPS Generation Execution Report
================================================================================

Phase: INDEX
  Status: completed
  Started: 2025-10-28T18:30:00
  Ended: 2025-10-28T18:35:00
  Total Jobs: 1
  Completed: 1
  Total Elapsed Time: 4m 55s

Phase: REGIONS
  Status: completed
  Started: 2025-10-28T18:35:01
  Ended: 2025-10-28T19:45:00
  Total Jobs: 24
  Completed: 24
  Total Elapsed Time: 2h 15m 30s
  Average Job Time: 5m 38s

Phase: CONCAT
  ...
```

## Mais Informações

Ver documentação completa em: `docs/EXECUTION_TRACKING.md`
