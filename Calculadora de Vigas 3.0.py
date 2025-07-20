import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import json
import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from fpdf import FPDF
from PIL import Image, ImageTk
import sys
import tempfile

def resource_path(relative_path):
    """Converte caminhos relativos em absolutos para o executável ou desenvolvimento."""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS #type:ignore
    else:
        base_path = os.path.abspath(".")
    full_path = os.path.join(base_path, relative_path)
    print(f"Tentando acessar: {full_path}")  # Para debug
    return full_path

# ============================ CÁLCULOS ============================
def calcular_carga_total(cargas_p, cargas_d):
    return sum(c["valor"] for c in cargas_p) + sum(d["intensidade"] * (d["fim"] - d["inicio"]) for d in cargas_d)

def calcular_momento_total(cargas_p, cargas_d):
    return sum(c["valor"] * c["pos"] for c in cargas_p) + sum(
        d["intensidade"] * (d["fim"] - d["inicio"]) * ((d["fim"] + d["inicio"]) / 2) for d in cargas_d
    )

def calcular_reacoes_viga_continua(carga_total, apoios):
    num = len(apoios)
    return [carga_total / num for _ in apoios]

def plotar_viga(comprimento, cargas_pontuais, cargas_distribuidas, pos_apoios):
    fig, ax = plt.subplots(figsize=(10, 3))

    altura_viga = 0.2
    y_viga = 0.0

    # Desenhar viga
    viga = patches.Rectangle((0, y_viga - altura_viga / 2), comprimento, altura_viga,
                            linewidth=1.5, edgecolor='black', facecolor='lightgrey', zorder=1)
    ax.add_patch(viga)

    # Desenhar apoios (triângulo apontando para baixo)
    for i, x in enumerate(pos_apoios):
        triangulo = patches.RegularPolygon((x, y_viga - 0.3), numVertices=3, radius=0.15,
                                        orientation=0, facecolor='black', zorder=2)
        ax.add_patch(triangulo)
        ax.text(x, y_viga - 0.5, f'Apoio {i+1}', ha='center', va='top', fontsize=9)

    # Cargas pontuais
    for pos, valor in cargas_pontuais:
        y_seta = y_viga + 0.3
        ax.arrow(pos, y_seta + 0.3, 0, -0.3, head_width=0.15 * (comprimento/10), head_length=0.15,
                fc='red', ec='red', linewidth=2, zorder=3)
        ax.text(pos, y_seta + 0.45, f'{valor:.2f} kN', ha='center', color='red', fontsize=9, weight='bold')

    # Cargas distribuídas (flechas acima da viga)
    for inicio, fim, intensidade in cargas_distribuidas:
        y_dist_base = y_viga + 0.3
        altura_dist = 0.3
        # Retângulo representando a carga
        carga_rect = patches.Rectangle((inicio, y_dist_base), fim - inicio, altura_dist,
                                    linewidth=0, facecolor='blue', alpha=0.2, zorder=2)
        ax.add_patch(carga_rect)

        # Setas indicando a carga (apontando para baixo, acima da viga)
        num_setas = int((fim - inicio) * 4) + 2
        xs = np.linspace(inicio, fim, num_setas)
        y_topo_seta = y_dist_base + altura_dist
        for x in xs:
            ax.arrow(x, y_topo_seta, 0, -altura_dist, head_width=0.08 * (comprimento/10),
                    head_length=0.1, fc='blue', ec='blue', linewidth=1, zorder=3)
        ax.text((inicio + fim) / 2, y_topo_seta + 0.15, f'{intensidade:.2f} kN/m',
                ha='center', color='blue', fontsize=9, weight='bold')

    # Reta graduada
    y_graduacao = y_viga - 0.75
    ax.hlines(y=y_graduacao, xmin=0, xmax=comprimento, colors='black', linewidth=1)
    marcacoes = np.linspace(0, comprimento, int(comprimento) + 1)
    for x_mark in marcacoes:
        ax.vlines(x=x_mark, ymin=y_graduacao - 0.05, ymax=y_graduacao + 0.05, colors='black', linewidth=1)
        ax.text(x_mark, y_graduacao - 0.15, f'{x_mark:.1f}m', ha='center', va='top', fontsize=8)

    # Ajustes finais
    ax.set_xlim(-0.5, comprimento + 0.5)
    ax.set_ylim(y_graduacao - 0.4, y_viga + 1.2)
    ax.set_title("Diagrama da Viga e Carregamentos", fontsize=14, pad=20)
    ax.set_xlabel("Posição (m)", fontsize=10) # Adicionado rótulo do eixo X
    ax.axis('off') # Mantém os eixos ocultos, mas o xlabel ainda funciona
    

