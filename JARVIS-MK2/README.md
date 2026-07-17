# JARVIS-MK2

A modular personal AI operating system inspired by fictional assistants like JARVIS, built as a realistic engineering project.

## Project Structure

```
JARVIS-MK2/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── CLAUDE.md               # Development guidelines
│
├── core/                   # Core system components
│   ├── controller.py       # Application lifecycle management
│   ├── router.py           # Message/request routing
│   ├── config.py           # Configuration management
│   ├── logger.py           # Logging system
│   └── events.py           # Event system for inter-module communication
│
├── brain/                  # Cognitive components
│   ├── planner.py          # Goal decomposition and planning
│   ├── decision_engine.py  # Decision making logic
│   ├── critic.py           # Decision review and improvement
│   └── reasoning.py        # Logical reasoning and inference
│
├── memory/                 # Memory systems
│   ├── memory_manager.py   # Memory coordination
│   ├── short_term.py       # Short-term memory (working memory)
│   └── long_term.py        # Long-term memory (persistent storage)
│
├── modules/                # Functional modules
│   ├── system/             # System monitoring and control
│   ├── voice/              # Speech input/output
│   ├── vision/             # Computer vision
│   ├── tools/              # External tool integration
│   └── automation/         # Workflow automation
│
├── tasks/                  # Task management system
│   ├── task_manager.py     # Task creation and tracking
│   ├── scheduler.py        # Task scheduling
│   └── queue.py            # Asynchronous task queue
│
├── tests/                  # Test suite
├── docs/                   # Documentation
└── memory/                 # Persistent memory storage (JSON files, etc.)
```

## Features (Planned)

- Voice input and output
- Local AI model integration (Ollama, Llama family)
- Long-term and short-term memory
- Task planning and execution
- System monitoring and control
- Tool execution and automation
- Vision capabilities
- Event-driven architecture
- Modular design for easy extension

## Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python main.py`

## Development

See [CLAUDE.md](CLAUDE.md) for development guidelines and architecture details.

## License

MIT