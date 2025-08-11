from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
from scipy.stats import entropy
from scipy.spatial.distance import pdist, squareform
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.colors as mcolors
import io
import base64
import google.generativeai as genai
import os
from io import BytesIO 
from Bio import Entrez 
from skbio.stats.ordination import pcoa 
from skbio import DistanceMatrix 
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

# Flask App Setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Variáveis alvo que o modelo irá predizer
TARGET_VARIABLES = ["age_months", "body_weight"] 

#CHAVES APIs
DEV_GEMINI_API_KEY= "INSERIR A CHAVE ENVIADA NO EMAIL (GEMINI)"
DEV_NCBI_API_KEY= "INSERIR A CHAVE ENVIADA NO EMAIL (NCBI)"
NCBI_EMAIL="INSERIR O ENDEREÇO DE EMAIL ENVIADO"


#CORES DA IDENTIDADE VISUAL
PRIMARY_TEXT_COLOR = "#1A2C4B"
ACCENT_COLOR = "#E91E63"
ACCENT_LIGHT_COLOR = "#FCE4EC" 

_gemini_api_configured_successfully = False
_ncbi_api_configured_successfully = False 


# Cria o diretório de uploads se ele não existir
if not os.path.exists(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'])):
    os.makedirs(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER']))

#Configura as APIs
def configure_apis_global():
    global _gemini_api_configured_successfully, _ncbi_api_configured_successfully
    if DEV_GEMINI_API_KEY and DEV_GEMINI_API_KEY != "chave":
        try:
            genai.configure(api_key=DEV_GEMINI_API_KEY)
            _gemini_api_configured_successfully = True
        except Exception as e:
            print(f"ERRO CRÍTICO: Falha ao configurar a API do Gemini: {e}")
    if NCBI_EMAIL and DEV_NCBI_API_KEY and DEV_NCBI_API_KEY != "chave_ncbi":
        Entrez.email = NCBI_EMAIL
        Entrez.api_key = DEV_NCBI_API_KEY
        _ncbi_api_configured_successfully = True

#Carregamento dos arquivos (documentos alvo e referencia fornecidos)
def load_data_from_memory(file_storage):
    try:
        file_content = file_storage.read()
        file_stream = BytesIO(file_content)
        filename = file_storage.filename
        df = None
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(file_stream, sep=None, engine='python')
            except Exception:
                file_stream.seek(0)
                df = pd.read_csv(file_stream, delimiter=';')
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_stream)
        
        if df is None or df.empty:
            raise ValueError("Arquivo vazio ou formato não suportado/lido.")
        return df, None
    except Exception as e:
        return None, str(e)

#Cálculo da alfa diversidade (métrica que avalia riqueza e diversidade intraindividual da microbiota)
def calculate_alpha_diversity(microbiota_data):
    microbiota_data = microbiota_data.fillna(0).astype(float)
    proportions = microbiota_data.apply(lambda x: x / x.sum() if x.sum() > 0 else x, axis=1)
    proportions[proportions == 0] = np.finfo(float).eps 
    alpha_diversity = entropy(proportions, base=np.e, axis=1)
    return pd.Series(alpha_diversity, index=microbiota_data.index)

#Consulta no pubmed com base nas 3 espécies mais abundantes (utilizada para propor um laudo cientifico e individualizado)
def generate_pubmed_query_for_bacteria(top_3_bacteria):
    if not top_3_bacteria or not _gemini_api_configured_successfully: return ""
    
    bacteria_names_clean = [name.replace("s__", "").replace("_", " ") for name in top_3_bacteria]
    
    bact_queries = []
    for bact_name in bacteria_names_clean:
        bact_queries.append(f'("{bact_name}"[MeSH Terms] OR "{bact_name}"[All Fields])')
    
    main_bact_query = " OR ".join(bact_queries)

    prompt = (
        f"Com base na seguinte lista de bactérias: {', '.join(bacteria_names_clean)}, "
        f"gere uma consulta PubMed. A consulta principal para as bactérias, que já foi pré-formatada, é: `({main_bact_query})`. "
        f"Sua tarefa é combinar esta consulta principal com termos gerais sobre microbiota intestinal humana usando o operador AND. "
        f"A saída deve ser APENAS a string da consulta final."
    )
    try:
        model = genai.GenerativeModel()
        response = model.generate_content(prompt)
        return response.text.strip().strip('`" ')
    except Exception as e:
        print(f"DEBUG: Erro ao gerar consulta PubMed com Gemini: {e}")
        return ""

def search_pubmed_and_get_summaries(query, max_articles=5):
    if not query or not _ncbi_api_configured_successfully: return []
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_articles, retmode="xml")
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record.get("IdList", [])
        print(f"DEBUG: Encontrados {len(id_list)} artigos no PubMed para a consulta.")

        if not id_list: return []
        
        handle = Entrez.efetch(db="pubmed", id=id_list, rettype="abstract", retmode="xml")
        articles = Entrez.read(handle)
        handle.close()
        
        summaries = []
        for article in articles.get("PubmedArticle", []):
            title = article.get("MedlineCitation", {}).get("Article", {}).get("ArticleTitle", "")
            abstract_parts = article.get("MedlineCitation", {}).get("Article", {}).get("Abstract", {}).get("AbstractText", [])
            abstract = " ".join(abstract_parts) if isinstance(abstract_parts, list) else str(abstract_parts)
            if title and abstract:
                summaries.append(f"Título: {title}\nResumo: {abstract}\n")
        return summaries
    except Exception as e:
        print(f"DEBUG: Erro na busca PubMed: {e}")
        return []

