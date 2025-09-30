# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
- `npm run dev` - Start development server (opens on port 3000)
- `npm run build` - Build production bundle to `dist/`
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint with auto-fix
- `npm run format` - Format code with Prettier

### Environment Setup
1. Copy `.env.example` to `.env`
2. Configure Dify API credentials:
   ```env
   VITE_DIFY_API_URL=https://api.dify.ai/v1
   VITE_DIFY_API_KEY=app-xxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. Restart dev server after env changes

## Architecture Overview

### Technology Stack
- **Frontend**: Vue 3 with Composition API
- **State Management**: Pinia stores
- **Build Tool**: Vite with Vue plugin
- **UI Components**: Ant Design Vue
- **API Integration**: Dify workflow API
- **Styling**: CSS with CSS variables
- **Markdown**: markdown-it with highlight.js

### Project Structure
```
src/
├── components/          # Vue components
│   ├── Sidebar.vue     # Chat sidebar with history
│   ├── MainChat.vue    # Main chat interface
│   └── Message.vue     # Individual messages
├── services/
│   └── dify.js         # Dify API service layer
├── stores/
│   └── chat.js         # Pinia chat state management
├── views/
│   └── Chat.vue        # Main chat page
└── utils/
    └── helpers.js      # Utility functions
```

### Key Architectural Patterns

**State Management**:
- Centralized chat state in Pinia store (`useChatStore`)
- Conversation management with local IDs + Dify conversation IDs
- Message history with real-time streaming updates
- Abort controllers for canceling API requests

**API Integration**:
- `DifyService` class handles all Dify API communications
- Supports both streaming and blocking response modes
- Demo mode with simulated responses when API key not configured
- File upload support with batch processing

**Streaming Chat Implementation**:
- Server-Sent Events (SSE) for real-time message streaming
- Progressive message building with `onMessage` callbacks
- AbortController integration for stopping generation
- Error handling for network/API failures

**Conversation Management**:
- Local conversation IDs mapped to Dify conversation IDs
- History loading from Dify API with message reconstruction
- Empty conversation cleanup to avoid clutter
- Dynamic title generation from first user message

## Special Features

### Think Tag Processing
- Automatically detects and styles `<think></think>` tags in AI responses
- Renders thinking process in smaller gray text with special icon
- Preserves markdown rendering for the rest of the content

### File Upload System
- Multi-file upload with drag & drop support
- File type detection (image, document, text, etc.)
- Batch upload with progress tracking
- Integration with Dify's file reference system

### Responsive Design
- Desktop: Fixed sidebar layout
- Mobile: Collapsible drawer sidebar
- Breakpoint: 768px

## Development Notes

### Component Communication
- Parent-child prop passing for data flow
- Event emission for user interactions
- Pinia store for global state management

### Error Handling
- API errors with user-friendly messages
- Network timeout handling
- Graceful fallbacks to demo mode

### Performance Considerations
- Message virtualization for large chat histories
- Debounced input handling
- Lazy loading of conversation history
- Optimized re-rendering with computed properties

## Deployment Configuration

### PM2 Production Setup
- `ecosystem.config.js` configured for cluster mode
- 2 instances with auto-restart
- Serves via `vite preview` on port 3000
- Memory limit: 1GB per instance

### Environment Variables
- All client-side env vars must be prefixed with `VITE_`
- `.env.example` and `.env.production.example` provided
- API keys should never be committed to repository