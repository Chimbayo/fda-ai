import './styles.css';

interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface ChatSession {
  id: string;
  messages: ChatMessage[];
}

class ChatResponse {
  response!: string;
  timestamp!: Date;
}

class FDAChatBot {
  private chatContainer!: HTMLDivElement;
  private messageInput!: HTMLInputElement;
  private sendButton!: HTMLButtonElement;
  private historyList!: HTMLDivElement;
  private newChatBtn!: HTMLButtonElement;
  private messages: ChatMessage[] = [];
  private chatSessions: ChatSession[] = [];
  private currentSessionId: string = '';
  private isLoading: boolean = false;

  constructor() {
    // Initialize DOM elements with proper error handling
    const chatContainerElement = document.getElementById('chat-container');
    const messageInputElement = document.getElementById('message-input');
    const sendButtonElement = document.getElementById('send-button');
    const historyListElement = document.getElementById('history-list');
    const newChatBtnElement = document.getElementById('new-chat-btn');
    
    if (!chatContainerElement || !messageInputElement || !sendButtonElement || !historyListElement || !newChatBtnElement) {
      console.error('Required DOM elements not found');
      return;
    }
    
    this.chatContainer = chatContainerElement as HTMLDivElement;
    this.messageInput = messageInputElement as HTMLInputElement;
    this.sendButton = sendButtonElement as HTMLButtonElement;
    this.historyList = historyListElement as HTMLDivElement;
    this.newChatBtn = newChatBtnElement as HTMLButtonElement;
    
    this.initializeEventListeners();
    this.loadChatSessions();
    this.createNewSession();
  }

