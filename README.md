# AgentUI

![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-4B8BBE?style=flat-square)
![LLaMA](https://img.shields.io/badge/LLaMA_3.3_70B-Groq-F55036?style=flat-square)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38BDF8?style=flat-square&logo=tailwindcss)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker)
![Railway](https://img.shields.io/badge/Deployed_on-Railway-0B0D0E?style=flat-square&logo=railway)

A full-stack conversational AI agent with real-time web search, streaming responses, and a dark glassmorphism UI. Built with a LangGraph-powered FastAPI backend and a Next.js frontend.

---

## Features

- **Streaming responses** — token-by-token output via Server-Sent Events (SSE)
- **Web search** — agent autonomously searches the web using Tavily and displays sources
- **Persistent memory** — conversation context maintained across turns via LangGraph checkpointing
- **Session history** — conversations stored in sessionStorage and accessible from the sidebar
- **Responsive UI** — works on desktop and mobile with a slide-in sidebar drawer
- **Neon glassmorphism design** — dark theme with hot pink/magenta accents and animated effects

---

## Tech Stack

### Backend (`/server`)
| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Agent runtime | LangGraph |
| LLM | LLaMA 3.3 70B via Groq |
| Web search | Tavily Search API |
| Streaming | Server-Sent Events (SSE) |
| Containerization | Docker |

### Frontend (`/client`)
| Layer | Technology |
|---|---|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS v4 + CSS variables |
| Icons | Lucide React |
| Deployment | Railway |

---

## Project Structure

```
project/
├── server/                  # FastAPI backend
│   ├── app.py               # Main application + LangGraph agent
│   ├── Dockerfile           # Container definition
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment variable template
│
└── client/                  # Next.js frontend
    └── app/
        ├── globals.css          # Design system + animations
        ├── layout.tsx           # Root layout
        ├── page.tsx             # Entry page
        └── components/
            ├── ChatShell.tsx        # Main layout + SSE logic
            ├── Sidebar.tsx          # Conversation history drawer
            ├── TopBar.tsx           # Title + capability pills
            ├── MessageList.tsx      # Scrollable message area
            ├── MessageBubble.tsx    # Individual message bubble
            ├── SearchCard.tsx       # Web search indicator + URLs
            ├── ThinkingIndicator.tsx# Animated reasoning dots
            ├── ChatInput.tsx        # Textarea + send button
            └── types.ts             # Shared TypeScript types
```

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- A [Groq API key](https://console.groq.com)
- A [Tavily API key](https://tavily.com)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 2. Set up the backend

```bash
cd server
cp .env.example .env
# Fill in your API keys in .env
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### 3. Set up the frontend

```bash
cd client
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Environment Variables

### Backend (`server/.env`)

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key for LLaMA inference |
| `TAVILY_API_KEY` | Your Tavily API key for web search |

### Frontend (`client/.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL of the FastAPI backend (e.g. `http://localhost:8000`) |

---

## Deployment

Both services are deployed on **Railway** with automatic deploys on every push to `main`.

- **Backend** — Docker service pointing to `/server`
- **Frontend** — Node.js service pointing to `/client`

Set `NEXT_PUBLIC_API_URL` in the frontend Railway service to the backend's public Railway URL.

---

## How It Works

```
User message
     │
     ▼
Next.js frontend  ──GET /chat_stream/{message}──▶  FastAPI backend
                                                          │
                                                          ▼
                                                   LangGraph agent
                                                          │
                                              ┌───────────┴───────────┐
                                              ▼                       ▼
                                         LLaMA 3.3              Tavily Search
                                         (Groq)                  (if needed)
                                              │                       │
                                              └───────────┬───────────┘
                                                          ▼
                                                   SSE event stream
                                                  (session, thinking,
                                                  search_start, content,
                                                  search_results, end)
                                                          │
                                                          ▼
                                              Real-time UI updates
```

---

## Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create a branch** for your feature
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and test locally
4. **Commit** with a clear message
   ```bash
   git commit -m "feat: add your feature description"
   ```
5. **Push** to your fork
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request** against `main` — describe what you changed and why

### Guidelines

- Keep PRs focused — one feature or fix per PR
- Test both backend and frontend before submitting
- Follow the existing code style (TypeScript strict mode, Python type hints)
- Add comments for non-obvious logic

---

## License

MIT — feel free to use, modify, and distribute.
