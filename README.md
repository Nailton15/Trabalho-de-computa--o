# 🏗️ Calculadora de Vigas 3.0

Projeto desenvolvido como trabalho final da disciplina Computação Aplicada à Engenharia, no curso de Engenharia de Produção Civil da UNEB.

Esta ferramenta permite analisar reações de apoio, diagramas de força cortante e momento fletor para diferentes tipos de vigas (biapoiadas, em balanço e contínuas), com suporte à entrada de dados via planilha Excel e exportação automática dos resultados em PDF com os diagramas gerados.

---

## ⚙️ Funcionalidades

- Interface gráfica amigável (Tkinter)
- Leitura de dados estruturais via planilha Excel
- Suporte a múltiplas vigas e múltiplos tipos de carga (pontual e distribuída)
- Geração automática de diagramas de esforço (V e M)
- Exportação dos resultados em arquivos PDF com gráficos

---

## 🧠 Tecnologias Utilizadas

- Python – Linguagem principal
- Tkinter – Interface gráfica
- pandas – Leitura e manipulação de planilhas
- matplotlib e numpy – Geração de gráficos dos diagramas
- fpdf – Geração de arquivos PDF com os resultados
- pillow – Manipulação de imagens

---

## 🧱 Conceitos de Programação Aplicados

O código utiliza conceitos fundamentais de programação em Python, como:

- Listas e dicionários para armazenar e manipular dados das vigas e cargas
- Laços de repetição (`for`) para percorrer dados das planilhas
- Funções personalizadas para modularizar os cálculos e a geração de gráficos
- POO (Programação Orientada a Objetos) para organizar a interface e os componentes da aplicação
- Tratamento de erros para garantir robustez no uso de arquivos e inputs do usuário

---

## 📁 Organização dos Arquivos

| Arquivo / Pasta              | Descrição |
|------------------------------|-----------|
| `Calculadora de Vigas 3.0.py`| Código-fonte principal com a interface e os cálculos |
| `Instruções e Modelo.xlsx`   | Exemplo de planilha para entrada de dados |
| `Logotipo.png`               | Logo do aplicativo |
| `Logo.ico`                   | Ícone do programa |
| `README.md`                  | Este arquivo de apresentação do projeto |

---

## 🔗 Arquivos para Download

- 📄 [Relatório LaTeX completo](https://www.overleaf.com/read/tbbhzysckrry#f2d23b)
- 📽️ [Apresentação de slides em LaTeX (Beamer)](https://www.overleaf.com/read/xnhbkbsgqksp#a42421)
- 📦 [Download do executável (.exe)](https://drive.google.com/drive/folders/1Ecj31lPfMhjptuNqPDsPL9nnydcmb5IM?usp=sharing)
- 🌈 [Download da Rede de Petri Colorida (.cpn)](https://drive.google.com/drive/folders/1Y1kwLDYVQ9YBTiOI3lCD5T7ta2aLenbI?usp=drive_link)

---

## 🧪 Como Executar o Projeto

Você pode executar o projeto de duas formas: via código-fonte em Python ou utilizando o executável disponibilizado.

### 💻 Rodando via Python (Recomendado para desenvolvedores)

1. Instale os pacotes necessários:
   ```bash
   pip install pandas matplotlib numpy fpdf pillow
   
## Desenvolvedores:

Ana Caroline Souza Mendes,
Eduardo do Carmo Szadkowski,
Jamim Suriel Fortaleza Silva, 
Nailton Caldeira dos Santos Filho.
