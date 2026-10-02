# Arquitetura

XLSM somente leitura → núcleo Python determinístico → FastAPI → React/Vite. Uma camada de persistência registra feedback, casos e snapshots em SQLite no desenvolvimento local ou PostgreSQL/Supabase quando `DATABASE_URL` está configurada.

O FastAPI mantém um cache em memória do pipeline normalizado. O cache é protegido contra reconstruções concorrentes e invalidado quando muda a data ou o tamanho do XLSM, do arquivo de pesos ou do arquivo de limiares.

O frontend separa contratos (`types.ts`), acesso à API (`api.ts`), componentes compartilhados (`components.tsx`), páginas (`pages.tsx`) e orquestração (`App.tsx`). A navegação desktop usa sidebar fixa; em telas menores ela vira um drawer, sem reservar espaço do conteúdo.

Na publicação, frontend e backend são projetos Vercel separados. O backend é uma Function FastAPI que lê o XLSM e as configurações empacotadas no deploy, sem escrever no filesystem. A persistência usa o Transaction Pooler do Supabase e o frontend recebe somente a URL pública da API.
