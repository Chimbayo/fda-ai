# FDA-AI: Agricultural Assistant for Malawi

An advanced AI-powered agricultural advisory system for farmers in Malawi. The system combines **RAG (Retrieval-Augmented Generation)** with **Neo4j knowledge graphs** and **Ollama** to provide expert agricultural advice based on local PDFs and structured expert knowledge.

## 🌟 Features

### Current Implementation (RAG-based)
- **📚 PDF Knowledge Base**: Ingests and processes agricultural PDFs for local knowledge
- **🧠 Intelligent Retrieval**: FAISS vector search for relevant document chunks
- **🤖 Local LLM**: Uses Ollama with Gemma 4B for fast, private responses
- **📊 Expert Knowledge**: Structured cabbage farming expertise from agricultural experts
- **⚡ Fast Response**: <2s initial token latency with optimized caching

### Knowledge Management
- **🌾 Crop Information**: Varieties, planting schedules, fertilizer requirements
- **🦠 Disease & Pest Management**: Specific treatments and prevention strategies
- **🧪 Chemical Recommendations**: Exact product names and application rates
- **🔄 Crop Rotation**: Best practices for disease prevention
- **📈 Regional Adaptations**: Seasonal and climate-specific advice

### API Features
- **💬 Chat Interface**: RESTful API for farmer queries
- **📈 Knowledge Statistics**: Track knowledge base size and coverage
- **🔄 Knowledge Reloading**: Update knowledge base without restart
- **🏥 Health Monitoring**: System status and performance metrics

## 🏗️ Architecture

```
fda-ai/
├── app/
│   ├── main.py                # FastAPI entry point with RAG system
│   ├── config.py              # Configuration management (Ollama, Neo4j)
│   ├── rag.py                 # RAG system (PDF retrieval + LLM generation)
│   ├── database/
│   │   ├── pdf_ingestion.py   # PDF processing and FAISS indexing
│   │   ├── neo4j_client.py    # Neo4j connection and queries
│   │   ├── neo4j_schema.py    # Knowledge graph schema definition
│   │   ├── ingestion.py       # Sample knowledge ingestion
│   │   └── ingest_cabbage_data.py # Cabbage expert knowledge ingestion
│   ├── models/
│   │   └── ollama_model.py    # Optimized Ollama interface with caching
│   └── utils/
│       ├── formatter.py       # Response formatting utilities
│       └── ranking.py         # Source ranking and confidence scoring
├── data/
│   ├── pdfs/                  # PDF documents for knowledge base
│   ├── vectors/               # FAISS vector index storage
│   ├── sample_knowledge.json  # Sample agricultural data
│   └── cabbage_expert_knowledge.json # Expert cabbage farming knowledge
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

### How the Chatbot Works

1. **📚 Knowledge Ingestion**
   - PDFs are processed and chunked into manageable pieces
   - Text chunks are converted to embeddings using SentenceTransformer
   - FAISS vector index enables fast similarity search
   - Expert knowledge is structured and stored in Neo4j graph database

2. **🔍 Query Processing**
   - User query is received via FastAPI endpoint
   - Query is embedded using the same transformer model
   - FAISS retrieves most relevant document chunks
   - Neo4j provides structured expert knowledge if available

3. **🤖 Response Generation**
   - Retrieved context is combined with user query
   - Prompt is constructed with strict context usage instructions
   - Ollama (Gemma 4B) generates response using only provided context
   - Response includes confidence score and source information

4. **⚡ Performance Optimizations**
   - Response caching for common queries
   - Connection pooling for Ollama requests
   - Prompt compression to reduce token count
   - Streaming responses for better user experience

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Neo4j Database (optional - for structured knowledge)
- Ollama with Gemma 4B model

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Ollama and Gemma 4B

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Download Gemma 4B model
ollama pull gemma:4b
```

### 3. Configure Environment

Create a `.env` file (optional - defaults will work):

```env
# Neo4j Configuration (optional)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma:4b

# App Configuration
DEBUG=False
LOG_LEVEL=INFO
```

### 4. Start Ollama

```bash
ollama serve
```

### 5. Add Knowledge Base

#### Option A: Add PDFs (Recommended)
```bash
# Place PDF files in data/pdfs/ directory
mkdir -p data/pdfs
# Copy your agricultural PDFs here
```

#### Option B: Add Expert Knowledge
```bash
# Ingest cabbage expert knowledge (if Neo4j is running)
python -c "from app.database.ingest_cabbage_data import CabbageKnowledgeIngestion; ingestion = CabbageKnowledgeIngestion(); ingestion.ingest_cabbage_knowledge('data/cabbage_expert_knowledge.json')"
```

### 6. Run the Application

```bash
cd fda-ai
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### 7. Test the System

```bash
# Health check
curl http://localhost:8000/health

# Test chat
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What cabbage variety should I plant?"}'
```

## 📡 API Endpoints

### Chat Endpoint

```bash
POST /chat

Request:
{
  "message": "What cabbage variety should I plant?",
  "user_id": "farmer_001"
}

Response:
{
  "response": "For early harvest, I recommend Star 3317, Malicanta, or Kilimo varieties which mature in 90 days...",
  "sources": ["cabbage_expert_knowledge.json"],
  "confidence": 0.9,
  "context_used": true
}
```

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "pdfs_loaded": 5,
  "chunks_indexed": 1247,
  "has_index": true
}
```

### Knowledge Statistics

