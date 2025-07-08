# 🤖 Autonomous AI Agent System

A fully automated AI agent with autonomous reasoning, task planning, execution capabilities, and a modern web interface for monitoring and control.

## ✨ Features

- **🧠 Autonomous Reasoning**: AI-powered task analysis and planning
- **📋 Task Management**: Intelligent task prioritization and execution
- **🔄 Self-Learning**: Learns from past experiences and improves over time
- **🛠️ Tool Integration**: Web search, file operations, code execution, data analysis
- **🌐 Web Dashboard**: Modern, real-time monitoring interface
- **💾 Persistent Memory**: SQLite + ChromaDB for semantic memory
- **🔌 Multi-LLM Support**: OpenAI GPT-4, Anthropic Claude
- **📊 Analytics**: Performance tracking and execution metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Git

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd ai-agent-system
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure API keys:**
Edit `config.yaml` and add your API keys:
```yaml
api_keys:
  openai: "your-openai-api-key-here"
  anthropic: "your-anthropic-api-key-here"
```

4. **Run the system:**
```bash
python main.py
```

5. **Access the web dashboard:**
Open your browser to `http://localhost:8000`

## 🎯 Usage Examples

### Web Interface
The web dashboard provides:
- Real-time agent status monitoring
- Task creation and management
- Memory usage statistics
- Configuration management

### CLI Mode
Run agent without web interface:
```bash
python main.py --mode agent
```

### Web Interface Only
Run only the web dashboard:
```bash
python main.py --mode web --port 8080
```

## 📋 Task Examples

The agent can handle various types of tasks:

1. **Research Tasks:**
```
"Research the latest developments in quantum computing and create a summary"
```

2. **Data Analysis:**
```
"Analyze the CSV file 'sales_data.csv' and create visualizations"
```

3. **Code Generation:**
```
"Create a Python script to scrape weather data from a public API"
```

4. **File Operations:**
```
"Create a project structure for a Flask web application"
```

5. **API Integration:**
```
"Fetch data from the GitHub API and analyze repository trends"
```

## ⚙️ Configuration

### Basic Configuration (`config.yaml`)

```yaml
agent:
  name: "AutoAgent"
  model: "gpt-4"
  max_iterations: 50
  timeout_seconds: 300

autonomous_mode:
  enabled: true
  check_interval_seconds: 60
  max_concurrent_tasks: 3

tools:
  web_search: true
  file_operations: true
  code_execution: true
  data_analysis: true
  api_calls: true

web_interface:
  host: "0.0.0.0"
  port: 8000
```

### Advanced Configuration

- **Memory Settings**: Configure SQLite and ChromaDB
- **Logging**: Customize log levels and outputs
- **Security**: API rate limits and sandboxing
- **Performance**: Concurrency and timeout settings

## 🏗️ Architecture

```
src/
├── agent/
│   ├── core.py          # Main agent logic
│   ├── memory.py        # Memory management
│   ├── planner.py       # Task planning
│   ├── tools.py         # Tool implementations
│   └── llm.py           # LLM interface
└── web/
    ├── app.py           # FastAPI web server
    └── templates/       # Web interface templates
```

### Core Components

1. **AutoAgent**: Main agent class with autonomous loop
2. **MemoryManager**: Persistent storage and learning
3. **TaskPlanner**: AI-powered task decomposition
4. **ToolManager**: Execution capabilities
5. **LLMInterface**: Multi-provider AI integration

## 🔧 Development

### Running Tests
```bash
python -m pytest tests/
```

### Development Mode
```bash
python main.py --log-level DEBUG
```

### Custom Tools
Add new tools by extending the `ToolManager` class:

```python
async def custom_tool(self, param1: str, param2: int) -> Dict[str, Any]:
    """Custom tool implementation"""
    # Your tool logic here
    return {"success": True, "result": "Tool output"}
```

## 📊 Monitoring

### Web Dashboard Features
- **Real-time Status**: Agent state and active tasks
- **Task Management**: Create, monitor, and cancel tasks
- **Memory Analytics**: Usage statistics and patterns
- **Performance Metrics**: Execution times and success rates

### API Endpoints
- `GET /api/status` - Agent status
- `POST /api/tasks` - Create task
- `GET /api/tasks` - List tasks
- `DELETE /api/tasks/{id}` - Cancel task
- `GET /api/memory/stats` - Memory statistics

## 🔒 Security

### Sandboxing
- Code execution in isolated environment
- File system access restrictions
- Network request filtering
- Resource usage limits

### Best Practices
- Use environment variables for API keys
- Regular security updates
- Monitor agent actions
- Implement rate limiting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

**Agent won't start:**
- Check API keys in config.yaml
- Verify Python version (3.8+)
- Install missing dependencies

**Web interface not accessible:**
- Check port availability
- Verify firewall settings
- Check logs for errors

**Tasks failing:**
- Review agent logs
- Check tool configurations
- Verify internet connectivity

### Support

- 📚 Documentation: Check the `/docs` folder
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions

## 🎉 Acknowledgments

Built with:
- FastAPI for web interface
- SQLite + ChromaDB for memory
- OpenAI & Anthropic APIs
- Tailwind CSS for styling

---

**Ready to deploy your autonomous AI agent? Start with the Quick Start guide above! 🚀**