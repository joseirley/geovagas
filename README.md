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
- **Deploy na Vercel**: funções Python em `api/` consultam o GO BH sob demanda e disponibilizam a busca JobSpy das fontes externas.

### Fontes externas

As abas LinkedIn, Indeed e Glassdoor consultam uma fonte por vez pelo endpoint `GET /api/busca`. O JobSpy está fixado em `requirements.txt` (Python 3.10+). Cada busca solicita até 300 resultados e `hours_old=144`; Indeed e Glassdoor recebem `country_indeed="Brazil"`. A descrição completa fica desativada para evitar requisições extras por anúncio.

O backend valida `date_posted` em UTC, exclui datas comprovadamente antigas e futuras, e mantém datas ausentes ou impossíveis de validar em uma lista separada. Datas sem horário só são marcadas recentes quando o dia inteiro cabe dentro da janela de 144 horas. Os resultados de cada parâmetro de busca ficam em cache de processo por até 60 minutos. A Vercel executa funções de até 60 segundos nesta configuração; bloqueios, lentidão ou indisponibilidade da plataforma aparecem como falha da fonte consultada.

O mapa externo abre na visão do Brasil e agrega vagas por município, apenas quando cidade e estado são reconhecidos e o geocodificador confirma a localização. Todos os municípios distintos das vagas recentes são geocodificados, com cache persistente local e intervalo compatível com o serviço público; vagas sem data confirmada permanecem na lista sem chamadas extras de geocodificação. Municípios sem coordenadas confirmadas permanecem na lista e são contabilizados no aviso. A lista mostra 50 registros por vez e permite carregar mais. O cache de buscas é temporário e pode desaparecer entre execuções serverless.

Para executar localmente com as fontes externas, use Python 3.10 ou superior e instale `requirements.txt` antes de iniciar `server.py`. A pasta `publicacao-dominio` também usa essa dependência e requer Python 3.10+ com Passenger/WSGI. Hospedagens limitadas ao Python 3.6 não são compatíveis com JobSpy.

---

## 🚀 Como Executar

### Deploy na Vercel
Importe este repositório como um projeto Vercel, mantendo a raiz do projeto como diretório de deploy. A configuração em `vercel.json` publica a página estática e as rotas `/api/vagas`, `/api/sync` e `/api/busca` como funções Python. Não é necessário configurar um build command ou variáveis de ambiente; a Vercel instala a dependência listada em `requirements.txt`.

As vagas são consultadas na API do GO BH quando a página carrega; a resposta pode ficar em cache na borda por até 5 minutos. O botão de atualização faz uma nova consulta. A Vercel não persiste arquivos gravados pela função, então a atualização não grava `data/vagas.json`.

### Opção 1: Atalho Rápido no Windows (Recomendado)
Basta dar dois cliques no arquivo:
👉 **`iniciar_geovagas.bat`**

O script verifica Python 3.10+, cria o ambiente local `.venv`, instala JobSpy se necessário, inicia o servidor e abre a página no navegador.

### Opção 2: Linha de Comando (Terminal)
1. Certifique-se de ter Python 3.10 ou superior instalado.
2. Instale as dependências:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Inicie o servidor:
   ```bash
   python server.py
   ```
4. Acesse no navegador:
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