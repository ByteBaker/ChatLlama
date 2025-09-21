        // Global state
        let currentChatId = null;
        let chats = [];
        let isGenerating = false;

        // DOM elements
        const messagesContainer = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const chatList = document.getElementById('chatList');
        const newChatBtn = document.getElementById('newChatBtn');
        console.log('newChatBtn element:', newChatBtn); // Debug
        const emptyState = document.getElementById('emptyState');
        const chatTitle = document.getElementById('chatTitle');
        const modelStatus = document.getElementById('modelStatus');

        // Initialize
        loadChatList();

        // Event listeners
        newChatBtn.addEventListener('click', function() {
            console.log('New Chat button clicked!'); // Debug
            createNewChat();
        });
        sendButton.addEventListener('click', sendMessage);

        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });

        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        async function loadChatList() {
            try {
                const response = await fetch('/chats');
                const data = await response.json();
                chats = data.chats || [];
                renderChatList();
            } catch (error) {
                console.error('Failed to load chat list:', error);
            }
        }

        function renderChatList() {
            chatList.innerHTML = '';

            if (chats.length === 0) {
                chatList.innerHTML = '<div style="padding: 1rem; text-align: center; color: #8e8ea0;">No chats yet</div>';
                return;
            }

            chats.forEach(chat => {
                const chatItem = document.createElement('div');
                chatItem.className = 'chat-item';
                chatItem.dataset.chatId = chat.id;

                if (chat.id === currentChatId) {
                    chatItem.classList.add('active');
                }

                const date = new Date(chat.updated_at).toLocaleDateString();

                chatItem.innerHTML = `
                    <div>
                        <div class="chat-title">${chat.title}</div>
                        <div class="chat-date">${date}</div>
                    </div>
                    <button class="delete-chat-btn" onclick="deleteChat('${chat.id}')" title="Delete chat">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6h14ZM10 11v6M14 11v6"/>
                        </svg>
                    </button>
                `;

                chatItem.addEventListener('click', (e) => {
                    if (!e.target.closest('.delete-chat-btn')) {
                        selectChat(chat.id, chat.title);
                    }
                });

                chatList.appendChild(chatItem);
            });
        }

        async function selectChat(chatId, title) {
            if (chatId === currentChatId) return;

            currentChatId = chatId;
            chatTitle.textContent = title;

            // Update active chat in sidebar
            document.querySelectorAll('.chat-item').forEach(item => {
                item.classList.toggle('active', item.dataset.chatId === chatId);
            });

            // Load chat messages
            await loadChatMessages(chatId);

            // Hide empty state
            emptyState.style.display = 'none';
            messageInput.focus();
        }

        async function loadChatMessages(chatId) {
            try {
                const response = await fetch(`/chat/${chatId}`);
                const data = await response.json();

                messagesContainer.innerHTML = '';

                data.messages.forEach(message => {
                    addMessageToUI(message.role, message.content);
                });

                scrollToBottom();

                // Load memory stats
                const memoryResponse = await fetch(`/memory-stats/${chatId}`);
                const memoryData = await memoryResponse.json();
                if (memoryData.memory_stats) {
                    updateMemoryDisplay(memoryData.memory_stats);
                }

            } catch (error) {
                console.error('Failed to load chat messages:', error);
                addErrorMessage('Failed to load chat messages');
            }
        }

        function createNewChat() {
            console.log('createNewChat called'); // Debug
            // Clear current chat display
            currentChatId = null;
            currentChatTitle = '✨ New Chat';
            chatTitle.textContent = currentChatTitle;
            messagesContainer.innerHTML = `
                <div class="empty-state" style="border: 2px dashed #555; border-radius: 12px; padding: 2rem; margin: 1rem; background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);">
                    <h2 style="color: #10a37f; margin-bottom: 1rem;">✨ New Chat Ready</h2>
                    <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">Type your first message below to start this conversation.</p>
                    <p style="color: #8e8ea0; font-size: 0.9rem;">This chat will have its own memory and context.</p>
                </div>
            `;

            // Clear memory display
            updateMemoryDisplay({facts: 0, preferences: 0, experiences: 0, topics: 0});

            // Remove active state from all chat items
            const chatItems = document.querySelectorAll('.chat-item');
            chatItems.forEach(item => item.classList.remove('active'));

            // Focus on input
            messageInput.focus();
            console.log('createNewChat completed, currentChatId:', currentChatId); // Debug
        }

        async function createNewChatWithMessage(message) {
            // Clear the empty state
            messagesContainer.innerHTML = '';

            // Add user message to UI
            addMessageToUI('user', message);
            messageInput.value = '';
            messageInput.style.height = 'auto';

            isGenerating = true;
            sendButton.disabled = true;
            modelStatus.textContent = 'Creating new chat...';

            try {
                const response = await fetch('/new-chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message.trim() })
                });

                const data = await response.json();

                if (data.error) {
                    addErrorMessage(data.error);
                } else {
                    // Add new chat to list
                    const newChat = {
                        id: data.chat_id,
                        title: data.title,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString()
                    };

                    chats.unshift(newChat);
                    renderChatList();

                    // Select the new chat
                    selectChat(data.chat_id, data.title);

                    // Add assistant response to UI
                    addMessageToUI('assistant', data.response, data.memories_added || 0);

                    updateMemoryDisplay(data.memory_stats);
                }
            } catch (error) {
                addErrorMessage('Failed to create new chat: ' + error.message);
            } finally {
                isGenerating = false;
                sendButton.disabled = false;
                modelStatus.textContent = 'Llama 3 8B Q4_K_M Ready';
            }
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message || isGenerating) return;

            // If no current chat, this is a new chat creation
            if (!currentChatId) {
                await createNewChatWithMessage(message);
                return;
            }

            // Add user message to UI
            addMessageToUI('user', message);
            messageInput.value = '';
            messageInput.style.height = 'auto';

            // Add assistant message placeholder for streaming
            const assistantMessageId = addStreamingMessagePlaceholder();

            isGenerating = true;
            sendButton.disabled = true;
            modelStatus.textContent = 'Generating...';

            try {
                console.log('Starting streaming request to /chat-stream'); // Debug
                const response = await fetch('/chat-stream', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        chat_id: currentChatId
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                // Handle streaming response
                console.log('Setting up streaming reader'); // Debug
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let fullResponse = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        console.log('Stream completed, done=true'); // Debug
                        break;
                    }

                    const chunk = decoder.decode(value, { stream: true });
                    buffer += chunk;
                    console.log('Received chunk:', chunk); // Debug - show full chunk

                    // Process complete lines
                    while (buffer.includes('\n\n')) {
                        const doubleNewlineIndex = buffer.indexOf('\n\n');
                        const line = buffer.substring(0, doubleNewlineIndex).trim();
                        buffer = buffer.substring(doubleNewlineIndex + 2);

                        console.log('Processing complete line:', line); // Debug
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            console.log('Extracted data:', data); // Debug
                            if (data === '[DONE]') {
                                console.log('Stream completed with [DONE]'); // Debug
                                return; // Exit the function completely
                            }
                            try {
                                const parsed = JSON.parse(data);
                                console.log('Parsed JSON:', parsed); // Debug
                                if (parsed.token) {
                                    console.log('Received token:', parsed.token); // Debug
                                    fullResponse += parsed.token;
                                    updateStreamingMessage(assistantMessageId, fullResponse);
                                    scrollToBottom(); // Scroll as tokens come in
                                } else if (parsed.memories_added !== undefined) {
                                    console.log('Received final metadata'); // Debug
                                    // Final response with metadata
                                    finalizeStreamingMessage(assistantMessageId, parsed.memories_added);
                                    updateMemoryDisplay(parsed.memory_stats);
                                    scrollToBottom();
                                }
                            } catch (e) {
                                console.error('Failed to parse streaming data:', e, 'Data was:', data);
                            }
                        }
                    }
                }

                // Update chat in sidebar (move to top)
                const chatIndex = chats.findIndex(c => c.id === currentChatId);
                if (chatIndex > -1) {
                    const chat = chats.splice(chatIndex, 1)[0];
                    chat.updated_at = new Date().toISOString();
                    chats.unshift(chat);
                    renderChatList();
                }

            } catch (error) {
                removeMessage(assistantMessageId);
                addErrorMessage('Connection error: ' + error.message);
            } finally {
                isGenerating = false;
                sendButton.disabled = false;
                modelStatus.textContent = 'Llama 3 8B Q4_K_M Ready';
                messageInput.focus();
            }
        }

        async function deleteChat(chatId) {
            if (!confirm('Are you sure you want to delete this chat?')) return;

            try {
                const response = await fetch(`/chat/${chatId}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    // Remove from chats array
                    chats = chats.filter(c => c.id !== chatId);
                    renderChatList();

                    // If this was the current chat, clear the main area
                    if (chatId === currentChatId) {
                        currentChatId = null;
                        chatTitle.textContent = 'Llama 3 8B Multi-Chat';
                        messagesContainer.innerHTML = '';
                        emptyState.style.display = 'flex';
                    }
                } else {
                    alert('Failed to delete chat');
                }
            } catch (error) {
                alert('Error deleting chat: ' + error.message);
            }
        }

        function addMessageToUI(type, content, memoriesAdded = 0) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            messageDiv.id = `msg-${Date.now()}-${Math.random()}`;

            const avatar = type === 'user' ? '👤' : '🦙';

            let memoryIndicator = '';
            if (type === 'assistant' && memoriesAdded > 0) {
                memoryIndicator = `<div class="memory-indicator">🧠 +${memoriesAdded} memories learned</div>`;
            }

            // Determine if message is short (less than 50 characters and no line breaks)
            const isShort = content.length < 50 && !content.includes('\n');
            const shortClass = isShort ? ' short' : '';

            messageDiv.innerHTML = `
                <div class="avatar">${avatar}</div>
                <div>
                    <div class="message-content${shortClass}">${formatMessage(content)}</div>
                    ${memoryIndicator}
                </div>
            `;

            messagesContainer.appendChild(messageDiv);
            scrollToBottom();
            return messageDiv.id;
        }

        function addStreamingMessagePlaceholder() {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';
            messageDiv.id = `stream-${Date.now()}`;

            messageDiv.innerHTML = `
                <div class="avatar">🦙</div>
                <div>
                    <div class="message-content" data-streaming="true">
                        <span class="cursor">|</span>
                    </div>
                </div>
            `;

            messagesContainer.appendChild(messageDiv);
            scrollToBottom();
            return messageDiv.id;
        }

        function updateStreamingMessage(messageId, content) {
            console.log('updateStreamingMessage called with:', messageId, content.substring(0, 50) + '...'); // Debug
            const messageElement = document.getElementById(messageId);
            if (messageElement) {
                console.log('Found message element, updating content'); // Debug
                const contentDiv = messageElement.querySelector('.message-content');
                contentDiv.innerHTML = formatMessage(content) + '<span class="cursor">|</span>';
                scrollToBottom();
            } else {
                console.log('Message element not found:', messageId); // Debug
            }
        }

        function finalizeStreamingMessage(messageId, memoriesAdded = 0) {
            const messageElement = document.getElementById(messageId);
            if (messageElement) {
                const contentDiv = messageElement.querySelector('.message-content');
                // Remove cursor
                const finalContent = contentDiv.innerHTML.replace('<span class="cursor">|</span>', '');
                contentDiv.innerHTML = finalContent;
                contentDiv.removeAttribute('data-streaming');

                // Check if the final content is short and apply short class
                const textContent = contentDiv.textContent || contentDiv.innerText;
                if (textContent.length < 50 && !textContent.includes('\n')) {
                    contentDiv.classList.add('short');
                }

                // Add memory indicator if any memories were added
                if (memoriesAdded > 0) {
                    const memoryIndicator = document.createElement('div');
                    memoryIndicator.className = 'memory-indicator';
                    memoryIndicator.innerHTML = `🧠 +${memoriesAdded} memories learned`;
                    messageElement.querySelector('div:last-child').appendChild(memoryIndicator);
                }
            }
        }

        function addThinkingMessage() {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';
            messageDiv.id = `thinking-${Date.now()}`;

            messageDiv.innerHTML = `
                <div class="avatar">🦙</div>
                <div>
                    <div class="message-content thinking">
                        <span>Thinking</span>
                        <div class="thinking-dots">
                            <div class="thinking-dot"></div>
                            <div class="thinking-dot"></div>
                            <div class="thinking-dot"></div>
                        </div>
                    </div>
                </div>
            `;

            messagesContainer.appendChild(messageDiv);
            scrollToBottom();
            return messageDiv.id;
        }

        function addErrorMessage(error) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';

            messageDiv.innerHTML = `
                <div class="avatar">⚠️</div>
                <div>
                    <div class="message-content error-message">
                        Error: ${error}
                    </div>
                </div>
            `;

            messagesContainer.appendChild(messageDiv);
            scrollToBottom();
        }

        function removeMessage(messageId) {
            const messageElement = document.getElementById(messageId);
            if (messageElement) {
                messageElement.remove();
            }
        }

        function formatMessage(text) {
            if (!text) return '';

            // First, escape HTML to prevent XSS
            let html = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#x27;');

            // Handle code blocks with language detection
            html = html.replace(/```(\w+)?\s*\n?([\s\S]*?)```/g, (match, language, code) => {
                const trimmedCode = code.trim();
                const lineCount = trimmedCode.split('\n').length;
                const isCompact = lineCount <= 3 && trimmedCode.length < 100;
                const compactClass = isCompact ? ' compact' : '';
                return `<div class="code-block${compactClass}">
                    <pre><code>${trimmedCode}</code></pre>
                </div>`;
            });

            // Handle inline code
            html = html.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');

            // Handle bold text
            html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

            // Handle italic text
            html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

            // Handle headers
            html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>');
            html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>');
            html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>');

            // Handle lists (simple unordered lists)
            html = html.replace(/^- (.*$)/gm, '<li>$1</li>');
            html = html.replace(/(<li>.*<\/li>)/gm, (match, listItems) => {
                // Wrap consecutive list items in <ul>
                return listItems.replace(/(<li>.*?<\/li>)(?=\s*<li>|$)/g, '$1');
            });

            // Wrap consecutive list items in ul tags
            html = html.replace(/(<li>.*?<\/li>)(\s*<li>.*?<\/li>)*/g, '<ul>$&</ul>');

            // Handle line breaks (after all other processing)
            html = html.replace(/\n/g, '<br>');

            return html;
        }

        function escapeForAttribute(str) {
            return str
                .replace(/&/g, '&amp;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#x27;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        }


        function updateMemoryDisplay(stats) {
            // Update memory info in model status area
            const memoryInfo = `${stats.facts} facts, ${stats.experiences} experiences, ${stats.topics} topics`;
            // You could add this to the UI if needed
        }

        function scrollToBottom() {
            const scroll = () => {
                // Force scroll to absolute bottom
                messagesContainer.scrollTop = messagesContainer.scrollHeight + 1000;
            };

            // Immediate scroll
            scroll();

            // Also scroll after DOM updates
            requestAnimationFrame(() => {
                scroll();

                // Try scrollIntoView as well
                const lastMessage = messagesContainer.lastElementChild;
                if (lastMessage) {
                    lastMessage.scrollIntoView({ behavior: 'auto', block: 'start' });
                    // Then scroll a bit more to account for input padding
                    messagesContainer.scrollTop += 100;
                }
            });

            // Final scroll attempt
            setTimeout(scroll, 100);
        }

        // Allow Enter key to work normally for new chat creation