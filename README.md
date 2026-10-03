# GeoVagas - Encontre. Conecte. Trabalhe. 📍

O **GeoVagas** é uma plataforma web interativa focada na busca de oportunidades de emprego e estágio através da **localização geoespacial**.

O projeto utiliza como fonte inicial os dados abertos oficiais da **Prefeitura de Belo Horizonte (GO BH)**, georreferenciando os locais de trabalho das vagas em um mapa dinâmico integrado a uma tabela completa e filtros inteligentes.

> ⚠️ **Aviso Importante**: Esta plataforma é voltada exclusivamente para **visualização geoespacial**. Toda candidatura deve ser realizada diretamente no portal oficial do **GO BH**.

---

## 📸 Funcionalidades

1. **Mapa Interativo (Centro da Tela)**:
   - Visualização por mapa com **OpenStreetMap** (100% livre de chaves/tokens).
   - Agrupamento em **clusters de proximidade** para facilitar a navegação por regiões de Belo Horizonte.
   - Popups com informações completas: Cargo, Empregador, Endereço, Modalidade, Escolaridade, Horário, Carga Horária, Salário e link oficial da vaga.
   - Interatividade bidirecional: clicar num marcador destaca a vaga na tabela; clicar na tabela abre o marcador correspondente no mapa.

2. **Filtros Laterais Inteligentes**:
   - **Busca por palavra-chave** (busca por bairro, empresa ou termos do requisito).
   - **Cargo / Ocupação** (lista dinâmica dos cargos disponíveis).
   - **Tipo de Contratação** (*CLT*, *Estágio*, etc.).
   - **Escolaridade** (*Superior Incompleto*, *Médio Completo*, etc.).
   - **Horário de Trabalho** (*Manhã*, *Tarde*, *Indiferente*, etc.).
   - **Carga Horária** (*Meio Período*, *Período Integral*, *Escala 12x36*, etc.).
   - **Faixa Salarial** (Até R$ 1.000, R$ 1.000 a R$ 1.500, R$ 1.500 a R$ 2.000 e Acima de R$ 2.000).
   - Botão **Limpar Filtros** e botão de **Sincronização em tempo real com a PBH**.

3. **Tabela Completa de Oportunidades**:
   - Localizada logo abaixo do mapa para visualização simultânea.
   - Atualizada instantaneamente conforme os filtros aplicados.
   - Ordenação por colunas e link direto para visualização oficial no GO BH.

---

## 🛠️ Tecnologias Utilizadas

- **Frontend**: HTML5, CSS3 moderno (design clean e responsivo), JavaScript ES6+.
- **Mapas**: [Leaflet.js](https://leafletjs.com/) e [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) com base OpenStreetMap.
- **Backend / Servidor**: Python 3 nativo (`http.server` / `socketserver`), leve e sem dependências pesadas obrigatórias.
- **Raspagem & Geocodificação**: Python (`urllib`, `json`, `ssl`) consumindo a API oficial da PBH com resolução de coordenadas via OpenStreetMap/Nominatim e cache local persistente.

---

## 🚀 Como Executar

### Opção 1: Atalho Rápido no Windows (Recomendado)
Basta dar dois cliques no arquivo:
👉 **`iniciar_geovagas.bat`**

O script irá validar os dados, iniciar o servidor web e abrir automaticamente a página no seu navegador.

### Opção 2: Linha de Comando (Terminal)
1. Certifique-se de ter o Python 3 instalado.
2. Inicie o servidor:
   ```bash
   python server.py
   ```
3. Acesse no navegador:
   ```
   http://localhost:8501
   ```

---

## 📁 Estrutura de Arquivos

```
geovagas/
├── .gitignore                   # Arquivos ignorados pelo Git
├── README.md                    # Documentação do projeto
├── index.html                   # Interface web principal (HTML5 + CSS + Leaflet JS)
├── server.py                    # Servidor HTTP nativo em Python e endpoints de API
├── scraper.py                   # Módulo de raspagem de dados do GO BH e geocodificação
├── iniciar_geovagas.bat         # Inicializador rápido com 1 clique para Windows
├── data/
│   ├── vagas.json               # Dados consolidados das vagas raspadas
│   └── geocache.json            # Cache de coordenadas dos endereços
├── logo/
│   └── logo_geovagas.png        # Logomarca original do GeoVagas
└── static/
    └── logo_geovagas.png        # Ativos estáticos servidos na web
```

---

## 👨‍💻 Autoria e Contato

- **Desenvolvido por**: José Irley
- **Contato**: [jose.geografo@gmail.com](mailto:jose.geografo@gmail.com)
