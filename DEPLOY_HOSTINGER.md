# Guia de Implantação: Dose2Risk na Hostinger

Este guia descreve os passos para implantar o projeto **Dose2Risk** em um ambiente de hospedagem da Hostinger. As instruções cobrem tanto ambientes de **Hospedagem Compartilhada/Cloud** (usando o recurso Python App) quanto **VPS** (instalação manual).

## 1. Pré-requisitos

*   Uma conta na Hostinger com um plano que suporte Python (Hospedagem Cloud ou VPS).
*   Acesso SSH ao servidor (recomendado) ou acesso via gerenciador de arquivos.
*   Os arquivos do projeto (sem as pastas `docs` e `Tese`).

---

## 2. Opção A: Hospedagem Compartilhada / Cloud (Python App)

A Hostinger oferece uma interface "Setup Python App" no hPanel.

### Passo 1: Preparar os arquivos
1.  No seu computador local, certifique-se de que o arquivo `requirements.txt` está atualizado.
2.  Compacte (zip) o conteúdo da pasta `Programa_Python_AR` (excluindo `docs`, `Tese`, `.venv`, `.git`).

### Passo 2: Criar a Aplicação Python no hPanel
1.  Acesse o **hPanel** e vá para a seção **Site** ou **Avançado**.
2.  Clique em **Setup Python App**.
3.  Clique em **Create New App**.
4.  **Python Version:** Selecione a versão recomendada (ex: 3.9 ou superior).
5.  **App Directory:** Defina a pasta onde o app ficará (ex: `dose2risk`).
6.  **App Domain/URI:** Escolha o domínio ou subdomínio.
7.  Clique em **Create**.

### Passo 3: Upload e Instalação
1.  Use o **Gerenciador de Arquivos** ou **FTP** para enviar os arquivos do projeto para a pasta criada (ex: `dose2risk`).
2.  Certifique-se de que o arquivo principal seja identificado. Se o seu arquivo principal é `run.py`, você pode precisar criar um arquivo `passenger_wsgi.py` (padrão usado pela Hostinger/cPanel) que importa sua aplicação Flask.

    **Exemplo de `passenger_wsgi.py`:**
    ```python
    import sys, os
    
    # Adiciona o diretório atual ao path
    sys.path.append(os.getcwd())
    
    # Importa a aplicação Flask
    # Supondo que em dose2risk/api/__init__.py você tenha 'create_app'
    # Ou se você usa run.py e ele expõe 'app'
    
    from dose2risk.core.pipeline import create_app # Ajuste conforme sua estrutura real de importação
    application = create_app()
    ```

3.  Volte para a tela **Setup Python App**.
4.  Em "Configuration files", adicione `requirements.txt` se não estiver lá.
5.  Clique em **Run Pip Install** para instalar as dependências.
6.  Clique em **Restart** para iniciar a aplicação.

---

## 3. Opção B: Servidor VPS (Ubuntu/Debian)

Este é o método mais robusto e recomendado para controle total.

### Passo 1: Acesso e Atualização
Acesse seu VPS via SSH:
```bash
ssh root@seu_ip
apt update && apt upgrade -y
```

### Passo 2: Instalar Dependências do Sistema
```bash
apt install python3-pip python3-venv nginx git -y
```

### Passo 3: Clonar/Enviar o Projeto
```bash
cd /var/www
git clone https://github.com/profalvarobarros/Dose2Risk.git
cd Dose2Risk
```
*Alternativamente, use SCP/SFTP para enviar os arquivos se o repositório for privado ou local.*

### Passo 4: Configurar Ambiente Virtual
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### Passo 5: Testar com Gunicorn
```bash
# Ajuste o caminho de importação conforme sua aplicação
gunicorn --bind 0.0.0.0:8000 "dose2risk.api:create_app()" 
```
Se funcionar, pare com `Ctrl+C`.

### Passo 6: Criar Serviço Systemd
Crie um arquivo para manter o app rodando: `/etc/systemd/system/dose2risk.service`

```ini
[Unit]
Description=Gunicorn instance directly serving Dose2Risk
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/dose2risk
Environment="PATH=/var/www/dose2risk/.venv/bin"
ExecStart=/var/www/dose2risk/.venv/bin/gunicorn --workers 3 --bind unix:dose2risk.sock -m 007 "dose2risk.api:create_app()"

[Install]
WantedBy=multi-user.target
```

Ative o serviço:
```bash
systemctl start dose2risk
systemctl enable dose2risk
```

### Passo 7: Configurar Nginx (Reverse Proxy)
Crie o arquivo de configuração: `/etc/nginx/sites-available/dose2risk`

```nginx
server {
    listen 80;
    server_name seu_dominio.com www.seu_dominio.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/dose2risk/dose2risk.sock;
    }
}
```

Ative o site e reinicie o Nginx:
```bash
ln -s /etc/nginx/sites-available/dose2risk /etc/nginx/sites-enabled
nginx -t
systemctl restart nginx
```

---

## 4. Notas Importantes

*   **Banco de Dados:** Este projeto usa arquivos locais ou SQLite? Se for SQLite, certifique-se de que a pasta onde o banco reside tem permissões de escrita para o usuário que roda a aplicação.
*   **Variáveis de Ambiente:** Crie um arquivo `.env` no servidor com suas chaves secretas (SECRET_KEY do Flask, etc). **Não comite o .env!**
*   **Logs:** Verifique os logs do Gunicorn (`journalctl -u dose2risk`) ou do Nginx (`/var/log/nginx/error.log`) em caso de erro.