def summarize_articles_or_knowledge_with_gemini(article_texts, top_3_bacteria_names):
    if not _gemini_api_configured_successfully: return "Insight da IA indisponível."
    
    clean_names = ', '.join([name.replace("s__", "").replace("_", " ") for name in top_3_bacteria_names])
    model = genai.GenerativeModel()
    prompt_text = ""

    if article_texts:
        print("DEBUG: Resumindo com base nos artigos encontrados no PubMed.")
        combined_text = "\n\n---\n\n".join(article_texts)
        prompt_text = (
            f"Você é um assistente de análise de microbioma. Com base nos resumos de artigos científicos fornecidos, escreva um insight conciso sobre o que significa ter {clean_names} como as bactérias mais abundantes em uma amostra. "
            f"Aborde a funcionalidade, a importância para a saúde e o potencial risco (se aplicável)."
        )
    elif top_3_bacteria_names:
        print("DEBUG: Nenhum artigo encontrado. Resumindo com base no conhecimento geral da IA.")
        prompt_text = (
            f"Você é um assistente de análise de microbioma. Baseado no conhecimento científico geral, escreva um insight conciso sobre o que significa ter {clean_names} como as bactérias mais abundantes em uma amostra. "
            f"Aborde a funcionalidade (o que fazem), a importância para a saúde (se são benéficas) e o potencial perigo (se podem ser patógenos oportunistas ou associadas a problemas quando em excesso)."
        )
    else:
        return "Não foi possível gerar insight (sem bactérias para analisar)."
    
    try:
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        return f"Erro ao gerar insight da IA: {e}"