def forca_cortante(x, reacoes, apoios, cargas_p, cargas_d):
    V = 0
    for i, a in enumerate(apoios):
        if x >= a:
            V += reacoes[i]
    for carga in cargas_p:
        if x >= carga["pos"]:
            V -= carga["valor"]
    for carga in cargas_d:
        if x >= carga["fim"]:
            V -= carga["intensidade"] * (carga["fim"] - carga["inicio"])
        elif x >= carga["inicio"]:
            V -= carga["intensidade"] * (x - carga["inicio"])
    return V

def momento_fletor(x, reacoes, apoios, cargas_p, cargas_d):
    M = 0
    for i, a in enumerate(apoios):
        if x >= a:
            M += reacoes[i] * (x - a)
    for carga in cargas_p:
        if carga["pos"] <= x:
            M -= carga["valor"] * (x - carga["pos"])
    for carga in cargas_d:
        x1, x2 = carga["inicio"], carga["fim"]
        q = carga["intensidade"]
        if x <= x1:
            continue
        elif x >= x2:
            L = x2 - x1
            xc = (x1 + x2) / 2
            M -= q * L * (x - xc)
        else:
            L = x - x1
            xc = (x1 + x) / 2
            M -= q * L * (x - xc)
    return M

# ============================ PROCESSAMENTO ============================
def processar_arquivo(caminho):
    try:
        # 1. Validação do arquivo e da aba
        xls = pd.ExcelFile(caminho)
        if "Vigas" not in xls.sheet_names:
            messagebox.showerror("Erro de Planilha", "A planilha deve conter uma aba chamada 'Vigas'.")
            return

        df = pd.read_excel(xls, sheet_name="Vigas")

    except FileNotFoundError:
        messagebox.showerror("Erro de Arquivo", "Arquivo não encontrado. Verifique o caminho.")
        return
    except pd.errors.EmptyDataError:
        messagebox.showerror("Erro de Conteúdo", "O arquivo Excel está vazio ou a aba 'Vigas' não contém dados.")
        return
    except Exception as e:
        messagebox.showerror("Erro ao Ler Planilha", f"Erro inesperado ao ler o arquivo Excel:\n{e}")
        return

    # 2. Validação das colunas obrigatórias
    colunas_obrigatorias = ["ID", "Tipo", "L (m)", "Apoios (m)", "Cargas JSON"]
    if not all(col in df.columns for col in colunas_obrigatorias):
        missing_cols = [col for col in colunas_obrigatorias if col not in df.columns]
        messagebox.showerror("Erro de Formato",
                            f"A planilha 'Vigas' deve conter as seguintes colunas: {', '.join(colunas_obrigatorias)}.\n"
                            f"Colunas faltando: {', '.join(missing_cols)}")
        return

    pdf_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("Arquivos PDF", "*.pdf")],
        title="Salvar Relatório PDF Como...",
        initialfile="Relatorio_Vigas.pdf"
    )

    if not pdf_path:
        return # Usuário cancelou o salvamento

    with tempfile.TemporaryDirectory() as pasta_graficos:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # <<< ALTERAÇÃO 1: INICIALIZA A LISTA PARA ARMAZENAR ERROS >>>
        vigas_com_erro = []

        processed_beams_count = 0 
        for index, viga in df.iterrows():
            viga_id = viga.get("ID", f"Linha {index+2}") 
            try:
                # 3. Validação dos tipos de dados e valores
                tipo = str(viga["Tipo"]).lower().strip() 
                if tipo not in ["biapoiada", "balanço", "contínua"]:
                    raise ValueError(f"Tipo de viga inválido '{viga['Tipo']}'. Tipos aceitos: 'biapoiada', 'balanço', 'contínua'.")

                L = float(viga["L (m)"])
                if L <= 0:
                    raise ValueError("O comprimento da viga (L) deve ser um valor positivo.")

                try:
                    apoios = json.loads(viga["Apoios (m)"])
                    if not isinstance(apoios, list) or not all(isinstance(x, (int, float)) for x in apoios):
                        raise ValueError("O campo 'Apoios (m)' deve ser uma lista JSON de números.")
                    if not all(0 <= a <= L for a in apoios):
                        raise ValueError("As posições dos apoios devem estar dentro do comprimento da viga (0 a L).")
                except json.JSONDecodeError:
                    raise ValueError("O campo 'Apoios (m)' não é um JSON válido.")

                try:
                    cargas = json.loads(viga["Cargas JSON"])
                    if not isinstance(cargas, list):
                        raise ValueError("O campo 'Cargas JSON' deve ser uma lista JSON.")
                    for c in cargas:
                        if not isinstance(c, dict):
                            raise ValueError("Cada carga em 'Cargas JSON' deve ser um objeto JSON.")
                        if c.get("tipo") == "pontual":
                            if not all(k in c for k in ["pos", "valor"]):
                                raise ValueError("Carga pontual deve ter 'pos' e 'valor'.")
                            if not isinstance(c["pos"], (int, float)) or not isinstance(c["valor"], (int, float)):
                                raise ValueError("Posição e valor da carga pontual devem ser números.")
                            if not (0 <= c["pos"] <= L):
                                raise ValueError("A posição da carga pontual deve estar dentro do comprimento da viga (0 a L).")
                        elif c.get("tipo") == "distribuida":
                            if not all(k in c for k in ["inicio", "fim", "intensidade"]):
                                raise ValueError("Carga distribuída deve ter 'inicio', 'fim' e 'intensidade'.")
                            if not all(isinstance(c[k], (int, float)) for k in ["inicio", "fim", "intensidade"]):
                                raise ValueError("Início, fim e intensidade da carga distribuída devem ser números.")
                            if not (0 <= c["inicio"] < c["fim"] <= L):
                                raise ValueError("O intervalo da carga distribuída deve estar dentro do comprimento da viga (0 a L) e 'inicio' < 'fim'.")
                        else:
                            raise ValueError("Tipo de carga inválido. Deve ser 'pontual' ou 'distribuida'.")
                except json.JSONDecodeError:
                    raise ValueError("O campo 'Cargas JSON' não é um JSON válido.")

                cargas_p = [c for c in cargas if c["tipo"] == "pontual"]
                cargas_d = [c for c in cargas if c["tipo"] == "distribuida"]

                carga_total = calcular_carga_total(cargas_p, cargas_d)
                momento_total = calcular_momento_total(cargas_p, cargas_d)

                if tipo == "biapoiada":
                    if len(apoios) != 2:
                        raise ValueError("Viga biapoiada deve ter exatamente 2 apoios.")
                    a, b = apoios[0], apoios[1]
                    span = b - a
                    if span <= 0:
                        raise ValueError("Para viga biapoiada, a posição do segundo apoio deve ser maior que a do primeiro.")
                    Rb = momento_total / span
                    Ra = carga_total - Rb
                    reacoes = [Ra, Rb]
                elif tipo == "balanço":
                    if len(apoios) != 1:
                        raise ValueError("Viga em balanço deve ter exatamente 1 apoio.")
                    Ra = carga_total 
                    reacoes = [Ra]
                elif tipo == "contínua":
                    if len(apoios) < 2:
                        raise ValueError("Viga contínua deve ter no mínimo 2 apoios.")
                    reacoes = calcular_reacoes_viga_continua(carga_total, apoios)
                else:
                    continue

                # Geração dos gráficos e PDF (código existente sem alteração)
                cargas_p_formatadas = [(c['pos'], c['valor']) for c in cargas_p]
                cargas_d_formatadas = [(c['inicio'], c['fim'], c['intensidade']) for c in cargas_d]

                fig_esquema = os.path.join(pasta_graficos, f"{viga_id}_esquema.png")
                plotar_viga(L, cargas_p_formatadas, cargas_d_formatadas, apoios)
                plt.savefig(fig_esquema, bbox_inches='tight')
                plt.close()

                xs = np.linspace(0, L, 500)
                Vs = [forca_cortante(x, reacoes, apoios, cargas_p, cargas_d) for x in xs]
                Ms = [momento_fletor(x, reacoes, apoios, cargas_p, cargas_d) for x in xs]

                fig_v = os.path.join(pasta_graficos, f"{viga_id}_cortante.png")
                plt.figure(figsize=(8, 3))
                plt.plot(xs, Vs, label="Força Cortante")
                plt.axhline(0, color="black", lw=0.7)
                plt.title(f"Força Cortante - {viga_id}")
                plt.xlabel("Posição (m)", fontsize=10)
                plt.ylabel("Força Cortante (kN)", fontsize=10)
                plt.tight_layout()
                plt.savefig(fig_v)
                plt.close()

                fig_m = os.path.join(pasta_graficos, f"{viga_id}_momento.png")
                plt.figure(figsize=(8, 3))
                plt.plot(xs, Ms, label="Momento Fletor", color="orange")
                plt.axhline(0, color="black", lw=0.7)
                plt.title(f"Momento Fletor - {viga_id}")
                plt.xlabel("Posição (m)", fontsize=10)
                plt.ylabel("Momento Fletor (kNm)", fontsize=10)
                plt.tight_layout()
                plt.savefig(fig_m)
                plt.close()

                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, f"Relatório - Viga {viga_id}", ln=True, align='C')

                pdf.image(fig_esquema, w=180)
                pdf.ln(5)

                pdf.set_font("Arial", "", 12)
                pdf.cell(0, 8, f"Tipo: {tipo.capitalize()}", ln=True)
                pdf.cell(0, 8, f"Comprimento: {L} m", ln=True)
                pdf.cell(0, 8, f"Apoios: {', '.join(map(str, apoios))}", ln=True)
                pdf.cell(0, 8, f"Carga Total Aplicada: {carga_total:.2f} kN", ln=True)
                pdf.cell(0, 8, f"Momento Total (na origem): {momento_total:.2f} kNm", ln=True)

                for i, r in enumerate(reacoes):
                    pdf.cell(0, 8, f"Reação no apoio {i+1} (R{chr(65+i)}): {r:.2f} kN", ln=True)

                pdf.ln(5)
                pdf.image(fig_v, w=180)
                pdf.ln(5)
                pdf.image(fig_m, w=180)
                
                processed_beams_count += 1

            except ValueError as ve:
                mensagem_erro = f"Erro na viga {viga_id}: {ve}"
                messagebox.showwarning("Erro nos Dados da Viga", f"{mensagem_erro}\nEsta viga será ignorada.")
                # <<< ALTERAÇÃO 2: ADICIONA O ERRO À LISTA >>>
                vigas_com_erro.append({"id": viga_id, "erro": str(ve)})
            
            except Exception as e:
                mensagem_erro = f"Erro inesperado ao processar a viga {viga_id}: {e}"
                messagebox.showwarning("Erro Inesperado", f"{mensagem_erro}\nEsta viga será ignorada.")
                # <<< ALTERAÇÃO 2: ADICIONA O ERRO À LISTA >>>
                vigas_com_erro.append({"id": viga_id, "erro": str(e)})

        if processed_beams_count == 0 and not vigas_com_erro:
            messagebox.showwarning("Nenhuma Viga Processada", "Nenhuma viga pôde ser processada. Verifique se o arquivo contém dados.")
            return

        # <<< ALTERAÇÃO 3: ADICIONA A SEÇÃO DE ERROS AO PDF >>>
        if vigas_com_erro:
            # Adiciona uma nova página se já houver conteúdo
            if processed_beams_count > 0:
                pdf.add_page()
            else: # Se nenhuma viga foi processada, cria a primeira página
                pdf.add_page()

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Resumo de Vigas com Erros de Leitura", ln=True, align='C')
            pdf.ln(10)

            for item_erro in vigas_com_erro:
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 7, f"Viga ID: {item_erro['id']}", ln=True)
                pdf.set_font("Arial", "", 11)
                pdf.set_text_color(220, 50, 50) # Cor vermelha para o erro
                pdf.multi_cell(0, 6, f"Erro: {item_erro['erro']}")
                pdf.set_text_color(0, 0, 0) # Restaura a cor preta
                pdf.ln(5)

        # Adiciona o rodapé (movido para antes do output)
        if pdf.page_no() > 0: # Garante que há uma página para adicionar o rodapé
            pdf.set_y(-45) # Posiciona o cursor perto do final da página
            pdf.set_font("Arial", "I", 10)
            pdf.cell(0, 10, "Desenvolvido por:", ln=True, align="L")
            pdf.cell(0, 5, "Ana Caroline Souza Mendes,", ln=True, align="L")
            pdf.cell(0, 5, "Eduardo do Carmo Szadkowski, ", ln=True, align="L")
            pdf.cell(0, 5, "Jamim Suriel Fortaleza Silva e", ln=True, align="L")
            pdf.cell(0, 5, "Nailton Caldeira dos Santos Filho", ln=True, align="L")

        try:
            pdf.output(pdf_path)
            messagebox.showinfo("Sucesso", f"Relatório gerado com sucesso em:\n{pdf_path}")
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar o arquivo PDF.\nVerifique se você tem permissão no local escolhido.\n\nErro técnico: {e}")

