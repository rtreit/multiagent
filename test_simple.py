#!/usr/bin/env python3
import os
import sys
sys.path.append('.')

# Set environment variable manually (replace with your actual API key)
os.environ['OPENAI_API_KEY'] = 'your-openai-api-key-here'

from agents.llm_agent import LangGraphToolAgent

print('Testing OpenAI integration...')
print(f'API Key: {os.environ.get("OPENAI_API_KEY", "Not set")[:20]}...')

agent = LangGraphToolAgent(9014, 8024, 'http://localhost:9010')
response = agent.handle_message('what is the square root of 70?')
print(f'Response: {response}')
