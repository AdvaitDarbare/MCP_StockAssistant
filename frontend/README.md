# 🎨 AI Stock Assistant Frontend

A beautiful, intuitive React frontend for the AI Stock Assistant, featuring a clean chat interface inspired by modern AI assistants.

## ✨ **Design Features**

### **Interface Design**
- **Clean, minimalist layout** with intuitive navigation
- **Message bubbles** with distinct styling for user and assistant
- **Typing indicators** for real-time conversation feel
- **Auto-scrolling** message history
- **Responsive design** that works on all screen sizes

### **Color Scheme**
- **Primary**: Teal/Cyan theme (`#009c96`) for trust and technology
- **Neutrals**: Sophisticated gray palette for readability
- **Status Colors**: Green, yellow, red for market indicators
- **Backgrounds**: Clean whites and light grays

### **Typography**
- **Inter font family** for modern, readable text
- **Balanced text sizing** for comfortable reading
- **Proper line spacing** for message clarity

## 🚀 **Quick Start**

### **Development (Easiest)**
```bash
# From the project root
./dev.sh
```
This starts the entire system including the frontend at `http://localhost:3000`

### **Frontend Only**
```bash  
cd frontend
npm install
npm start
```

### **Manual Setup**
```bash
# Install dependencies
cd frontend
npm install

# Set environment variables
cp .env.example .env
# Edit REACT_APP_API_URL if needed

# Start development server
npm start
```

## 🎮 **User Interface**

### **Chat Interface**
- **Message History**: Scrollable conversation with timestamp
- **User Messages**: Right-aligned blue bubbles
- **Assistant Messages**: Left-aligned white bubbles with AI avatar
- **Loading States**: Typing indicator during processing
- **Auto-resize**: Text input that grows with content

### **Quick Actions**
When you first visit, you'll see helpful quick action buttons:
- 📈 **Stock Price** - "What's AAPL stock price?"
- 📊 **Compare Stocks** - "Compare AAPL vs TSLA"  
- 🕐 **Market Hours** - "What are market hours today?"
- 🏢 **Company Info** - "Tell me about Apple company"
- 📰 **Latest News** - "Recent news for Tesla"
- 👥 **Insider Trading** - "Show me insider trading for NVDA"

### **Message Formatting**
The interface supports rich text formatting:
- **Bold text**: `**bold**`
- *Italic text*: `*italic*`
- `Code snippets`: `` `code` ``
- Code blocks with syntax highlighting
- Automatic line breaks and spacing

## 🛠️ **Technical Stack**

### **Core Technologies**
- **React 18** with TypeScript
- **Tailwind CSS** for styling  
- **Lucide React** for icons
- **Custom hooks** for state management

### **Key Components**
```
src/
├── components/
│   ├── Header.tsx           # App header with branding
│   ├── Message.tsx          # Individual message bubbles
│   ├── MessageInput.tsx     # Text input with send button
│   ├── QuickActions.tsx     # Suggested action buttons
│   └── TypingIndicator.tsx  # Loading animation
├── hooks/
│   └── useChat.ts           # Chat state management
├── utils/
│   └── api.ts               # API communication
└── types/
    └── index.ts             # TypeScript definitions
```

### **State Management**
The `useChat` hook manages:
- **Message history** with persistence
- **Loading states** during API calls
- **Error handling** with user feedback
- **Auto-scrolling** to latest messages

### **API Integration**
- **RESTful calls** to LangGraph backend
- **Error handling** with user-friendly messages
- **Timeout management** for network requests
- **Response formatting** from AI assistant

## 🎨 **Styling System**

### **Design Tokens**
```css
/* Primary Colors */
--primary-500: #009c96  /* Main brand color */
--primary-600: #007d78  /* Hover states */

/* Grays */
--gray-50: #f9fafb     /* Backgrounds */
--gray-900: #101828    /* Text */

/* Status */
--success-500: #10b981  /* Green indicators */
--error-500: #ef4444    /* Error states */
```

### **Component Classes**
- `.message-user` - User message styling
- `.message-assistant` - AI response styling  
- `.input-primary` - Text input styling
- `.btn-primary` - Primary button styling
- `.stock-card` - Data card styling

## 📱 **Responsive Design**

### **Breakpoints**
- **Mobile**: < 768px (single column, compact spacing)
- **Tablet**: 768px - 1024px (adjusted quick actions)
- **Desktop**: > 1024px (full layout with sidebars)

### **Mobile Optimizations**
- **Touch-friendly** button sizes (44px minimum)
- **Readable font sizes** (16px+ for inputs)
- **Optimized spacing** for thumb navigation
- **Responsive quick actions** grid

## 🔧 **Configuration**

### **Environment Variables**
```bash
# .env file
REACT_APP_API_URL=http://127.0.0.1:2024  # Backend API URL
GENERATE_SOURCEMAP=true                   # Dev sourcemaps
FAST_REFRESH=true                         # Hot reloading
```

### **Build Configuration**
```bash
# Production build
npm run build

# Serve production build locally
npx serve -s build -l 3000
```

## 🚀 **Deployment**

### **Development**
```bash
# Start with backend
./dev.sh

# Or frontend only
cd frontend && npm start
```

### **Production**
```bash
# Build optimized version
cd frontend
npm run build

# Deploy the build/ directory to your hosting provider
```

## 🎯 **User Experience**

### **Conversation Flow**
1. **Welcome message** with capability overview
2. **Quick actions** for common queries
3. **Natural conversation** with the AI assistant
4. **Rich responses** with formatted stock data
5. **Conversation history** maintained throughout session

### **Performance**
- **Fast initial load** (< 2 seconds)
- **Instant message sending** with optimistic updates
- **Smooth animations** and transitions
- **Responsive interactions** throughout

### **Accessibility**
- **Keyboard navigation** support
- **Screen reader** friendly markup
- **High contrast** text and backgrounds
- **Focus indicators** for interactive elements

---

🎨 **The frontend provides a beautiful, intuitive interface that makes complex stock market data accessible through natural conversation.**

**Ready to chat with your AI Stock Assistant?** Visit `http://localhost:3000` after running `./dev.sh`!