# ============================ UI COM ESTILO ============================

def selecionar_arquivo():
    caminho = filedialog.askopenfilename(filetypes=[("Planilhas Excel", "*.xlsx")])
    if caminho:
        entrada_arquivo.delete(0, tk.END)
        entrada_arquivo.insert(0, caminho)

def executar():
    caminho = entrada_arquivo.get()
    if not caminho:
        messagebox.showerror("Erro", "Selecione um arquivo.")
        return
    processar_arquivo(caminho)

def baixar_modelo():
    try:
        # Verifica se o arquivo de modelo existe antes de tentar copiar
        modelo_origem = resource_path("Instruções e Modelo.xlsx")
        if not os.path.exists(modelo_origem):
            messagebox.showerror("Erro", f"O arquivo de modelo não foi encontrado: {modelo_origem}")
            return

        destino = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Planilha Excel", "*.xlsx")], initialfile="modelo_vigas.xlsx")
        if destino:
            shutil.copyfile(modelo_origem, destino)
            messagebox.showinfo("Sucesso", "Modelo copiado com sucesso!")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao copiar modelo:\n{e}")

janela = tk.Tk()
janela.title("Calculadora de Vigas 3.0 - Geração de Relatório")
janela.geometry("750x400")
janela.config(bg="#e5e8e1")
try:
    icon_path = resource_path("Logo.ico")
    janela.iconbitmap(icon_path)
