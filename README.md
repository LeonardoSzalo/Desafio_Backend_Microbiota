🧬 Plataforma de Análise Preditiva de Microbiota
<div align="center">
<img src="https://raw.githubusercontent.com/LeonardoSzalo/Desafio_Backend_Microbiota/main/static/inside_logo.png" alt="Logo Inside Diagnósticos" width="250px">
</div>

<p align="center">
<strong>Uma aplicação web completa para análise de dados de microbioma, utilizando Machine Learning para predições de idade e peso, e integração com a API da Google (Gemini) para geração de insights científicos.</strong>
</p>

<p align="center">
<a href="https://github.com/LeonardoSzalo/Desafio_Backend_Microbiota"><img src="https://img.shields.io/badge/Repositório-GitHub-blueviolet" alt="Repositório"></a>
<img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Versão do Python">
<img src="https://img.shields.io/badge/Framework-Flask-black.svg" alt="Flask">
</p>

🚀 Como Executar o Projeto: Guia Rápido
Este guia detalha o passo a passo para clonar, configurar e executar a plataforma em seu ambiente local.

Passo 1: Clonar o Repositório
Primeiro, clone este repositório para a sua máquina local usando o seguinte comando no terminal:

git clone https://github.com/LeonardoSzalo/Desafio_Backend_Microbiota.git
cd Desafio_Backend_Microbiota

Passo 2: Configurar o Ambiente Virtual
É uma forte recomendação usar um ambiente virtual para isolar as dependências do projeto e evitar conflitos.

# Criar o ambiente virtual
python -m venv venv

# Ativar o ambiente no Windows
venv\Scripts\activate

# Ativar o ambiente no macOS/Linux
source venv/bin/activate

Com o ambiente ativado, seu terminal deve exibir (venv) no início da linha.

Passo 3: Instalar as Dependências
Todas as bibliotecas necessárias estão listadas no arquivo requirements.txt. Instale todas de uma só vez com o comando:

pip install -r requirements.txt

Passo 4: Configurar as Chaves de API
Para que a geração de insights com IA funcione, você precisa configurar suas chaves de API.

Crie uma cópia do arquivo .env.example e renomeie-a para .env.

Abra o novo arquivo .env e insira suas chaves de API do Google Gemini e do NCBI.

DEV_GEMINI_API_KEY="SUA_CHAVE_REAL_DO_GEMINI_AQUI"
DEV_NCBI_API_KEY="SUA_CHAVE_REAL_DO_NCBI_AQUI"
NCBI_EMAIL="SEU_EMAIL_CADASTRADO_NO_NCBI"

⚠️ Segurança: Suas chaves estão seguras. O arquivo .env está no .gitignore e nunca será enviado para o GitHub.

Passo 5: Executar a Aplicação
Com tudo configurado, inicie o servidor Flask:

flask run
# Ou, alternativamente:
python app.py

Abra seu navegador e acesse http://127.0.0.1:5000.

Passo 6: Utilizar a Plataforma
Na página inicial, faça o upload dos arquivos de exemplo para teste.

Base de Referência: Use o arquivo referencia.csv da pasta arquivos_referencia_e_alvo.

Amostra(s) Alvo: Use um ou mais arquivos alvo_*.xlsx da mesma pasta.

Clique em "Analisar Amostras".

Aguarde o processamento. O laudo completo será exibido na tela.

📁 Armazenamento e Geração de Laudos
Laudos em Formato JSON
Ao final de cada análise, a aplicação cria automaticamente a pasta uploads/ (se ainda não existir) e salva um arquivo .json contendo todos os dados brutos, predições e métricas geradas. Este arquivo serve como um registro permanente da análise.

Revisando Laudos Anteriores (sem reprocessar)
Se você deseja apenas visualizar um laudo que já foi gerado, não é necessário rodar a análise novamente. Utilize o script gerador_html.py.

Encontre o arquivo .json da análise desejada dentro da pasta uploads/.

Execute o seguinte comando no terminal, substituindo o nome do arquivo pelo seu:

python gerador_html.py "uploads/analysis_results_20250811_144205.json"

Um novo arquivo, laudo_visual.html, será criado na pasta principal do projeto. Abra-o em qualquer navegador para ver o relatório completo.

✨ Funcionalidades e Tecnologias
Interface Web Intuitiva: Upload de arquivos de referência e amostras-alvo diretamente pelo navegador.

Modelos Preditivos: Treinamento de modelos de Machine Learning (RandomForestRegressor) em tempo real para predizer idade e peso.

Métricas de Ecologia: Cálculo automático de diversidade Alfa (Shannon) e Beta (PCoA).

Visualização de Dados: Geração dinâmica de gráficos com Matplotlib.

Insights com IA: Integração com a API do Google Gemini para gerar resumos científicos.

Back-end: Python, Flask

Análise de Dados: Pandas, NumPy, Scikit-learn, SciPy, Scikit-bio, Biopython

Templating: Jinja2
