# Arquitetura

XLSM somente leitura → núcleo Python determinístico → FastAPI → React/Vite. Uma camada de persistência registra feedback, casos e snapshots em SQLite no desenvolvimento local ou PostgreSQL/Supabase quando `DATABASE_URL` está configurada.

O FastAPI mantém um cache em memória do pipeline normalizado. O cache é protegido contra reconstruções concorrentes e invalidado quando muda a data ou o tamanho do XLSM, do arquivo de pesos ou do arquivo de limiares.

O frontend separa contratos (`types.ts`), acesso à API (`api.ts`), componentes compartilhados (`components.tsx`), páginas em módulos próprios (`pages/*.tsx`) e orquestração (`App.tsx`). O `react-router-dom` mantém uma URL por página, filtros relevantes em query parameters, histórico do navegador, rota 404 e detalhe compartilhável em `/skus/:sku`. As páginas são carregadas sob demanda com `React.lazy`. A navegação desktop usa sidebar fixa; em telas menores ela vira um drawer, sem reservar espaço do conteúdo.

A página **Previsão e recomendações** carrega `GET /api/forecasts` somente quando é aberta. A rota agrega todos os SKUs sobre o pipeline cacheado e reutiliza o mesmo cálculo de recomendação do detalhe. Filtros, indicadores e ordenação são locais; a abertura da página `/skus/:sku` solicita `GET /api/priorities/{sku}`. Assim, a listagem não produz uma chamada serverless por SKU nem aumenta o carregamento inicial das outras páginas.

O Guia de uso, a rota 404, a listagem de previsões e o detalhe do SKU não dependem do carregamento global do dashboard. As demais páginas ainda compartilham `loadDashboard()`; a substituição por chamadas específicas está reservada para a Etapa 2 da V2.

Na publicação, frontend e backend são projetos Vercel separados. O backend é uma Function FastAPI que lê o XLSM e as configurações empacotadas no deploy, sem escrever no filesystem. A persistência usa o Transaction Pooler do Supabase e o frontend recebe somente a URL pública da API. O rewrite definido em `frontend/vercel.json` entrega `index.html` para rotas internas, preservando deep links da SPA.
