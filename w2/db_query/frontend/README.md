# DB Query Tool - Frontend

React-based web interface for the database query tool using Refine framework and Ant Design.

## Features

- Database connection management
- Schema browser with tree view
- SQL editor with syntax highlighting (Monaco Editor)
- Query results with pagination
- Natural language to SQL generation

## Requirements

- Node.js 18+
- yarn

## Setup

```bash
# Install dependencies
yarn install

# Run development server
yarn dev
```

The frontend will be available at: http://localhost:5173

## Scripts

| Command | Description |
|---------|-------------|
| `yarn dev` | Start development server |
| `yarn build` | Build for production |
| `yarn preview` | Preview production build |
| `yarn lint` | Run ESLint |
| `yarn typecheck` | Run TypeScript type checking |

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx                 # Application entry with Refine config
│   ├── main.tsx                # React entry point
│   ├── index.css               # Global styles (Tailwind)
│   ├── components/
│   │   ├── DatabaseList.tsx    # Database connection list
│   │   ├── SchemaTree.tsx      # Schema tree view
│   │   ├── SqlEditor.tsx       # Monaco SQL editor
│   │   ├── QueryResults.tsx    # Query results table
│   │   └── NaturalLanguageInput.tsx  # AI query input
│   ├── pages/
│   │   ├── databases/
│   │   │   ├── list.tsx        # Database list page
│   │   │   └── show.tsx        # Database detail page
│   │   └── query/
│   │       └── index.tsx       # Query execution page
│   ├── providers/
│   │   └── dataProvider.ts     # Refine data provider
│   ├── types/
│   │   └── index.ts            # TypeScript type definitions
│   └── utils/
│       └── error.ts            # Error handling utilities
├── index.html                  # HTML entry
├── package.json                # Dependencies
├── tsconfig.json               # TypeScript config
├── vite.config.ts              # Vite config
├── tailwind.config.js          # Tailwind CSS config
└── postcss.config.js           # PostCSS config
```

## Tech Stack

- **Framework**: React 18 + Refine 5
- **UI Components**: Ant Design 5
- **Styling**: Tailwind CSS
- **SQL Editor**: Monaco Editor
- **Build Tool**: Vite
- **Language**: TypeScript

## Backend API

The frontend expects the backend API to be running at `http://localhost:8000`.

See [../backend/README.md](../backend/README.md) for backend setup instructions.

## Pages

### Databases (`/databases`)
- View all saved database connections
- Add new PostgreSQL connections
- Delete existing connections

### Database Detail (`/databases/:id`)
- View database metadata
- Browse schema structure (tables, views, columns)
- Refresh metadata

### Query (`/query/:dbName`)
- Write and execute SQL queries
- View query results with pagination
- Generate SQL from natural language descriptions
