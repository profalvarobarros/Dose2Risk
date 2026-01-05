# HotSpot BEIR V/VII - Estimativa de Risco de Câncer por Radiação

## Visão Geral
Este projeto realiza o processamento de dados de doses provenientes de simulações HotSpot, estimando o risco de câncer associado à exposição à radiação ionizante, utilizando os modelos epidemiológicos BEIR V e BEIR VII.

O sistema é focado em aplicações de radioproteção, emergências nucleares e análises de risco em áreas expostas a radionuclídeos, fornecendo resultados automatizados e transparentes para pesquisadores e profissionais da área.

## Estrutura do Projeto
```
Programa_Python/
├── dose2risk/             # Pacote principal da aplicação
│   ├── api/               # API Web e aplicação Flask
│   │   ├── routes.py      # Rotas do Flask
│   │   ├── templates/     # Templates HTML
│   │   └── static/        # Arquivos estáticos
│   └── core/              # Lógica principal de processamento
│       ├── pipeline.py        # Orquestrador
│       ├── extractor.py       # Extração de dados de arquivos HotSpot
│       ├── transposer.py      # Reorganização de dados
│       └── risk_calculator.py # Modelos de risco BEIR V/VII
├── config/                # Arquivos de configuração
├── data/                  # Diretório de dados
├── run.py                 # Ponto de entrada da aplicação
├── requirements.txt       # Dependências do projeto
└── LEIAME.md              # Este arquivo
```

## Funcionalidades
- **Extração automática** de dados de arquivos HotSpot.
- **Transposição e organização** dos dados para formato tabular.
- **Cálculo de risco de câncer** para diferentes órgãos e cenários, com base nos modelos BEIR V e BEIR VII.
- **Geração de relatórios** em CSV e logs detalhados do processamento.
- **Parâmetros personalizáveis**: idade de exposição, idade de avaliação, modelo de risco, etc.
- **Interface Web**: Upload de arquivos, configuração de parâmetros e download de resultados.

## Modelos Epidemiológicos
- **BEIR VII**: Utiliza parâmetros beta, gamma e eta para cada órgão/sexo, ajustando o risco conforme idade de exposição e avaliação. Fórmula principal:
  
  `Risco Excedente = beta × ERR(e,a) × dose_Sv`
  
  Onde `ERR(e,a) = exp(gamma × e*) × (idade_avaliacao / 60)^eta`

- **BEIR V**: Modelo alternativo para doses muito elevadas, utilizando coeficientes alpha2, alpha3 e modificadores baseados no tempo desde a exposição.

## Como Executar

O projeto utiliza uma interface web para facilitar o uso.

1. **Pré-requisitos:**
   - Python 3.8+
   - Instalar dependências (recomendado usar ambiente virtual):
     ```bash
     python -m venv .venv
     
     # Windows
     .\.venv\Scripts\Activate
     
     # Linux/Mac
     source .venv/bin/activate
     
     pip install -r requirements.txt
     ```

2. **Executando o servidor web:**
   - No terminal, acesse a pasta do projeto e execute:
     ```bash
     python run.py
     ```
   - O sistema estará disponível em `http://localhost:5000` (ou `http://127.0.0.1:5000`).

3. **Fluxo de uso:**
   - **Upload:** Faça upload de um ou mais arquivos HotSpot `.txt` pela página inicial.
   - **Parâmetros:** Informe a idade na exposição e a idade atual no formulário exibido após o upload.
   - **Processamento:** O sistema executa o pipeline e gera os arquivos de saída (CSV e LOG) para download.
   - **Reprocessamento:** É possível reprocessar os mesmos arquivos com outros parâmetros de idade, sem necessidade de novo upload.
   - **Download:** Baixe os arquivos de saída gerados diretamente pela interface.

4. **Isolamento de execuções:**
   - Cada sessão de upload cria uma pasta exclusiva para os arquivos enviados e para os resultados, permitindo execuções organizadas.
## Parâmetros de Entrada
- **Idade de exposição:** Idade da pessoa no momento da exposição à radiação.
- **Idade de avaliação:** Idade da pessoa na avaliação do risco.
- **Modelo:** O sistema seleciona automaticamente entre BEIR V e VII conforme a dose, mas pode ser forçado via parâmetro.

## Referências Científicas
- **BEIR VII (2006):** Health Risks from Exposure to Low Levels of Ionizing Radiation (National Academy of Sciences).
- **BEIR V (1990):** Health Effects of Exposure to Low Levels of Ionizing Radiation.

Consulte os PDFs em `dados_referencia/` para detalhes sobre fórmulas, parâmetros e tabelas utilizadas.

## Observações Importantes
- Os resultados dependem da qualidade dos dados de entrada e da correta parametrização.
- O sistema é voltado para fins acadêmicos e de pesquisa. Para uso regulatório, consulte especialistas e normas vigentes.
- Para dúvidas sobre os parâmetros dos modelos, consulte diretamente as tabelas do BEIR VII/V.

## Suporte
Para dúvidas, sugestões ou colaboração, entre em contato com o responsável pelo projeto ou abra uma issue neste repositório.

---

**Desenvolvido para aplicações em Radioproteção, Emergências Nucleares e Pesquisa Científica.**
