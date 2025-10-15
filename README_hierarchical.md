# HiPS Concatenação Hierárquica

Script para processar imagens particionadas usando HipsGen com concatenação hierárquica em pares, gerando um RGB final.

## Fluxo de Processamento

1. **Fase 1**: Executa HipsGen para cada imagem particionada em paralelo
2. **Fase 2**: Concatena as saídas em pares hierarquicamente até sobrar uma imagem por banda
3. **Fase 3**: Consolida as 3 bandas finais em um RGB

## Uso

```bash
cd /home/singulani/projects/hipsimage_gen

# Exemplo básico
python src/hips_hierarchical_concat.py param_hierarchical.yaml "data/*/*.fits"

# Com opções específicas  
python src/hips_hierarchical_concat.py param_hierarchical.yaml "data/*/*.parquet" \
    --ra-col ra_deg --dec-col dec_deg \
    --id-pattern healpix \
    --max-partitions 8

# Modo de teste (não submete jobs)
python src/hips_hierarchical_concat.py param_hierarchical.yaml "data/*/*.fits" --dry-run
```

## Parâmetros

- `config_file`: Arquivo YAML de configuração
- `input_pattern`: Padrão glob para encontrar arquivos particionados
- `--ra-col`: Nome da coluna RA (padrão: 'ra')
- `--dec-col`: Nome da coluna DEC (padrão: 'dec') 
- `--id-pattern`: Padrão para extrair ID da região ('auto', 'healpix', 'custom')
- `--max-partitions`: Máximo de partições a processar
- `--dry-run`: Apenas simula, não submete jobs

## Configuração

Edite `param_hierarchical.yaml` com:

```yaml
aladin_cmd: /path/to/Aladin.jar
cwd: /trabalho/hips_hierarquico  
max_mem: 16  # GB de RAM

hipsgen:
  creator_did: CDS/P/SEU/SURVEY
  obs_title: 'Nome do Survey'
  # ... outras configurações
```

## Exemplo de Concatenação

Para 8 partições, o processo seria:

```
Nível 0: [P1] [P2] [P3] [P4] [P5] [P6] [P7] [P8]
         ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓
Nível 1: [P1+P2] [P3+P4] [P5+P6] [P7+P8] 
         ↓       ↓       ↓       ↓
Nível 2: [P1234]   [P5678]
         ↓         ↓  
Nível 3: [P12345678] ← Resultado final por banda
```

## Arquivos Criados

- `partition_{id}.config`: Configuração para cada partição
- `concat_level{N}_{pair}.config`: Configuração para concatenações
- `rgb_final.config`: Configuração final RGB
- Diretórios de saída organizados por nível

## Dependencies

O script gerencia automaticamente as dependências entre jobs no Slurm:
- Jobs de concatenação aguardam partições correspondentes
- RGB final aguarda todas as concatenações

## Scripts SBATCH Necessários

- `color.sbatch`: Para processamento inicial das partições
- `concat.sbatch`: Para concatenação hierárquica  
- `rgb.sbatch`: Para consolidação RGB final