except Exception as e:
    print(f"Erro ao carregar ícone: {e}")

# Frame para agrupar imagem e título
header_frame = tk.Frame(janela, bg="#e5e8e1")
header_frame.pack(pady=10)

# Carrega e exibe a imagem
try:
    image_path = resource_path("Logo.png")
    if os.path.exists(image_path):
        original_image = Image.open(image_path)
        resized_image = original_image.resize((150, 150))
        tk_image = ImageTk.PhotoImage(resized_image)
        img_label = tk.Label(header_frame, image=tk_image, bg="#e5e8e1")
        img_label.image = tk_image #type:ignore
        img_label.pack(side=tk.LEFT, padx=(0, 10))
    else:
        raise FileNotFoundError(f"Arquivo não encontrado: {image_path}")
except Exception as e:
    print(f"Erro ao carregar logo: {str(e)}")
    # Placeholder se a imagem não carregar
    img_label = tk.Label(header_frame, text="[LOGO]", bg="#e5e8e1", font=("Arial", 14))
    img_label.pack(side=tk.LEFT, padx=(0, 10))

# Título ao lado da imagem
titulo = tk.Label(header_frame, text="Calculadora de Vigas 3.0",
                font=("Segoe UI", 26, "bold"), bg="#e5e8e1")
titulo.pack(side=tk.LEFT)

