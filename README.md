# Bob the Builder - Twitter AI Assistant

Bob the Builder is an AI-powered Twitter assistant that engages in conversations through DMs, mentions, and Twitter Spaces. Bob is a friendly and knowledgeable construction and DIY expert who loves helping others build and create things.

## Overview

Bob uses a dual-LLM architecture:
- Fast responses with GPT-3.5 Turbo for immediate interactions
- Deep analysis with GPT-4 for complex building discussions
- Confidence-based interaction system for natural conversation flow
- Memory system to maintain context across conversations

## Features

### Direct Message Handling
- Responds to DMs with helpful building advice
- Maintains conversation history for context
- Verifies message delivery and tracks responses
- Handles message requests automatically

### Mention Processing
- Monitors and responds to Twitter mentions
- Tracks replied tweets to avoid duplicates
- Contextual responses based on mention content

### Space Participation (Coming Soon)
- Joins relevant building/DIY spaces
- Builds confidence through listening
- Contributes when confidence threshold is met
- Analyzes conversation context before speaking

## Setup

1. Clone the repository:
```bash
git clone https://github.com/peytontolbert/bob-the-twitter-agent.git
cd bob-the-twitter-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`:
```env
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
OPENAI_API_KEY=your_openai_key
```

4. Run Bob:
```bash
python main.py
```

## Project Structure

```
├── main.py                     # Main entry point
├── src/
│   ├── agent/
│   │   ├── action_handler.py   # Selenium browser control
│   │   ├── bob_agent.py        # Bob's core logic and personality
│   │   ├── message_controller.py # DM handling
│   │   ├── mention_controller.py # Mention processing
│   │   └── conversation_memory.py # Memory management
│   └── utils/
│       └── browser_utils.py    # Selenium utilities
├── data/
│   └── conversations/          # Conversation history storage
├── scripts/
│   ├── debug_conversations.py  # Message debugging
│   └── debug_accept_requests.py # Request debugging
└── tests/
    └── test_tweet_interactions.py
```

## Bob's Personality

Bob is designed to be:
- Helpful and encouraging in building projects
- Focused on practical, actionable advice
- Safety-conscious in all recommendations
- Patient with beginners
- Enthusiastic about building and creating

## Technical Details

### Memory System
- Persistent conversation storage
- Tracks message history per user
- Maintains context across sessions
- Handles both DMs and mentions

### Message Processing
- Validates message delivery
- Ensures chronological processing
- Deduplicates responses
- Handles system messages appropriately

### Confidence System
- Starts at 0% confidence with new users
- Builds through successful interactions
- Affects response style and engagement
- Resets appropriately between sessions

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Debugging Tools
```bash
# Debug conversation processing
python scripts/debug_conversations.py

# Debug message request handling
python scripts/debug_accept_requests.py
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Safety Notice

Bob provides general guidance but is not a replacement for professional expertise. Always consult qualified professionals for specific building projects and follow local regulations and safety guidelines.

## License

MIT License - See LICENSE file for details 