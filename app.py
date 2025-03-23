import gradio as gr
import time
import re
from new_private_gpt import process_query

def generate_response(user_message, history):
    if not user_message.strip():
        bot_message = "Please enter a valid query."
        history.append((user_message, bot_message))
        return history, gr.update(value="")
    
    start = time.time()
    res = process_query(user_message)
    end = time.time()
    
    answer = res.get("result", "No answer generated")
    sources = ""
    if res.get("source_documents"):
        for i, doc in enumerate(res["source_documents"], 1):
            snippet = doc.page_content[:300]  # Truncate for brevity
            sources += f"\n\n**Source {i}:** *{doc.metadata.get('source','Unknown Source')}*\n{snippet}..."
    
    processing_time = end - start
    
    # Modified format: Answer first, then hidden sources that can be toggled
    bot_message = (
        f"**Answer:**\n{answer}\n\n"
        f"<sources>{sources}</sources>\n\n"
        f"*(Processed in {processing_time:.2f} seconds)*"
    )
    
    history.append((user_message, bot_message))
    return history, gr.update(value="")

# Custom CSS for centralized UI with collapsible sources
custom_css = """
/* Base styling */
:root {
    --bg-color: #171923;
    --text-color: #f5f6fa;
    --accent-color: #6c5ce7;
    --accent-hover: #5849d1;
    --border-color: #2c304d;
    --card-bg: #1f2235;
    --secondary-text: #a0a3bd;
    --input-bg: #242940;
    --shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    --success-color: #10b981;
    --success-hover: #059669;
}

body {
    background-color: var(--bg-color) !important;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif !important;
    color: var(--text-color) !important;
    margin: 0 !important;
    padding: 0 !important;
}

.gradio-container {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 auto !important;
    padding: 0 !important;
    background-color: var(--bg-color) !important;
}

/* Central container */
.central-container {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    min-height: 100vh !important;
    padding: 0 20px !important;
}

.central-content {
    width: 100% !important;
    max-width: 800px !important;
    margin: 0 auto !important;
}

/* Header styling */
.header {
    text-align: center !important;
    margin-bottom: 2rem !important;
}

.logo-container {
    display: flex !important;
    justify-content: center !important;
    margin-bottom: 1rem !important;
}

.logo-icon {
    font-size: 2.5rem !important;
    color: var(--accent-color) !important;
    margin-bottom: 0.5rem !important;
}

.app-title {
    font-size: 2rem !important;
    font-weight: 600 !important;
    color: var(--text-color) !important;
    margin: 0.75rem 0 !important;
    background: linear-gradient(90deg, #6c5ce7, #a29bfe) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

.app-description {
    max-width: 500px !important;
    margin: 0 auto 1.5rem auto !important;
    color: var(--secondary-text) !important;
    font-size: 0.95rem !important;
    line-height: 1.5 !important;
}

/* Examples section */
.examples-section {
    margin-bottom: 2rem !important;
}

.examples-title {
    text-align: center !important;
    font-size: 1.25rem !important;
    font-weight: 500 !important;
    margin-bottom: 1rem !important;
}

.examples-grid {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 0.75rem !important;
}

.example-btn {
    width: 100% !important;
    text-align: left !important;
    padding: 0.85rem 1rem !important;
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    font-size: 0.9rem !important;
    transition: all 0.2s ease !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

.example-btn:hover {
    background-color: var(--input-bg) !important;
    border-color: var(--accent-color) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 5px 15px rgba(108, 92, 231, 0.15) !important;
}

/* Chat container */
.chat-container {
    background-color: var(--card-bg) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    margin-bottom: 1.5rem !important;
    box-shadow: var(--shadow) !important;
    border: 1px solid var(--border-color) !important;
}

.chatbox {
    min-height: 400px !important;
    max-height: 50vh !important;
    overflow-y: auto !important;
    padding: 1rem !important;
    background-color: var(--card-bg) !important;
    border: none !important;
}

/* Sources styling */
.sources-hidden {
    display: none;
}

.sources-container {
    border-top: 1px dashed var(--border-color);
    padding-top: 15px;
    margin-top: 15px;
}

.sources-title {
    font-weight: 600;
    margin-bottom: 10px;
}

.source-item {
    background-color: rgba(255, 255, 255, 0.05);
    padding: 12px 15px;
    border-radius: 8px;
    margin-bottom: 10px;
}

.source-header {
    font-weight: 500;
    margin-bottom: 8px;
    color: var(--accent-color);
}

.source-content {
    font-size: 0.9rem;
    color: var(--secondary-text);
}

.view-sources-btn {
    display: inline-block;
    margin-top: 10px;
    padding: 6px 12px;
    background-color: transparent;
    border: 1px solid var(--border-color);
    color: var(--secondary-text);
    font-size: 0.85rem;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.view-sources-btn:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: var(--text-color);
    border-color: var(--accent-color);
}

/* Input area */
.input-container {
    background-color: var(--card-bg) !important;
    border-radius: 12px !important;
    border: 1px solid var(--border-color) !important;
    box-shadow: var(--shadow) !important;
    overflow: hidden !important;
}

.input-area {
    display: flex !important;
    align-items: center !important;
    padding: 0.5rem !important;
}

.input-box textarea {
    flex-grow: 1 !important;
    padding: 1rem !important;
    background-color: var(--input-bg) !important;
    color: var(--text-color) !important;
    border: none !important;
    border-radius: 8px !important;
    resize: none !important;
    font-size: 0.95rem !important;
    line-height: 1.5 !important;
    min-height: 60px !important;
    max-height: 150px !important;
}

.input-box textarea:focus {
    outline: none !important;
    box-shadow: 0 0 0 2px var(--accent-color) !important;
}

.input-box textarea::placeholder {
    color: var(--secondary-text) !important;
}

.send-btn {
    padding: 10px 16px !important;
    margin-left: 0.5rem !important;
    background-color: var(--accent-color) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 1rem !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

.send-btn:hover {
    background-color: var(--accent-hover) !important;
    transform: translateY(-2px) !important;
}

.send-btn:active {
    transform: translateY(0) !important;
}

.clear-btn {
    width: 100% !important;
    padding: 0.75rem 1rem !important;
    margin-top: 1rem !important;
    background-color: transparent !important;
    color: var(--secondary-text) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    font-size: 0.9rem !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

.clear-btn:hover {
    background-color: rgba(255, 255, 255, 0.05) !important;
    color: var(--text-color) !important;
}

/* Footer */
.footer {
    text-align: center !important;
    color: var(--secondary-text) !important;
    font-size: 0.8rem !important;
    margin-top: 2rem !important;
    margin-bottom: 1rem !important;
}

/* Message styling */
.message {
    max-width: none !important;
    margin: 0 0 0.5rem 0 !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Media queries for responsiveness */
@media (max-width: 768px) {
    .examples-grid {
        grid-template-columns: 1fr !important;
    }
    
    .app-title {
        font-size: 1.5rem !important;
    }
}
"""

