# Quality Autopilot — Control Plane

Custom AgentOS control plane for Quality Autopilot. Built on Next.js 15 with Zustand, Radix UI, and Tailwind CSS.

## Features

- **Chat** — Real-time streaming chat with all 9 QAP agents and 4 squads (SSE streaming)
- **Dashboard** — Phase gate status, agent health, and regression metrics
- **Workflows** — Trigger `spec-to-code`, `discovery-onboard`, `triage-heal` workflows
- **Spec Review** — Human Lead review panel for Gherkin specs from the Scribe agent
- **Healing Dashboard** — Review and approve locator healing patches from the Medic agent

## Quick Start

### Development (standalone)

```bash
cd control-plane
npm install
cp .env.local.example .env.local    # set NEXT_PUBLIC_AGENTOS_URL
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Full Stack (Docker Compose)

```bash
# From the repo root
docker compose up -d
```

This starts:
- `qap-db` — PostgreSQL + PgVector on port 5432
- `qap-api` — AgentOS FastAPI backend on port 8000
- `qap-ui`  — Control plane Next.js app on port 3000

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_AGENTOS_URL` | `http://localhost:8000` | AgentOS API base URL |
| `NEXT_PUBLIC_OS_SECURITY_KEY` | _(empty)_ | Optional auth token |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 15 (App Router) |
| State | Zustand 5 (localStorage persistence) |
| UI | Radix UI + Tailwind CSS |
| Streaming | SSE via AgentOS REST API |
| Animations | Framer Motion |
| Icons | Lucide React |
| Font | Geist Sans + DM Mono |

## Project Structure

```
control-plane/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx            # / — Chat
│   │   ├── dashboard/          # /dashboard
│   │   ├── workflows/          # /workflows
│   │   ├── spec-review/        # /spec-review
│   │   └── healing/            # /healing
│   ├── api/
│   │   ├── os.ts               # AgentOS API calls
│   │   ├── qap.ts              # QAP workflow API calls
│   │   └── routes.ts           # API endpoint constants
│   ├── components/
│   │   ├── chat/               # Full streaming chat UI
│   │   ├── dashboard/          # Phase gates + agent health
│   │   ├── healing/            # Healing patch diff viewer
│   │   ├── layout/             # AppLayout + Nav
│   │   ├── spec-review/        # Gherkin spec approval UI
│   │   ├── ui/                 # Base UI components
│   │   └── workflows/          # Workflow trigger panel
│   ├── hooks/
│   │   ├── useAIResponseStream.tsx  # SSE stream parser
│   │   ├── useAIStreamHandler.tsx   # Streaming chat handler
│   │   ├── useChatActions.ts        # Init + entity fetching
│   │   └── useSessionLoader.tsx     # Session history
│   ├── lib/
│   │   └── utils.ts            # cn(), formatRelativeTime(), etc.
│   ├── store.ts                # Zustand global store
│   └── types/
│       ├── os.ts               # AgentOS types
│       └── qap.ts              # QAP-specific types
├── Dockerfile
├── next.config.ts
├── tailwind.config.ts
└── package.json
```