# Frame principal para a área dos botões com cor diferente
main_frame = tk.Frame(janela, bg="#e5e8e1",  # Cor mais escura para o fundo
                    padx=20, pady=20)  # Padding interno
main_frame.pack(fill=tk.BOTH, expand=True)  # Preenche todo o espaço disponível


# Frame de input dentro do main_frame (herda a cor)
frame_input = tk.Frame(main_frame, bg="#e5e8e1")
frame_input.pack(pady=10)

label_arquivo = tk.Label(frame_input, text="Arquivo Excel:",
                        font=("Segoe UI", 12), bg="#e5e8e1")
label_arquivo.grid(row=0, column=0, padx=5, sticky="e")

entrada_arquivo = tk.Entry(frame_input, width=40, font=("Segoe UI", 10))
entrada_arquivo.grid(row=0, column=1, padx=5)

btn_procurar = tk.Button(frame_input, text="Procurar", command=selecionar_arquivo,
                        bg="#007acc", fg="white", font=("Segoe UI", 10, "bold"))
btn_procurar.grid(row=0, column=2, padx=5)

btn_executar = tk.Button(main_frame, text="Gerar Relatório PDF", command=executar,
                        bg="#28a745", fg="white", font=("Segoe UI", 12, "bold"), width=25)
btn_executar.pack(pady=10)

btn_modelo = tk.Button(main_frame, text="Baixar modelo de planilha Excel",
                    command=baixar_modelo, bg="#ffc107", fg="black",
                    font=("Segoe UI", 10, "bold"))
btn_modelo.pack(pady=5)

# Rodapé com fundo original
rodape = tk.Label(janela,
                text="Desenvolvido por: Ana Caroline Souza Mendes, Eduardo do Carmo Szadkowski, Jamim Suriel Fortaleza Silva e Nailton Caldeira dos Santos Filho",
                font=("Segoe UI", 8), bg="#e5e8e1", fg="#777")
rodape.pack(side="bottom", pady=10)

janela.mainloop()