#Exporta os resultados principais dos arquivos de referência e arquivos alvo (idade e peso predito, índice de shannon, MAZ para serem lidos posteriormente)
def save_results_to_json(data):
    upload_folder = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_folder): os.makedirs(upload_folder)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(upload_folder, f"analysis_results_{timestamp}.json")
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Resultados salvos com sucesso em: {filepath}")
    except Exception as e:
        print(f"ERRO: Falha ao salvar o arquivo JSON: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    #Treinamento dos modelos. É importante utilizar os modelos oferecidos como exemplo, considerando que o tratamento previo dos arquivos de referencia/alvo
    #não foram considerados aqui para otimizar o script (a tabela de referencia e de alvos DEVEM ter as mesmas colunas)
    if 'reference_db' not in request.files: return render_template('results.html', error="Por favor, envie o arquivo da Base de Dados de Referência.")
    target_files = request.files.getlist('target_sample')
    if not target_files or target_files[0].filename == '': return render_template('results.html', error="Por favor, envie pelo menos um arquivo de Amostra Alvo.")
    reference_file = request.files['reference_db']
    reference_db, error = load_data_from_memory(reference_file)
    if error: return render_template('results.html', error=f"Erro ao carregar a base de referência: {error}")
    species_columns = [col for col in reference_db.columns if col not in TARGET_VARIABLES and col != 'microbial_age']
    if not species_columns: return render_template('results.html', error="Nenhuma coluna de espécie identificada na base de referência.")
    for var in TARGET_VARIABLES + ["age_months"]:
        if var not in reference_db.columns: return render_template('results.html', error=f"Coluna necessária '{var}' não encontrada na base de referência.")
    X_ref = reference_db[species_columns]
    y_ref = reference_db[TARGET_VARIABLES]
    if len(X_ref) < 2: return render_template('results.html', error="Base de referência precisa de ao menos 2 amostras.")
    models, performance_metrics = {}, {}
    for target in TARGET_VARIABLES:
        y_target = y_ref[target]
        test_size = 0.2 if len(X_ref) >= 5 else (1 / len(X_ref))
        X_train, X_test, y_train, y_test = train_test_split(X_ref, y_target, test_size=test_size, random_state=42)
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        models[target] = model
        if len(y_test) > 0:
            y_pred_test = model.predict(X_test)
            r2 = r2_score(y_test, y_pred_test) if len(y_test.unique()) > 1 else 0.0
            mae = mean_absolute_error(y_test, y_pred_test)
            performance_metrics[target] = {"R2": r2, "MAE": mae}
    microbial_age_model = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_ref, reference_db["age_months"])
    predicted_microbial_ages_ref = microbial_age_model.predict(X_ref)
    mediana_microbiana_ref = np.median(predicted_microbial_ages_ref)
    desvio_padrao_microbiano_ref = np.std(predicted_microbial_ages_ref)
    ref_alpha_diversities = calculate_alpha_diversity(X_ref)
    alpha_diversity_ref_mean = ref_alpha_diversities.mean()
    alpha_diversity_ref_std = ref_alpha_diversities.std()

    all_individual_results = []
    for target_file in target_files:
        individual_result = {"filename": target_file.filename}
        target_sample, error = load_data_from_memory(target_file)
        if error or (target_sample is not None and len(target_sample) != 1):
            individual_result["error"] = error or "Arquivo alvo deve conter apenas uma linha."
            all_individual_results.append(individual_result)
            continue
        
        target_sample_aligned = target_sample.reindex(columns=species_columns, fill_value=0)
        
        predictions = {target: model.predict(target_sample_aligned)[0] for target, model in models.items()}
        comparison_metrics = {}
        for target in TARGET_VARIABLES:
            comparison_metrics[target] = { "real": target_sample.get(target, [None])[0], "predicted": predictions.get(target) }
        individual_result["comparison_metrics"] = comparison_metrics

        predicted_microbial_age_target = microbial_age_model.predict(target_sample_aligned)[0]
        if desvio_padrao_microbiano_ref > 0:
            individual_result["maz_value"] = (predicted_microbial_age_target - mediana_microbiana_ref) / desvio_padrao_microbiano_ref
        else:
            individual_result["maz_value"] = 0.0
        
        individual_result["alpha_diversity_value"] = calculate_alpha_diversity(target_sample_aligned).iloc[0]

        target_abund = target_sample_aligned.iloc[0].nlargest(10)
        top_3_bacteria = target_abund.head(3).index.tolist()
        
        #Grafico de abundancia das espécies
        fig_bar = Figure(figsize=(10, 6), dpi=150)
        fig_bar.patch.set_alpha(0.0)
        ax_bar = fig_bar.add_subplot(111)
        ax_bar.set_facecolor('#FFFFFF00')
        bar_colors = mcolors.LinearSegmentedColormap.from_list("grad", [ACCENT_LIGHT_COLOR, ACCENT_COLOR])
        normalized_values = plt.Normalize(target_abund.min(), target_abund.max())

        ax_bar.bar([l.replace('_', ' ').replace(' ', '\n') for l in target_abund.index], 
                   target_abund.values, 
                   color=bar_colors(normalized_values(target_abund.values)),
                   edgecolor=PRIMARY_TEXT_COLOR,
                   linewidth=0.5)

        ax_bar.set_title(f'Top 10 Bactérias - {target_file.filename}', color=PRIMARY_TEXT_COLOR, fontweight='bold', fontsize=14)
        ax_bar.set_ylabel('Abundância Relativa', color=PRIMARY_TEXT_COLOR, fontsize=12)
        ax_bar.tick_params(axis='x', colors=PRIMARY_TEXT_COLOR, rotation=45)
        ax_bar.tick_params(axis='y', colors=PRIMARY_TEXT_COLOR)
        ax_bar.grid(axis='y', linestyle='--', color='grey', alpha=0.5)
        ax_bar.spines['top'].set_visible(False)
        ax_bar.spines['right'].set_visible(False)
        ax_bar.spines['bottom'].set_color('grey')
        ax_bar.spines['left'].set_color('grey')

        fig_bar.tight_layout()
        buf_bar = io.BytesIO()
        fig_bar.savefig(buf_bar, format='png', bbox_inches='tight', transparent=True)
        plt.close(fig_bar)
        individual_result["top_bacteria_plot_url"] = base64.b64encode(buf_bar.getvalue()).decode('utf-8')
        
        #Print do resumo gerado por IA.
        print(f"\n--- Gerando Insight para {target_file.filename} ---")
        query = generate_pubmed_query_for_bacteria(top_3_bacteria)
        if query: print(f"DEBUG: Consulta PubMed gerada: {query}")
        summaries = search_pubmed_and_get_summaries(query) if query else []
        individual_result["gemini_insight_text"] = summarize_articles_or_knowledge_with_gemini(summaries, top_3_bacteria)
        print("--- Fim do Insight ---")

        #Gráfico PCoA (beta - diversidade), considerando a diversidade da microbiota entre os indivíduos
        pcoa_plot_url = None
        try:
            combined_data_for_beta = pd.concat([X_ref, target_sample_aligned], ignore_index=True).fillna(0).astype(float)
            if len(combined_data_for_beta) > 2:
                dm = DistanceMatrix(squareform(pdist(combined_data_for_beta, metric='braycurtis')))
                pcoa_results = pcoa(dm)
                coords = pcoa_results.samples[['PC1', 'PC2']].values
                if np.isnan(coords).any(): raise ValueError("Coordenadas PCoA com valores NaN.")

                fig = Figure(figsize=(8, 8), dpi=150)
                fig.patch.set_alpha(0.0) 
                ax = fig.add_subplot(111)
                ax.set_facecolor('#FFFFFF00')

                ages_ref = reference_db['age_months'].values
                age_target_predicted = individual_result['comparison_metrics']['age_months']['predicted']
                all_ages_for_plot = np.append(ages_ref, age_target_predicted)
                
                pcoa_cmap = mcolors.LinearSegmentedColormap.from_list("pcoa_grad", ["#DDDDDD", ACCENT_LIGHT_COLOR, ACCENT_COLOR])

                scatter = ax.scatter(coords[:, 0], coords[:, 1], c=all_ages_for_plot, cmap=pcoa_cmap, alpha=0.8, s=60, edgecolor='#FFFFFF', linewidth=0.5)
                
                ax.scatter(coords[-1, 0], coords[-1, 1], facecolors='none', edgecolors=PRIMARY_TEXT_COLOR, s=200, linewidth=2, label='Indivíduo Alvo')
                ax.set_title('Análise de Similaridade da Microbiota (PCoA)', color=PRIMARY_TEXT_COLOR, fontweight='bold', fontsize=14)
                ax.set_xlabel('Componente Principal 1', color=PRIMARY_TEXT_COLOR, fontsize=12)
                ax.set_ylabel('Componente Principal 2', color=PRIMARY_TEXT_COLOR, fontsize=12)
                ax.tick_params(axis='x', colors=PRIMARY_TEXT_COLOR)
                ax.tick_params(axis='y', colors=PRIMARY_TEXT_COLOR)
                ax.grid(True, linestyle='--', color='grey', alpha=0.5)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['bottom'].set_color('grey')
                ax.spines['left'].set_color('grey')

                legend = ax.legend()
                for text in legend.get_texts():
                    text.set_color(PRIMARY_TEXT_COLOR)
                
                cbar = fig.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04)
                cbar.set_label('Idade em Meses (Real ou Predita)', color=PRIMARY_TEXT_COLOR, fontsize=12)
                cbar.ax.yaxis.set_tick_params(color=PRIMARY_TEXT_COLOR)
                plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color=PRIMARY_TEXT_COLOR)

                fig.tight_layout()
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
                plt.close(fig)
                pcoa_plot_url = base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"ERRO AO GERAR GRÁFICO PCOA para {target_file.filename}: {e}")
        
        individual_result["pcoa_plot_url"] = pcoa_plot_url
        all_individual_results.append(individual_result)
    
    #  montagem do JSON e renderização
    final_results = {
        "analysis_timestamp": datetime.now().isoformat(),
        "reference_file": reference_file.filename,
        "model_performance": performance_metrics,
        "reference_alpha_diversity": {"mean": alpha_diversity_ref_mean, "std": alpha_diversity_ref_std},
        "reference_maz_mean": 0.0,
        "individual_analyses": all_individual_results
    }
    save_results_to_json(final_results)
    return render_template('results.html', results=final_results)

if __name__ == '__main__':
    with app.app_context():
        configure_apis_global()
    app.run(debug=True)