  private initializeEventListeners(): void {
    this.sendButton.addEventListener('click', () => this.sendMessage());
    this.messageInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        this.sendMessage();
      }
    });
    this.newChatBtn.addEventListener('click', () => this.createNewSession());
  }

  private async sendMessage(): Promise<void> {
    const message = this.messageInput.value.trim();
    if (!message) return;

    // Add user message first
    this.addMessageToChat({ content: message, sender: 'user', timestamp: new Date() });
    this.messageInput.value = '';
    this.setLoading(true);

    try {
      console.log('Sending message to API:', message);
      const response = await this.callChatAPI(message);
      console.log('API response:', response);
      this.addMessageToChat({ content: response, sender: 'bot', timestamp: new Date() });
      this.saveChatHistory();
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = this.getDetailedErrorMessage(error);
      this.addMessageToChat({ 
        content: errorMessage, 
        sender: 'bot', 
        timestamp: new Date() 
      });
    } finally {
      this.setLoading(false);
    }
  }

  private getDetailedErrorMessage(error: any): string {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return 'Cannot connect to the server. Please make sure the backend is running on http://localhost:8000';
    } else if (error instanceof Error && error.message.includes('HTTP error')) {
      return `Server error: ${error.message}. Please try again later.`;
    } else {
      return `Error: ${error.message || 'Unknown error occurred'}. Please try again.`;
    }
  }

  private async callChatAPI(message: string): Promise<string> {
    const apiUrl = '/api/chat/';
    
    const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            user_id: 'frontend_user'
        })
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.response;
}
  private addMessageToChat(messageData: Omit<ChatMessage, 'id'>): void {
    const message: ChatMessage = {
      ...messageData,
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
    
    this.messages.push(message);
    
    // Update current session
    const currentSession = this.chatSessions.find(s => s.id === this.currentSessionId);
    if (currentSession) {
      currentSession.messages.push(message);
    }
    
    this.renderMessages();
    this.renderChatHistory();
    this.saveChatSessions();
    this.scrollToBottom();
  }

  private renderMessages(): void {
    if (!this.chatContainer) return;
    
    this.chatContainer.innerHTML = '';
    
    this.messages.forEach(message => {
      const messageElement = document.createElement('div');
      messageElement.className = `message ${message.sender}`;
      
      const contentElement = document.createElement('div');
      contentElement.className = 'message-content';
      
      if (message.sender === 'bot') {
        contentElement.innerHTML = this.formatBotMessage(message.content);
      } else {
        contentElement.textContent = message.content;
      }
      
      messageElement.appendChild(contentElement);
      
      const timestampElement = document.createElement('div');
      timestampElement.className = 'timestamp';
      timestampElement.textContent = this.formatTimestamp(message.timestamp);
      
      messageElement.appendChild(timestampElement);
      this.chatContainer.appendChild(messageElement);
    });
  }

  private formatBotMessage(content: string): string {
    // Convert markdown-style formatting to HTML
    return content
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/• (.*?)$/gm, '<li>$1</li>');
  }

  private formatTimestamp(date: Date): string {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }, 100);
  }

  private setLoading(loading: boolean): void {
    this.isLoading = loading;
    this.sendButton.disabled = loading;
    this.sendButton.textContent = loading ? 'Sending...' : 'Send';
  }

  private saveChatHistory(): void {
    // This method is now handled by saveChatSessions
    this.saveChatSessions();
  }

  private loadChatHistory(): void {
    const saved = localStorage.getItem('fda-chat-history');
    if (saved) {
      try {
        this.messages = JSON.parse(saved);
        this.renderMessages();
      } catch (error) {
        console.error('Error loading chat history:', error);
      }
    }
  }

  private loadChatSessions(): void {
    const saved = localStorage.getItem('fda-chat-sessions');
    if (saved) {
      try {
        this.chatSessions = JSON.parse(saved);
        this.renderChatHistory();
      } catch (error) {
        console.error('Error loading chat sessions:', error);
      }
    }
  }

  private saveChatSessions(): void {
    localStorage.setItem('fda-chat-sessions', JSON.stringify(this.chatSessions));
  }

  private createNewSession(): void {
    const sessionId = `session_${Date.now()}`;
    this.currentSessionId = sessionId;
    this.messages = [];
    
    const newSession: ChatSession = {
      id: sessionId,
      messages: []
    };
    
    this.chatSessions.unshift(newSession);
    this.renderChatHistory();
    this.renderMessages();
    this.saveChatSessions();
  }

  private renderChatHistory(): void {
    if (!this.historyList) return;
    
    this.historyList.innerHTML = '';
    
    this.chatSessions.forEach((session, index) => {
      const historyItem = document.createElement('div');
      historyItem.className = 'history-item';
      if (session.id === this.currentSessionId) {
        historyItem.classList.add('active');
      }
      
      const content = document.createElement('div');
      content.className = 'history-item-content';
      
      const title = document.createElement('div');
      title.className = 'history-item-title';
      title.textContent = `Chat ${this.chatSessions.length - index}`;
      
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'delete-btn';
      deleteBtn.textContent = 'Delete';
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent loading session
        this.deleteSession(session.id);
      });
      
      title.appendChild(deleteBtn);
      
      const preview = document.createElement('div');
      preview.className = 'history-item-preview';
      if (session.messages && session.messages.length > 0) {
        const lastMessage = session.messages[session.messages.length - 1];
        if (lastMessage && lastMessage.content) {
          preview.textContent = lastMessage.content.substring(0, 50) + '...';
        }
      } else {
        preview.textContent = 'New chat';
      }
      
      const time = document.createElement('div');
      time.className = 'history-item-time';
      if (session.messages && session.messages.length > 0) {
        const lastMessage = session.messages[session.messages.length - 1];
        if (lastMessage && lastMessage.timestamp) {
          time.textContent = this.formatTimestamp(lastMessage.timestamp);
        }
      } else {
        time.textContent = 'Just now';
      }
      
      content.appendChild(title);
      content.appendChild(preview);
      content.appendChild(time);
      
      historyItem.appendChild(content);
      
      historyItem.addEventListener('click', () => {
        this.loadSession(session.id);
      });
      
      this.historyList.appendChild(historyItem);
    });
  }

  private loadSession(sessionId: string): void {
    const session = this.chatSessions.find(s => s.id === sessionId);
    if (session) {
      this.currentSessionId = sessionId;
      this.messages = session.messages;
      this.renderMessages();
      this.renderChatHistory();
    }
  }

  private deleteSession(sessionId: string): void {
    // Confirm deletion
    if (confirm('Are you sure you want to delete this chat session?')) {
      // Remove session from array
      this.chatSessions = this.chatSessions.filter(s => s.id !== sessionId);
      
      // If deleting current session, create a new one
      if (sessionId === this.currentSessionId) {
        if (this.chatSessions.length > 0) {
          this.loadSession(this.chatSessions[0].id);
        } else {
          this.createNewSession();
        }
      }
      
      // Update UI and save
      this.renderChatHistory();
      this.saveChatSessions();
    }
  }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new FDAChatBot();
});
