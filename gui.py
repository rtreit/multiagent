from flask import Flask, render_template_string, request, jsonify
import requests
import json

AGENT_PORTS = {
    "Math Agent": 9011,
    "Quote Agent": 9012,
    "Search Agent": 9013,
}

HTML = """<!doctype html>
<html>
<head>
    <title>Multi-Agent Chat</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .controls { margin-bottom: 20px; }
        select, input, button { padding: 8px; margin: 5px; font-size: 14px; }
        input[type="text"] { width: 400px; }
        button { background-color: #007cba; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #005a87; }
        .response { 
            background-color: #f5f5f5; 
            border: 1px solid #ddd; 
            padding: 15px; 
            margin-top: 20px; 
            border-radius: 5px;
            white-space: pre-wrap;
            min-height: 100px;
        }
        .loading { color: #666; font-style: italic; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Multi-Agent Chat Interface</h1>
        
        <div class="controls">
            <label for="agent">Select Agent:</label>
            <select id="agent">
                {% for name in agents %}<option value="{{name}}">{{name}}</option>{% endfor %}
            </select>
            
            <br><br>
            
            <label for="msg">Message:</label>
            <input id="msg" type="text" placeholder="Enter your message..." onkeypress="if(event.key==='Enter') send()"/>
            <button onclick="send()">Send</button>
        </div>
        
        <div id="response" class="response">
            Select an agent and enter a message to start chatting...
        </div>
    </div>

    <script>
        async function send() {
            const agent = document.getElementById('agent').value;
            const msg = document.getElementById('msg').value.trim();
            const responseDiv = document.getElementById('response');
            
            if (!msg) {
                responseDiv.innerHTML = '<span class="error">Please enter a message</span>';
                return;
            }
            
            responseDiv.innerHTML = '<span class="loading">Sending message to ' + agent + '...</span>';
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        agent: agent,
                        message: msg
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    responseDiv.innerHTML = 
                        '<strong>Agent:</strong> ' + agent + '\\n' +
                        '<strong>Input:</strong> ' + msg + '\\n' +
                        '<strong>Response:</strong> ' + result.response;
                } else {
                    responseDiv.innerHTML = '<span class="error">Error: ' + result.error + '</span>';
                }
                
            } catch (error) {
                responseDiv.innerHTML = '<span class="error">Failed to send message: ' + error.message + '</span>';
            }
        }
    </script>
</body>
</html>
"""

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string(HTML, agents=AGENT_PORTS.keys())

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    agent = data.get('agent')
    text = data.get('message', '')
    
    if agent not in AGENT_PORTS:
        return jsonify({'success': False, 'error': f'Unknown agent: {agent}'})
    
    if not text.strip():
        return jsonify({'success': False, 'error': 'Message cannot be empty'})
    
    # GUI should communicate with agents using A2A client, just like the tests do
    # This is the proper way for external clients to communicate with A2A agents
    url = f"http://localhost:{AGENT_PORTS[agent]}"
    
    try:
        # First, check if the agent is responding
        health_response = requests.get(url, timeout=5)
        if health_response.status_code != 200:
            return jsonify({
                'success': False, 
                'error': f'Agent {agent} is not responding (HTTP {health_response.status_code})'
            })
        
        # Use A2A client to send message (this is how external clients communicate with agents)
        from python_a2a.client import A2AClient
        from python_a2a.models import Message, TextContent, MessageRole
        
        client = A2AClient(url)
        message = Message(content=TextContent(text=text), role=MessageRole.USER)
        
        response = client.send_message(message)
        
        return jsonify({
            'success': True, 
            'response': response.content.text,
            'agent': agent
        })
            
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'Request timed out'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': f'Could not connect to {agent}. Is the agent running?'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'})

if __name__ == '__main__':
    app.run(port=8000, debug=True)
