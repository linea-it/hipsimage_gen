# Execution Tracking

O módulo de rastreamento de execução permite calcular e monitorar o tempo de execução entre as fases do processo de geração de HiPS (index, regions e concat) quando os jobs são executados no Slurm.

## Funcionalidades

- **Rastreamento Automático**: Registra automaticamente todos os jobs submetidos em cada fase
- **Integração com Slurm**: Usa `sacct` para obter informações detalhadas dos jobs (tempo de execução, uso de memória, status)
- **Relatórios Detalhados**: Gera relatórios legíveis com estatísticas de execução
- **Formato JSON**: Salva dados em JSON para análise posterior

## Como Usar

### 1. Executar o hips-creator normalmente

O tracking é automático quando você executa o `hips-creator`:

```bash
bin/hips-creator -c config.yaml
```

Isso irá:
- Criar um arquivo `execution_tracking.json` no diretório de saída
- Registrar todos os jobs submetidos ao Slurm
- Gerar um relatório no final da execução

### 2. Consultar o Status da Execução

Você pode consultar o status a qualquer momento usando:

```bash
bin/hips-execution-status -d /path/to/output_dir
```

#### Opções disponíveis:

- `-d, --output-dir`: Diretório que contém o arquivo `execution_tracking.json` (obrigatório)
- `-u, --update`: Atualiza as informações dos jobs consultando o Slurm antes de exibir
- `-o, --output`: Salva o relatório em um arquivo específico
- `-j, --json`: Exibe os dados brutos em formato JSON

#### Exemplos:

```bash
# Visualizar relatório atual
bin/hips-execution-status -d /mnt/data/hips/output

# Atualizar informações do Slurm e visualizar
bin/hips-execution-status -d /mnt/data/hips/output -u

# Salvar relatório em arquivo
bin/hips-execution-status -d /mnt/data/hips/output -u -o report.txt

# Ver dados JSON brutos
bin/hips-execution-status -d /mnt/data/hips/output -j
```

## Estrutura dos Dados

### Arquivo execution_tracking.json

```json
{
  "started_at": "2025-10-28T18:30:00.123456",
  "phases": {
    "index": {
      "started_at": "2025-10-28T18:30:00.123456",
      "ended_at": "2025-10-28T18:35:00.123456",
      "status": "completed",
      "job_ids": [12345]
    },
    "regions": {
      "started_at": "2025-10-28T18:35:01.123456",
      "ended_at": "2025-10-28T19:45:00.123456",
      "status": "completed",
      "job_ids": [12346, 12347, 12348, ...]
    },
    "concat": {
      "started_at": "2025-10-28T19:45:01.123456",
      "ended_at": "2025-10-28T20:30:00.123456",
      "status": "completed",
      "job_ids": [12400, 12401, ...]
    }
  },
  "jobs": {
    "12345": {
      "phase": "index",
      "submitted_at": "2025-10-28T18:30:00.123456",
      "metadata": {
        "output_dir": "/path/to/output/index"
      },
      "slurm_info": {
        "job_id": "12345",
        "job_name": "index.sbatch",
        "state": "COMPLETED",
        "start": "2025-10-28T18:30:05",
        "end": "2025-10-28T18:35:00",
        "elapsed": "00:04:55",
        "cpu_time": "00:04:55",
        "max_rss": "2048M",
        "exit_code": "0:0"
      }
    }
  }
}
```

## Exemplo de Relatório

```
================================================================================
HiPS Generation Execution Report
================================================================================

Started at: 2025-10-28T18:30:00.123456

--------------------------------------------------------------------------------

Phase: INDEX
  Status: completed
  Started: 2025-10-28T18:30:00.123456
  Ended: 2025-10-28T18:35:00.123456
  Total Jobs: 1
  Job IDs: 12345
  Completed: 1
  Failed: 0
  Total Elapsed Time: 4m 55s
  Average Job Time: 4m 55s
--------------------------------------------------------------------------------

Phase: REGIONS
  Status: completed
  Started: 2025-10-28T18:35:01.123456
  Ended: 2025-10-28T19:45:00.123456
  Total Jobs: 24
  Job IDs: 12346, 12347, 12348, ...
  Completed: 24
  Failed: 0
  Total Elapsed Time: 2h 15m 30s
  Average Job Time: 5m 38s
--------------------------------------------------------------------------------

Phase: CONCAT
  Status: completed
  Started: 2025-10-28T19:45:01.123456
  Ended: 2025-10-28T20:30:00.123456
  Total Jobs: 8
  Job IDs: 12400, 12401, ...
  Completed: 8
  Failed: 0
  Total Elapsed Time: 45m 20s
  Average Job Time: 5m 40s
--------------------------------------------------------------------------------

================================================================================
```

## Informações Capturadas do Slurm

Para cada job, o sistema captura:

- **JobID**: ID do job no Slurm
- **JobName**: Nome do script sbatch executado
- **State**: Status do job (COMPLETED, FAILED, RUNNING, etc.)
- **Start/End**: Timestamps de início e fim
- **Elapsed**: Tempo total de execução
- **CPUTime**: Tempo total de CPU usado
- **MaxRSS**: Uso máximo de memória
- **ExitCode**: Código de saída do job

## Análise de Desempenho

Com os dados coletados, você pode:

1. **Identificar gargalos**: Ver qual fase demora mais
2. **Otimizar recursos**: Analisar uso de memória e CPU
3. **Detectar falhas**: Identificar jobs que falharam
4. **Estimar tempo**: Prever quanto tempo levará processamentos futuros
5. **Comparar execuções**: Comparar diferentes configurações ou datasets

## Comandos Slurm Úteis

Além do tracking automático, você pode usar comandos Slurm diretamente:

```bash
# Ver status de um job específico
sacct -j JOB_ID --format=JobID,JobName,State,Start,End,Elapsed,MaxRSS

# Ver todos os jobs de hoje
sacct --starttime today --format=JobID,JobName,State,Start,End,Elapsed

# Ver jobs em execução
squeue -u $USER

# Cancelar um job
scancel JOB_ID
```

## Troubleshooting

### Arquivo de tracking não encontrado

Se você não vê o arquivo `execution_tracking.json`, certifique-se de que:
- O diretório de saída existe e tem permissões de escrita
- O script `hips-creator` foi executado com sucesso

### Informações do Slurm não aparecem

Se `slurm_info` está vazio nos dados:
- Verifique se o comando `sacct` está disponível: `which sacct`
- Certifique-se de que você tem permissão para consultar seus jobs
- Os jobs podem ainda estar em execução ou na fila

### Jobs não aparecem no sacct

O Slurm mantém histórico por um período limitado. Se os jobs são muito antigos, eles podem não aparecer mais no `sacct`.
