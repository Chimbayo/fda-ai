# FDA-AI: Agricultural Assistant for Malawi

An advanced AI-powered agricultural advisory system built with **LangGraph** and **Neo4j** for farmers in Malawi. This system uses a multi-agent architecture to provide specialized advice on crops, diseases, weather, and research-based information.

## 🌟 Features

- **Multi-Agent System**: Specialized agents for different agricultural domains:
  - 🌽 **Crop Agent**: Expert in maize varieties, planting, and soil management
  - 🦠 **Disease Agent**: Diagnoses plant diseases and recommends treatments
  - 🌦️ **Weather Agent**: Provides weather-based agricultural advice
  - 📚 **Retrieval Agent**: Searches research papers and technical documents
  - 💬 **Conversation Agent**: Handles general queries and clarifies intent

- **Intelligent Routing**: LangGraph-based workflow automatically routes queries to the most appropriate agent

- **Knowledge Graph**: Neo4j database stores agricultural knowledge as an interconnected graph

- **Conversation Memory**: Persistent conversation history for context-aware responses

- **Local LLM**: Uses Ollama for efficient, privacy-preserving inference

## 🏗️ Architecture

```
fda-ai/
├── app/
│   ├── main.py                # FastAPI entry point
│   ├── config.py              # Configuration management
│   ├── graph/
│   │   ├── langgraph_flow.py  # LangGraph workflow orchestration
│   │   └── router.py          # Agent routing logic
│   ├── agents/
│   │   ├── crop_agent.py      # Crop expertise
│   │   ├── disease_agent.py   # Disease diagnosis
│   │   ├── weather_agent.py   # Weather advice
│   │   ├── retrieval_agent.py # Document retrieval
│   │   └── conversation_agent.py # General conversation
│   ├── memory/
│   │   └── memory_store.py    # Conversation persistence
│   ├── database/
│   │   ├── neo4j_client.py    # Neo4j connection
│   │   └── ingestion.py       # Knowledge base ingestion
│   ├── models/
│   │   └── ollama_model.py    # LLM interface
│   └── utils/
│       ├── formatter.py       # Response formatting
│       └── ranking.py         # Source ranking
├── data/
│   └── sample_knowledge.json  # Sample agricultural data
└── requirements.txt
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Neo4j Database (local or cloud)
- Ollama with a model (e.g., llama3.2)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# App Configuration
DEBUG=False
LOG_LEVEL=INFO
```

### 3. Start Neo4j

```bash
# Using Docker
docker run -d \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/your_password \
    neo4j:latest
```

### 4. Start Ollama

```bash
ollama run llama3.2
```

### 5. Initialize Knowledge Base

```bash
cd fda-ai
python -c "from app.database.ingestion import KnowledgeIngestion; k = KnowledgeIngestion(); k.ingest_from_json('data/sample_knowledge.json')"
```

### 6. Run the Application

```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

## 📡 API Endpoints

### Chat Endpoint

```bash
POST /chat

{
  "message": "What maize variety should I plant in low rainfall areas?",
  "user_id": "farmer_001",
  "location": "Blantyre"
}

Response:
{
  "response": "For low rainfall areas, I recommend...",
  "agent_type": "crop",
  "confidence": 0.85,
  "sources": [...],
  "context": {...}
}
```

### Health Check

```bash
GET /health
```

### Conversation History

```bash
GET /history/{user_id}
DELETE /history/{user_id}
```

## 🌾 Knowledge Base

The system includes knowledge about:

- **Maize Varieties**: Kalulu (SC 301/303), Kanyani (SC 403/419/423), Mbidzi (SC 529/537), Mkango (SC 627/653), Njobvu (SC 719)
- **Crop Diseases**: Maize Leaf Blight, Tomato Early Blight, and treatments
- **Farming Techniques**: Integrated soil fertility, fertilizer recommendations
- **Research**: Agricultural efficiency studies for Malawi

## 🔧 Customization

### Adding New Knowledge

1. Add data to `data/sample_knowledge.json`
2. Run ingestion script
3. Regenerate embeddings if using vector search

### Adding New Agents

1. Create agent file in `app/agents/`
2. Add to `AgentType` enum in `router.py`
3. Register in `langgraph_flow.py`

## 📝 Example Queries

```
"What are the symptoms of maize leaf blight?"
"Should I plant SC 301 or SC 529 in my area?"
"When is the best time to plant maize?"
"How do I treat tomato early blight?"
"What does the research say about maize farming efficiency?"
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

MIT License - Feel free to use for agricultural development projects.

## 🙏 Acknowledgments

- Built with LangGraph for workflow orchestration
- Uses Neo4j for knowledge graph storage
- Powered by Ollama for local LLM inference
- Designed for Malawi agricultural extension services