# Create the Gradio app
with gr.Blocks(css=custom_css, title="Phoenixville Municipal Code Chat") as demo:
    with gr.Column(elem_classes="central-container"):
        with gr.Column(elem_classes="central-content"):
            # Header
            with gr.Column(elem_classes="header"):
                with gr.Column(elem_classes="logo-container"):
                    gr.HTML("""
                        <div class="logo-icon">⚖️</div>
                    """)
                
                gr.HTML("""
                    <h1 class="app-title">Phoenixville Municipal Code Chat</h1>
                    <p class="app-description">
                        Ask questions about Phoenixville's municipal code and get accurate answers backed by
                        official documentation and references.
                    </p>
                """)
            
            # Examples Section
            with gr.Column(elem_classes="examples-section", visible=True) as examples_container:
                gr.HTML("""
                    <div class="examples-title">Try an example</div>
                """)
                
                with gr.Column(elem_classes="examples-grid"):
                    example1 = gr.Button("What are the rules for parking overnight?", elem_classes="example-btn")
                    example2 = gr.Button("What permits do I need for home renovations?", elem_classes="example-btn")
                    example3 = gr.Button("What are the noise ordinance hours?", elem_classes="example-btn")
                    example4 = gr.Button("How do I appeal a zoning decision?", elem_classes="example-btn")
            
            # Chat area
            with gr.Column(elem_classes="chat-container"):
                chatbot = gr.Chatbot(
                    elem_id="chatbox",
                    elem_classes="chatbox",
                    height=450,
                    show_label=False
                )
            
            # Input area
            with gr.Column(elem_classes="input-container"):
                with gr.Row(elem_classes="input-area"):
                    msg = gr.Textbox(
                        placeholder="Ask about Phoenixville Municipal Code...",
                        label="",
                        elem_id="input-box",
                        elem_classes="input-box",
                        lines=2
                    )
                    submit_btn = gr.Button("→", elem_classes="send-btn")
                
                clear_btn = gr.Button("Clear conversation", elem_classes="clear-btn")
            
            # Footer
            with gr.Column(elem_classes="footer"):
                gr.HTML("""
                    <div>Powered by PrivateGPT • Phoenixville Municipal Code Database • Last Updated March 2025</div>
                """)
    
    # Initialize state
    chat_state = gr.State([])
    
    # Handle example button clicks
    def use_example(example_text, history):
        return example_text
    
    example1.click(use_example, [example1, chat_state], [msg])
    example2.click(use_example, [example2, chat_state], [msg])
    example3.click(use_example, [example3, chat_state], [msg])
    example4.click(use_example, [example4, chat_state], [msg])
    
    # Handle message submission
    def submit_message(message, history):
        if message.strip() == "":
            return history, ""
        
        # Check if it's the first message to hide examples
        history_length = len(history)
        result = generate_response(message, history)
        
        return result
    
    msg.submit(submit_message, [msg, chat_state], [chatbot, msg])
    submit_btn.click(submit_message, [msg, chat_state], [chatbot, msg])
    
    # Handle clear button
    def clear_chat():
        return [], []
    
    clear_btn.click(clear_chat, [], [chatbot, chat_state])

    # Add JavaScript for collapsible sources and other UI enhancements
    demo.load(js="""
    function setupCollapsibleSources() {
        // Function to process messages and handle sources
        function processMessages() {
            document.querySelectorAll('.message.bot').forEach(function(message) {
                // Find source elements that haven't been processed yet
                const sourceElements = message.querySelectorAll('sources:not(.processed)');
                
                sourceElements.forEach(function(sourceElement) {
                    // Mark as processed
                    sourceElement.classList.add('processed');
                    
                    // Get the source content
                    const sourceContent = sourceElement.innerHTML;
                    
                    // Create a container for the sources
                    const sourcesContainer = document.createElement('div');
                    sourcesContainer.className = 'sources-container sources-hidden';
                    
                    // Create formatted sources content
                    let formattedContent = '<div class="sources-title">Sources</div>';
                    
                    // Parse and format sources using regex
                    const sourcePattern = /\*\*Source (\d+):\*\* \*(.*?)\*\n([\s\S]*?)(?=\n\n\*\*Source|\n\n\*\(|$)/g;
                    let match;
                    let sourceHtml = '';
                    
                    while ((match = sourcePattern.exec(sourceContent)) !== null) {
                        sourceHtml += `
                            <div class="source-item">
                                <div class="source-header">Source ${match[1]}: ${match[2]}</div>
                                <div class="source-content">${match[3]}</div>
                            </div>
                        `;
                    }
                    
                    sourcesContainer.innerHTML = formattedContent + sourceHtml;
                    
                    // Create "View Sources" button
                    const viewSourcesBtn = document.createElement('button');
                    viewSourcesBtn.className = 'view-sources-btn';
                    viewSourcesBtn.textContent = 'View Sources';
                    viewSourcesBtn.onclick = function() {
                        if (sourcesContainer.classList.contains('sources-hidden')) {
                            sourcesContainer.classList.remove('sources-hidden');
                            viewSourcesBtn.textContent = 'Hide Sources';
                        } else {
                            sourcesContainer.classList.add('sources-hidden');
                            viewSourcesBtn.textContent = 'View Sources';
                        }
                    };
                    
                    // Replace the original source element
                    sourceElement.replaceWith(viewSourcesBtn, sourcesContainer);
                });
            });
        }
        
        // Initial processing
        processMessages();
        
        // Set up an observer to watch for new messages
        const chatbox = document.getElementById('chatbox');
        if (chatbox) {
            const observer = new MutationObserver(function(mutations) {
                processMessages();
            });
            
            observer.observe(chatbox, {
                childList: true,
                subtree: true
            });
        }
    }
    
    // Run when the page loads
    window.addEventListener('load', setupCollapsibleSources);
    """)

# Launch with custom favicon
demo.launch(favicon_path="https://www.phoenixville.org/favicon.ico", share=False)

