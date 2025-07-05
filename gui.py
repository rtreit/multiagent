from flask import Flask, render_template_string, request, Response, stream_with_context
import asyncio
from python_a2a.client.streaming import StreamingClient
from python_a2a.models import Message, TextContent, MessageRole

AGENT_PORTS = {
    "Math Agent": 9011,
    "Quote Agent": 9012,
    "Search Agent": 9013,
}

HTML = """<!doctype html>
<title>Multi-Agent Chat</title>
<select id=agent>
{% for name in agents %}<option value="{{name}}">{{name}}</option>{% endfor %}
</select>
<input id=msg size=60 placeholder="Enter message"/>
<button onclick="send()">Send</button>
<pre id=log></pre>
<script>
function send(){
  const agent=document.getElementById('agent').value;
  const msg=document.getElementById('msg').value;
  const log=document.getElementById('log');
  log.textContent='';
  const es=new EventSource(`/chat?agent=${encodeURIComponent(agent)}&message=${encodeURIComponent(msg)}`);
  es.onmessage=e=>{ log.textContent += e.data + "\n"; };
}
</script>
"""

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string(HTML, agents=AGENT_PORTS.keys())

@app.route('/chat')
def chat():
    agent = request.args.get('agent')
    text = request.args.get('message', '')
    if agent not in AGENT_PORTS:
        return 'unknown agent', 400
    url = f"http://localhost:{AGENT_PORTS[agent]}/a2a"

    async def astream():
        client = StreamingClient(url)
        message = Message(content=TextContent(text=text), role=MessageRole.USER)
        async for chunk in client.stream_response(message):
            if isinstance(chunk, dict):
                yield chunk.get('content', str(chunk))
            else:
                yield chunk

    def generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        agen = astream()
        try:
            while True:
                chunk = loop.run_until_complete(agen.__anext__())
                yield f"data: {chunk}\n\n"
        except StopAsyncIteration:
            pass
        finally:
            loop.close()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(port=8000, debug=True)
