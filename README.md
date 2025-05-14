# Proactive Agents

A Python project demonstrating asynchronous agent-based communication using RabbitMQ and OpenAI. This project implements a message-based system where specialized agents can subscribe to topics and process messages asynchronously.

## Features

- Topic-based message routing using RabbitMQ
- Specialized agents for different tasks (poetry, jokes)
- Asynchronous message processing
- Automatic reconnection handling
- Rich console output for better visibility
- Environment-based configuration

## Prerequisites

- Python 3.9 or higher
- RabbitMQ server running locally
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd asynchronous-agents
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Create a `.env` file in the root directory with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Project Structure

```
src/
├── sender.py           # Message publisher for testing
├── receiver.py         # Main application with agent setup
└── consumers/
    ├── base.py        # Base consumer implementation
    ├── reconnecting.py # Reconnection handling logic
    └── __init__.py    # Package initialization
```

## Usage

1. Start the receiver (agent system):
```bash
poetry run python src/receiver.py
```

2. In a separate terminal, send test messages:
```bash
poetry run python src/sender.py
```

## Available Topics

The system supports the following topics:
- `jokes.*` - For joke generation
- `poems.*` - For poetry generation
- `limericks.*` - For limerick generation

## Agents

The system includes two specialized agents:
1. Poetry Agent - Subscribes to poetry-related topics
2. Joking Agent - Subscribes to joke-related topics

Each agent can:
- Subscribe to relevant topics
- Process incoming messages
- Generate appropriate responses based on their specialization

## Development

This project uses Poetry for dependency management. To add new dependencies:

```bash
poetry add package-name
```

## License

[Your chosen license]

## Contributing

[Your contribution guidelines] 
