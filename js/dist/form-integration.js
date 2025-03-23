// Phoenixville AI Permit Form Integration
document.addEventListener('DOMContentLoaded', function() {
    console.log("Permit form integration script loaded");
    
    // Function to check for form portal tags in responses
    const checkForFormPortal = function(data) {
      if (data && data.result && data.result.includes('<form_portal>')) {
        // Extract the message text and form details
        const portalContent = data.result.match(/<form_portal>(.*?)<\/form_portal>/)[1];
        const [message, formId, formTitle] = portalContent.split('|');
        
        // Get form data if available
        const formData = data.form_data || {
          form_id: formId,
          title: formTitle,
          description: "Permit application form"
        };
        
        // Create a container for the form
        const formContainer = document.createElement('div');
        formContainer.className = 'message assistant-message';
        
        // Add a message and iframe to display the form
        formContainer.innerHTML = `
          <p>${message}</p>
          <div style="margin-top: 16px;">
            <iframe src="/static/forms/${formData.form_id}.html" 
                   width="100%" 
                   height="600" 
                   style="border: none; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);">
            </iframe>
          </div>
          <div style="margin-top: 12px;">
            <button class="form-action-btn download-btn" data-form="${formData.form_id}">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
                <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
              </svg>
              Download PDF
            </button>
            <button class="form-action-btn print-btn" data-form="${formData.form_id}">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M2.5 8a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1z"/>
                <path d="M5 1a2 2 0 0 0-2 2v2H2a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h1v1a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-1h1a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-1V3a2 2 0 0 0-2-2H5zM4 3a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2H4V3zm1 5a2 2 0 0 0-2 2v1H2a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v-1a2 2 0 0 0-2-2H5zm7 2v3a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1z"/>
              </svg>
              Print Form
            </button>
          </div>
        `;
        
        // Add to chat container
        document.getElementById('chat-container').appendChild(formContainer);
        document.getElementById('chat-container').scrollTop = document.getElementById('chat-container').scrollHeight;
        
        // Add event listeners to the buttons
        formContainer.querySelector('.download-btn').addEventListener('click', function() {
          const formId = this.getAttribute('data-form');
          window.open(`/static/forms/${formId}.pdf`, '_blank');
        });
        
        formContainer.querySelector('.print-btn').addEventListener('click', function() {
          const iframe = formContainer.querySelector('iframe');
          iframe.contentWindow.print();
        });
        
        return true; // Indicates we handled this response
      }
      return false; // Not a form portal response
    };
    
    // Add permit example to examples section
    const examplesGrid = document.querySelector('.examples-grid');
    if (examplesGrid) {
      const permitExample = document.createElement('div');
      permitExample.className = 'example-card';
      permitExample.setAttribute('data-example', 'How do I apply for a deck permit?');
      permitExample.innerHTML = `
        <div class="example-card-icon">📋</div>
        <div class="example-card-text">How do I apply for a deck permit?</div>
      `;
      examplesGrid.appendChild(permitExample);
      
      // Add event listener to the example card
      permitExample.addEventListener('click', function() {
        document.getElementById('user-input').value = this.getAttribute('data-example');
        document.getElementById('user-input').focus();
      });
    }
    
    // Add CSS for form action buttons
    const style = document.createElement('style');
    style.textContent = `
      .form-action-btn {
        padding: 8px 16px;
        margin-right: 8px;
        border-radius: 4px;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid;
        background-color: transparent;
      }
      
      .form-action-btn.download-btn {
        color: #5686f5;
        border-color: #5686f5;
      }
      
      .form-action-btn.download-btn:hover {
        background-color: rgba(86, 134, 245, 0.1);
      }
      
      .form-action-btn.print-btn {
        color: #43b581;
        border-color: #43b581;
      }
      
      .form-action-btn.print-btn:hover {
        background-color: rgba(67, 181, 129, 0.1);
      }
    `;
    document.head.appendChild(style);
    
    // Store the original fetch function
    const originalFetch = window.fetch;
    
    // Override fetch to intercept form requests
    window.fetch = async function(url, options) {
      // Only intercept POST requests to the /query endpoint
      if (url === '/query' && options && options.method === 'POST') {
        try {
          // Make the original request
          const response = await originalFetch(url, options);
          const clone = response.clone();
          
          // Try to parse the JSON
          const data = await clone.json();
          
          // Check if this is a form portal response
          if (checkForFormPortal(data)) {
            // If we handled it as a form portal, return modified response
            // that will prevent the default message handling
            return new Response(JSON.stringify({
              result: "Permit form displayed",
              processing_time: 0.1,
              source_documents: []
            }), {
              status: 200,
              headers: {
                'Content-Type': 'application/json'
              }
            });
          }
          
          // If not a form portal, return the original response
          return response;
        } catch (e) {
          console.error("Error in fetch intercept:", e);
          // Fall back to original fetch if there's an error
          return originalFetch(url, options);
        }
      }
      
      // For all other requests, use the original fetch
      return originalFetch(url, options);
    };
});