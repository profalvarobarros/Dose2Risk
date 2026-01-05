# Garantia de Qualidade (QA) - Dose2Risk

Esta pasta contém a suíte de testes automatizados para verificação e validação do software.

## Estrutura
*   **unit/**: Testes de unidade focados em validar a lógica matemática interna da classe `CalculadoraRisco` (Caixa Branca). Valida se os algoritmos do BEIR V e BEIR VII comportam-se conforme descrito nos relatórios científicos.
*   **integration/**: Testes de integração que simulam o fluxo completo de dados (Arquivos -> Pipeline -> CSV), garantindo que os componentes interagem corretamente.

## Como Executar
Pré-requisito: `pip install pytest pytest-cov`

### Execução Simples
```bash
pytest
```

### Execução com Relatório de Cobertura
```bash
pytest --cov=dose2risk tests/
```
O objetivo é manter cobertura > 80% nos módulos críticos.

## Critérios de Aceite
Todos os testes devem passar antes de qualquer deploy em produção ("Mission Critical").
