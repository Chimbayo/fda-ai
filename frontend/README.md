# FDA-AI Frontend

A modern TypeScript frontend for the FDA-AI Agricultural Assistant.

## Features

- 🌾 **Real-time Chat**: Connects to FastAPI backend
- 💬 **Message History**: Persists conversations in localStorage
- 📱 **Responsive Design**: Works on desktop and mobile
- ⚡ **TypeScript**: Type-safe development
- 🎨 **Modern UI**: Clean, agricultural-themed design

## Technology Stack

- **TypeScript 5.0+**: Type-safe frontend development
- **Vite 5.0**: Fast build tool and dev server
- **CSS3**: Modern styling with gradients and animations
- **Fetch API**: Browser-native HTTP requests

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Configuration

The frontend connects to the FastAPI backend at `http://localhost:8000` by default. You can modify the backend URL in `src/main.ts`.

### Features

- **Smart Routing**: Automatically detects agricultural queries
- **Message Formatting**: Supports rich text formatting
- **Error Handling**: Graceful error display
- **Local Storage**: Chat history persistence
- **Responsive**: Mobile-friendly interface

## File Structure

```
frontend/
├── src/
│   ├── main.ts          # Main application logic
│   ├── styles.css       # Application styles
│   └── main.js         # Compiled JavaScript
├── index.html           # Main HTML file
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
└── vite.config.ts         # Vite build configuration
```

## API Integration

The frontend sends POST requests to `/chat` endpoint:

```typescript
const response = await fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: message,
    user_id: 'frontend_user'
  })
});
```

And expects responses in format:

```typescript
interface ChatResponse {
  response: string;
}
```