```bash
GET /knowledge-stats

Response:
{
  "pdf_count": 5,
  "chunk_count": 1247,
  "index_size_mb": 45.2,
  "last_updated": "2024-05-04T16:30:00Z"
}
```

### Reload Knowledge Base

```bash
POST /reload-knowledge

Response:
{
  "message": "Knowledge base reloaded successfully",
  "pdfs_processed": 5,
  "chunks_created": 1247
}
```

### API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 🌾 Knowledge Base

### Current Expert Knowledge

#### Cabbage Farming (Expert Interview Data)
- **Varieties**: 
  - Local: Garden Glory (180 days)
  - Normal Hybrid: Easy Seed (120-150 days)
  - F1 Hybrids: Star 3317, Malicanta, Kilimo (90 days)
- **Nursery Management**: 30-day nursery, weekly fungicide/pesticide application
- **Fertilizer Schedule**: Manure (Day 7) → NPK (Day 12) → NPK (Day 26) → CAN (Day 40-46)
- **Chemical Treatments**:
  - Pests: Proffex Super/Snowcron for aphids, whitefly, diamondback moth
  - Diseases: Success fungicide for chiwawu, downy mildew, powdery mildew
- **Disease Prevention**: Crop rotation (2-3 year intervals) as best practice

#### Sample Agricultural Data
- **Maize Varieties**: Kalulu (SC 301/303), Kanyani (SC 403/419/423), Mbidzi (SC 529/537), Mkango (SC 627/653), Njobvu (SC 719)
- **Crop Diseases**: Maize Leaf Blight, Tomato Early Blight, and treatments
- **Farming Techniques**: Integrated soil fertility, fertilizer recommendations
- **Research**: Agricultural efficiency studies for Malawi

### Knowledge Sources

1. **Expert Interviews**: Structured WhatsApp conversations with agricultural experts
2. **Research Papers**: Academic studies and technical documents
3. **Extension Materials**: Ministry of Agriculture publications
4. **Farmer Field Schools**: Practical farming experiences
5. **Commercial Data**: Seed company variety specifications

### Data Structure

Each knowledge entry includes:
- ✅ **Source attribution** (expert name, date, region)
- ✅ **Regional applicability** (where the advice applies)
- ✅ **Confidence level** (high/medium/low)
- ✅ **Update frequency** (how often to refresh)
- ✅ **Validation status** (verified by experts)

## 🔧 Customization

### Adding New Knowledge

#### PDF Documents
1. Place PDF files in `data/pdfs/` directory
2. Restart the application or call `/reload-knowledge` endpoint
3. System automatically processes and indexes new content

#### Expert Knowledge
1. Create structured JSON file following `cabbage_expert_knowledge.json` format
2. Use ingestion script: `python -c "from app.database.ingest_cabbage_data import CabbageKnowledgeIngestion; ..."`
3. Knowledge is stored in Neo4j graph with relationships

#### Knowledge Structure
```json
{
  "expert_report": {
    "expert_id": "EXP001",
    "specialization": "Crop_Type",
    "data": {
      "crops": [...],
      "farming_methods": [...],
      "chemicals": [...],
      "disease_prevention": {...}
    }
  }
}
```

### Performance Optimization

- **Caching**: Responses cached for common queries
- **Connection Pooling**: 10 persistent connections to Ollama
- **Prompt Compression**: Reduces token count while maintaining context
- **Vector Index**: FAISS enables sub-millisecond similarity search

## 📝 Example Queries

### Cabbage Farming (Current Expert Knowledge)
```
"What cabbage variety matures in 90 days?"
"How do I treat aphids on cabbage?"
"What fertilizer schedule should I use for cabbage?"
"Which fungicide treats chiwawu disease?"
"How can I prevent cabbage diseases?"
```

### General Agricultural Queries
```
"What are the symptoms of maize leaf blight?"
"Should I plant SC 301 or SC 529 in my area?"
"When is the best time to plant maize?"
"How do I treat tomato early blight?"
"What does the research say about maize farming efficiency?"
```

### System Capabilities
```
"What chemicals should I mix for pest control?"
"How much fertilizer should I apply?"
"What spacing should I use for cabbage?"
"When should I harvest my crop?"
```

## 📊 Performance Metrics

### Expected Response Times
- **Initial Token**: <2 seconds (with caching)
- **Full Response**: 4-6 seconds
- **Cache Hit**: ~0.1 seconds (instant)

### Knowledge Base Capacity
- **PDF Processing**: Supports 100+ PDFs
- **Vector Index**: Millions of text chunks
- **Neo4j Storage**: Unlimited expert knowledge
- **Concurrent Users**: 50+ simultaneous requests

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

MIT License - Feel free to use for agricultural development projects.

## 🙏 Acknowledgments

- **RAG System**: Built with FAISS for vector similarity search and Ollama for local LLM inference
- **Knowledge Graph**: Uses Neo4j for structured expert knowledge storage
- **Performance**: Optimized with caching, connection pooling, and prompt compression
- **Expert Knowledge**: Cabbage farming expertise from agricultural specialists in Malawi
- **Designed For**: Malawi agricultural extension services and smallholder farmers

## 📞 Support & Contact

For questions, contributions, or support:
- **Project**: FDA-AI Agricultural Assistant
- **Purpose**: Helping Malawian farmers with expert agricultural advice
- **Technology**: RAG + Knowledge Graph + Local LLM

---

**Built with ❤️ for Malawi's Agricultural Community**
