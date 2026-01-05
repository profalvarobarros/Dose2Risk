# Dose2Risk: A Computational Pipeline for Cancer Risk Estimation from Ionizing Radiation

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 

**Leia este documento em outros idiomas:** [Português (BR)](LEIAME.md)

---

## Overview

Dose2Risk is a scientific software tool that processes radiation dose data from HotSpot simulations to estimate cancer risk associated with ionizing radiation exposure. It implements the epidemiological models from the **BEIR V** and **BEIR VII** reports.

The system is designed for applications in radiation protection, nuclear emergency response, and risk analysis in radionuclide-exposed areas, providing automated and transparent results for researchers and professionals.

![Screenshot of Dose2Risk Web Interface](https://via.placeholder.com/700x400.png?text=Adicione+um+screenshot+da+interface+web+aqui) 
*Figure 1: The user-friendly web interface for uploading data and processing risks.*

## Features

- **Automated Data Extraction**: Seamlessly parses data from HotSpot output files.
- **Risk Calculation**: Computes cancer risk for various organs and scenarios using BEIR V and BEIR VII models.
- **Web Interface**: A modern, user-friendly web UI (built with Flask) for easy file uploads, parameter input, and result downloads.
- **Command-Line Interface**: A robust CLI for batch processing and integration into automated pipelines.
- **Customizable Parameters**: Allows users to specify age at exposure, age at assessment, and other relevant parameters.
- **Detailed Reporting**: Generates comprehensive CSV reports and detailed processing logs.
- **Internationalization (i18n)**: Supports multiple languages (English, Portuguese, Spanish, French).

## How to Cite

If you use this software in your research, please cite it as follows:

> [BARROS A.R., et.al], **Dose2Risk: A Computational Pipeline for Cancer Risk Estimation from Ionizing Radiation**, (2025), GitHub repository, [https://github.com/profalvarobarros/Dose2Risk](https://github.com/profalvarobarros/Dose2Risk)

*INSERIR REFERÊNCIA DO ARTIGO*

## Installation

To run this project, you need Python 3.8+ and the required libraries.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/profalvarobarros/Dose2Risk.git
    cd Dose2Risk
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    # Create and activate a virtual environment (optional but recommended)
    python -m venv .venv
    
    # On Windows
    .venv\Scripts\activate
    
    # On macOS/Linux
    source .venv/bin/activate

    # Install the required packages
    pip install -r requirements.txt
    ```

## Usage

You can use Dose2Risk through its web interface.

### Web Interface

The web interface is the easiest way to use the tool.

1.  **Start the web server:**
    ```bash
    python run.py
    ```

2.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:5000`.

3.  **Follow the workflow:**
    -   Upload one or more HotSpot `.txt` files.
    -   Enter the required parameters (e.g., age at exposure, current age).
    -   Click "Process" to run the pipeline.
    -   Download the generated CSV and LOG files directly from the interface.

## Project Structure

```
Programa_Python_AR/
├── dose2risk/             # Main application package
│   ├── api/               # Web API and Flask application
│   │   ├── routes.py      # Flask routes
│   │   ├── templates/     # HTML templates
│   │   └── static/        # Static assets
│   └── core/              # Core processing logic
│       ├── pipeline.py        # Orchestrator
│       ├── extractor.py       # Data extraction from HotSpot files
│       ├── transposer.py      # Data reshaping
│       └── risk_calculator.py # BEIR V/VII risk models
├── config/                # Configuration files
├── data/                  # Data directory
├── run.py                 # Application entry point
├── requirements.txt       # Project dependencies
└── README.md              # This file
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Scientific References

-   **BEIR VII (2006):** Health Risks from Exposure to Low Levels of Ionizing Radiation (National Academy of Sciences).
-   **BEIR V (1990):** Health Effects of Exposure to Low Levels of Ionizing Radiation.

---

**Developed for applications in Radiation Protection, Nuclear Emergencies, and Scientific Research.**
