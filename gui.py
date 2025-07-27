#!/usr/bin/env python3
"""
Clean GUI using OpenAI-compatible API endpoints instead of A2A protocol.
This eliminates the 12+ second delays caused by A2A client creation.
"""

from flask import Flask, render_template_string, request, jsonify
import requests
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gui_openai")

app = Flask(__name__)

# Agent configuration - OpenAI API ports
AGENTS = {
    "math": {
        "name": "Math Agent",
        "url": "http://127.0.0.1:10011",  # A2A port 9011 + 1000
        "description": "Performs mathematical calculations"
    },
    "search": {
        "name": "Search Agent", 
        "url": "http://127.0.0.1:10013",  # A2A port 9013 + 1000
        "description": "Searches for information online"
    },
    "quote": {
        "name": "Quote Agent",
        "url": "http://127.0.0.1:10012",  # A2A port 9012 + 1000
        "description": "Provides inspirational quotes"
    },
    "llm": {
        "name": "LLM Agent",
        "url": "http://127.0.0.1:10014",  # A2A port 9014 + 1000
        "description": "General language model interactions"
    }
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Agent System - OpenAI API</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .agent-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .agent-card { border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #f9f9f9; }
        .agent-card h3 { margin-top: 0; color: #333; }
        .status-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
        .status-healthy { background-color: #4CAF50; }
        .status-error { background-color: #f44336; }
        .status-unknown { background-color: #ff9800; }
        .chat-section { margin-top: 30px; }
        .message-input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px; }
        .send-button { background: #007cba; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
        .send-button:hover { background: #005a85; }
        .response-area { background: #f0f0f0; padding: 15px; border-radius: 4px; min-height: 100px; margin-top: 15px; white-space: pre-wrap; }
        .timing-info { background: #e8f4f8; padding: 10px; border-left: 4px solid #007cba; margin: 10px 0; font-family: monospace; font-size: 14px; }
        .error-message { background: #ffebee; color: #c62828; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .loading { color: #666; font-style: italic; }
        select { padding: 8px; margin-right: 10px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Multi-Agent System - OpenAI Compatible API</h1>
        <p>This GUI uses standard HTTP requests to OpenAI-compatible endpoints, eliminating A2A protocol overhead.</p>
        
        <div class="agent-grid">
            {% for agent_id, agent in agents.items() %}
            <div class="agent-card">
                <h3>
                    <span class="status-indicator status-unknown" id="status-{{ agent_id }}"></span>
                    {{ agent.name }}
                </h3>
                <p>{{ agent.description }}</p>
                <p><strong>API URL:</strong> {{ agent.url }}</p>
                <p><strong>Status:</strong> <span id="status-text-{{ agent_id }}">Checking...</span></p>
            </div>
            {% endfor %}
        </div>
        
        <div class="chat-section">
            <h2>Chat with Agents</h2>
            <select id="agent-select">
                {% for agent_id, agent in agents.items() %}
                <option value="{{ agent_id }}">{{ agent.name }}</option>
                {% endfor %}
            </select>
            <br><br>
            
            <textarea class="message-input" id="message-input" placeholder="Enter your message here..." rows="3"></textarea>
            <br>
            <button class="send-button" onclick="sendMessage()">Send Message</button>
            <button class="send-button" onclick="testAllAgents()" style="background: #4CAF50;">Test All Agents</button>
            <button class="send-button" onclick="clearResponse()" style="background: #666;">Clear</button>
            
            <div class="response-area" id="response-area">Response will appear here...</div>
        </div>
    </div>

    <script>
        // Check agent health on page load
        window.onload = function() {
            checkAllAgentHealth();
        };
        
        async function checkAgentHealth(agentId, agentUrl) {
            const statusIndicator = document.getElementById(`status-${agentId}`);
            const statusText = document.getElementById(`status-text-${agentId}`);
            
            try {
                const response = await fetch(`${agentUrl}/health`, {
                    method: 'GET',
                    timeout: 5000
                });
                
                if (response.ok) {
                    const data = await response.json();
                    statusIndicator.className = 'status-indicator status-healthy';
                    statusText.textContent = 'Healthy';
                } else {
                    statusIndicator.className = 'status-indicator status-error';
                    statusText.textContent = `Error: ${response.status}`;
                }
            } catch (error) {
                statusIndicator.className = 'status-indicator status-error';
                statusText.textContent = 'Offline';
            }
        }
        
        async function checkAllAgentHealth() {
            const agents = {{ agents | tojson }};
            for (const [agentId, agent] of Object.entries(agents)) {
                await checkAgentHealth(agentId, agent.url);
            }
        }
        
        async function sendMessage() {
            const agentSelect = document.getElementById('agent-select');
            const messageInput = document.getElementById('message-input');
            const responseArea = document.getElementById('response-area');
            
            const selectedAgent = agentSelect.value;
            const message = messageInput.value.trim();
            
            if (!message) {
                alert('Please enter a message');
                return;
            }
            
            const agents = {{ agents | tojson }};
            const agentUrl = agents[selectedAgent].url;
            const agentName = agents[selectedAgent].name;
            
            responseArea.innerHTML = `<div class="loading">Sending message to ${agentName}...</div>`;
            
            const startTime = performance.now();
            
            try {
                const requestData = {
                    model: agentName,
                    messages: [
                        {role: "user", content: message}
                    ]
                };
                
                const response = await fetch(`${agentUrl}/v1/chat/completions`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                const endTime = performance.now();
                const responseTime = ((endTime - startTime) / 1000).toFixed(2);
                
                if (response.ok) {
                    const data = await response.json();
                    const assistantMessage = data.choices[0].message.content;
                    
                    responseArea.innerHTML = `
                        <div class="timing-info">✅ Response time: ${responseTime}s</div>
                        <strong>${agentName} Response:</strong><br>
                        ${assistantMessage}
                        
                        <div style="margin-top: 15px; font-size: 12px; color: #666;">
                        <strong>Raw Response:</strong><br>
                        ${JSON.stringify(data, null, 2)}
                        </div>
                    `;
                } else {
                    const errorText = await response.text();
                    responseArea.innerHTML = `
                        <div class="error-message">
                        <strong>Error ${response.status}:</strong><br>
                        ${errorText}
                        </div>
                        <div class="timing-info">⚠️ Failed after: ${responseTime}s</div>
                    `;
                }
            } catch (error) {
                const endTime = performance.now();
                const responseTime = ((endTime - startTime) / 1000).toFixed(2);
                
                responseArea.innerHTML = `
                    <div class="error-message">
                    <strong>Network Error:</strong><br>
                    ${error.message}
                    </div>
                    <div class="timing-info">❌ Failed after: ${responseTime}s</div>
                `;
            }
        }
        
        async function testAllAgents() {
            const responseArea = document.getElementById('response-area');
            responseArea.innerHTML = '<div class="loading">Testing all agents...</div>';
            
            const agents = {{ agents | tojson }};
            const testMessage = "Hello, please respond with your capabilities";
            let results = "🔍 Testing All Agents\\n\\n";
            
            for (const [agentId, agent] of Object.entries(agents)) {
                const startTime = performance.now();
                
                try {
                    const requestData = {
                        model: agent.name,
                        messages: [{role: "user", content: testMessage}]
                    };
                    
                    const response = await fetch(`${agent.url}/v1/chat/completions`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(requestData)
                    });
                    
                    const endTime = performance.now();
                    const responseTime = ((endTime - startTime) / 1000).toFixed(2);
                    
                    if (response.ok) {
                        const data = await response.json();
                        const message = data.choices[0].message.content;
                        results += `✅ ${agent.name} (${responseTime}s): ${message}\\n\\n`;
                    } else {
                        results += `❌ ${agent.name} (${responseTime}s): HTTP ${response.status}\\n\\n`;
                    }
                } catch (error) {
                    const endTime = performance.now();
                    const responseTime = ((endTime - startTime) / 1000).toFixed(2);
                    results += `❌ ${agent.name} (${responseTime}s): ${error.message}\\n\\n`;
                }
                
                // Update UI progressively
                responseArea.innerHTML = `<pre>${results}</pre>`;
            }
            
            results += "🏁 Testing complete!";
            responseArea.innerHTML = `<pre>${results}</pre>`;
        }
        
        function clearResponse() {
            document.getElementById('response-area').innerHTML = 'Response will appear here...';
        }
        
        // Allow Enter key to send message
        document.getElementById('message-input').addEventListener('keypress', function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main GUI page."""
    logger.info("Serving main GUI page")
    return render_template_string(HTML_TEMPLATE, agents=AGENTS)

@app.route('/api/agents')
def list_agents():
    """API endpoint to list available agents."""
    return jsonify(AGENTS)

@app.route('/api/health')
def health_check():
    """GUI health check."""
    return jsonify({
        "status": "healthy",
        "gui": "openai_compatible",
        "agents": AGENTS
    })

if __name__ == '__main__':
    print("Starting Multi-Agent GUI with OpenAI-compatible API support...")
    print("This GUI eliminates A2A protocol overhead by using standard HTTP requests.")
    print("")
    print("Agent API endpoints:")
    for agent_id, agent in AGENTS.items():
        print(f"  {agent['name']}: {agent['url']}")
    print("")
    print("GUI will be available at: http://127.0.0.1:8080")
    print("")
    
    app.run(host='127.0.0.1', port=8080, debug=False)
