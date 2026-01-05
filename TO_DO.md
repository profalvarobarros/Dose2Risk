# TO DO - Adequação Normativa Ministério da Defesa

Este arquivo rastreia as tarefas necessárias para alinhar o projeto DoseToRisk à Doutrina Militar Brasileira.

## 1. Documentação e Glossário
- [ ] **Mapeamento de Termos:** Criar tabela DE-PARA entre termos do HotSpot/BEIR e o Glossário das Forças Armadas (MD35-G-01).
- [ ] **Atualizar Docstrings:** Refatorar comentários do `risk_calculator.py` para incluir referências às normas MD42 e MD40.
- [ ] **README Doutrinário:** Adicionar seção no README.md explicando o enquadramento do software como ferramenta de Apoio de Saúde (MD42-M-04).

## 2. Funcionalidades (Roadmap)
- [ ] **Detector de Dose Aguda:** Implementar *flag* no pipeline que alerta explicitamente se a dose ultrapassa limiares de efeitos deterministícos (> 700 mSv).
- [ ] **Relatório de Conformidade:** Adicionar rodapé nos relatórios HTML citando a integridade do dado (Hash SHA-256) como conformidade com MD40.

## 3. Validação
- [ ] **Testes de Regressão:** Garantir que ajustes de terminologia não quebrem a lógica de *parsing* do CSV.
- [ ] **Revisão por Pares:** Validar o plano de implementação com orientador ou especialista em Doutrina.
