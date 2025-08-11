import json
import argparse
from jinja2 import Environment, FileSystemLoader
import os

def gerar_html(json_filepath, template_name='results.html', output_filename='laudo_visual.html'):
    """
    Gera um arquivo HTML a partir de um JSON de resultados e um template Jinja2.
    """
    print(f"Lendo o arquivo de resultados: {json_filepath}")
    
    # Carrega os dados do arquivo JSON
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo de entrada não encontrado em '{json_filepath}'")
        return
    except json.JSONDecodeError:
        print(f"Erro: O arquivo '{json_filepath}' não contém um JSON válido.")
        return

    print("Carregando o template HTML...")
    
    # Configura o ambiente do Jinja2 para encontrar o template na pasta 'templates'
    env = Environment(loader=FileSystemLoader('templates/'))
    template = env.get_template(template_name)

    print("Renderizando o HTML com os dados do JSON...")
    
    # --- MUDANÇA AQUI ---
    # Renderiza o template, passando os dados e a "bandeira" de modo independente
    html_content = template.render(results=results_data, standalone_mode=True)

    # Salva o conteúdo renderizado em um novo arquivo HTML
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("\n" + "="*50)
        print(f"SUCESSO! O relatório foi gerado em '{os.path.abspath(output_filename)}'")
        print("Abra este arquivo em qualquer navegador para visualizar o laudo completo.")
        print("="*50)
    except Exception as e:
        print(f"Erro ao salvar o arquivo HTML: {e}")


def main():
    """Função principal para rodar o script."""
    parser = argparse.ArgumentParser(description="Gerador de Laudos HTML a partir de arquivos JSON.")
    parser.add_argument("json_filepath", type=str, help="Caminho para o arquivo JSON de resultados.")
    parser.add_argument("-o", "--output", type=str, default="laudo_visual.html", help="Nome do arquivo HTML de saída (padrão: laudo_visual.html).")
    
    args = parser.parse_args()
    gerar_html(args.json_filepath, output_filename=args.output)


if __name__ == "__main__":
    main()