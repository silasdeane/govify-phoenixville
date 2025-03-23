// Phoenixville AI Map Integration
document.addEventListener('DOMContentLoaded', function() {
    console.log("Map integration script loaded");
    
    // Function to check for map portal tags in responses
    const checkForMapPortal = function(data) {
      if (data && data.result && data.result.includes('<map_portal>')) {
        // Extract the message text
        const messageText = data.result.match(/<map_portal>(.*?)<\/map_portal>/)[1];
        
        // Get map data if available
        const mapData = data.map_data || {
          lat: 40.1308, 
          lng: -75.5146, 
          zoom: 14, 
          layer: 'locations'
        };
        
        // Create the assistant message with iframe
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        messageDiv.innerHTML = `<p>${messageText}</p>
          <div style="margin-top: 16px;">
            <iframe src="/static/map.html?lat=${mapData.lat}&lng=${mapData.lng}&zoom=${mapData.zoom}&layer=${mapData.layer}" 
                  width="100%" 
                  height="600" 
                  style="border: none; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);">
            </iframe>
          </div>`;
        
        // Add to chat container
        document.getElementById('chat-container').appendChild(messageDiv);
        document.getElementById('chat-container').scrollTop = document.getElementById('chat-container').scrollHeight;
        
        return true; // Indicates we handled this response
      }
      return false; // Not a map portal response
    };
    
    // Add map example to examples section
    const examplesGrid = document.querySelector('.examples-grid');
    if (examplesGrid) {
      const mapExample = document.createElement('div');
      mapExample.className = 'example-card';
      mapExample.setAttribute('data-example', 'Show me a map of Phoenixville');
      mapExample.innerHTML = `
        <div class="example-card-icon">🗺️</div>
        <div class="example-card-text">Show me a map of Phoenixville</div>
      `;
      examplesGrid.appendChild(mapExample);
      
      // Add event listener to the example card
      mapExample.addEventListener('click', function() {
        document.getElementById('user-input').value = this.getAttribute('data-example');
        document.getElementById('user-input').focus();
      });
    }
    
    // Store the original fetch function
    const originalFetch = window.fetch;
    
    // Override fetch to intercept map requests
    window.fetch = async function(url, options) {
      // Only intercept POST requests to the /query endpoint
      if (url === '/query' && options && options.method === 'POST') {
        try {
          // Make the original request
          const response = await originalFetch(url, options);
          const clone = response.clone();
          
          // Try to parse the JSON
          const data = await clone.json();
          
          // Check if this is a map portal response
          if (checkForMapPortal(data)) {
            // If we handled it as a map portal, return modified response
            // that will prevent the default message handling
            return new Response(JSON.stringify({
              result: "Map displayed",
              processing_time: 0.1,
              source_documents: []
            }), {
              status: 200,
              headers: {
                'Content-Type': 'application/json'
              }
            });
          }
          
          // If not a map portal, return the original response
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