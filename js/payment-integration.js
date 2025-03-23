// Phoenixville AI Payment Portal Integration
document.addEventListener('DOMContentLoaded', function() {
    console.log("Payment integration script loaded");
    
    // Payment keywords that will trigger the portal
    const paymentTriggers = [
      'pay water bill',
      'water bill payment',
      'pay my water',
      'how do i pay my water',
      'pay utility bill',
      'water payment'
    ];
    
    // Track if we've already handled a payment request
    let paymentRequestHandled = false;
    
    // Function to check if user message contains payment keywords
    function isPaymentRequest(message) {
      message = message.toLowerCase();
      return paymentTriggers.some(trigger => message.includes(trigger));
    }
    
    // Function to display the payment portal
    function showPaymentPortal(userQuery) {
      // If we've already handled a payment request, don't do it again
      if (paymentRequestHandled) {
        console.log("Payment request already handled, skipping");
        return false;
      }
      
      console.log("Showing payment portal");
      paymentRequestHandled = true;
      
      // Note: We no longer add the user message here because it's already added by sendMessage
      
      // Create a container for the payment portal
      const portalContainer = document.createElement('div');
      portalContainer.className = 'message assistant-message';
      
      // Add a message before showing the portal
      portalContainer.innerHTML = `
        <p>I can help you pay your water bill right here. Please use the secure payment form below:</p>
        <div style="margin-top: 16px;">
          <iframe src="/static/payment-portal.html" width="100%" height="600" style="border: none; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);"></iframe>
        </div>
      `;
      
      // Add to chat container
      document.getElementById('chat-container').appendChild(portalContainer);
      document.getElementById('chat-container').scrollTop = document.getElementById('chat-container').scrollHeight;
      
      // Reset the handled flag after a delay to allow for new payment requests
      setTimeout(() => {
        paymentRequestHandled = false;
      }, 2000);
      
      return true;
    }
    
    // Add water bill payment example to examples section
    const examplesGrid = document.querySelector('.examples-grid');
    if (examplesGrid) {
      const paymentExample = document.createElement('div');
      paymentExample.className = 'example-card';
      paymentExample.setAttribute('data-example', 'How do I pay my water bill?');
      paymentExample.innerHTML = `
        <div class="example-card-icon">💧</div>
        <div class="example-card-text">How do I pay my water bill?</div>
      `;
      examplesGrid.appendChild(paymentExample);
      
      // Add event listener to the example card
      paymentExample.addEventListener('click', function() {
        document.getElementById('user-input').value = this.getAttribute('data-example');
        document.getElementById('user-input').focus();
      });
    }
  
    // We're going to modify ONLY the fetch intercept to avoid conflicting with sendMessage's immediate display
    const originalFetch = window.fetch;
    window.fetch = async function(url, options) {
      // Only intercept POST requests to the /query endpoint
      if (url === '/query' && options && options.method === 'POST') {
        try {
          // Parse the request body
          const body = JSON.parse(options.body);
          const query = body.query;
          
          // Check if it's a payment request
          if (isPaymentRequest(query)) {
            console.log("Payment request detected in fetch intercept!");
            
            // Note: We don't need to add the user message or hide loading here
            // This happens after sendMessage already displayed the user message
            
            // Only handle it if we haven't already
            if (!paymentRequestHandled) {
              // Short timeout to ensure the user message is displayed first
              setTimeout(() => {
                // Hide any loading indicators
                const activeIndicator = document.getElementById('active-loading-indicator');
                if (activeIndicator) {
                  activeIndicator.remove();
                }
                
                // Show the payment portal
                showPaymentPortal(query);
              }, 100);
            }
            
            // Return a mock response
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve({
                result: "Payment portal displayed",
                processing_time: 0,
                source_documents: []
              })
            });
          }
        } catch (e) {
          console.error("Error in fetch intercept:", e);
        }
      }
      
      // Otherwise, proceed with the original fetch
      return originalFetch.apply(this, arguments);
    };
    
    // Reset the flag when starting a new chat
    const newChatBtn = document.getElementById('new-chat-btn');
    if (newChatBtn) {
      const originalNewChatClick = newChatBtn.onclick;
      newChatBtn.onclick = function(event) {
        // Reset the flag
        paymentRequestHandled = false;
        
        // Call the original handler
        if (originalNewChatClick) {
          return originalNewChatClick.call(this, event);
        }
      };
    }
  });