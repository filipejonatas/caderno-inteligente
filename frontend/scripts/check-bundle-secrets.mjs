// Fails the build check if database secrets or unexpected public variables reach the shipped bundle.
// Runs after `vite build`; reads only frontend/dist. No dependency beyond Node.
import { readdir, readFile } from 'node:fs/promises';
import { extname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const ALLOWED_PUBLIC_VARIABLES = new Set(['VITE_API_URL']);
const PATTERNS = [
  ['connection string PostgreSQL', /postgres(?:ql)?:\/\/[^\s"'`]+/i],
  ['variável DATABASE_URL', /DATABASE_URL/],
  ['parâmetro sslmode de conexão', /sslmode=/i],
  ['host do pooler Supabase', /pooler\.supabase\.com/i],
  ['chave de serviço Supabase', /service_role|SUPABASE_(?:SERVICE|SECRET)[A-Z_]*/i],
  ['JWT embutido', /eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/],
  ['chave privada', /-----BEGIN [A-Z ]*PRIVATE KEY-----/],
];

async function files(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => entry.isDirectory() ? files(join(directory, entry.name)) : [join(directory, entry.name)]));
  return nested.flat();
}

let list;
try {
  list = (await files(dist)).filter((file) => ['.js', '.html', '.css', '.map', '.json', '.txt'].includes(extname(file)));
} catch {
  console.error('dist/ não encontrado. Execute `npm run build` antes da verificação de segredos.');
  process.exit(1);
}

const findings = [];
for (const file of list) {
  const text = await readFile(file, 'utf8');
  for (const [label, pattern] of PATTERNS) if (pattern.test(text)) findings.push(`${relative(dist, file)}: ${label}`);
  for (const match of text.matchAll(/\bVITE_[A-Z0-9_]+/g)) {
    if (!ALLOWED_PUBLIC_VARIABLES.has(match[0])) findings.push(`${relative(dist, file)}: variável pública inesperada ${match[0]}`);
  }
}

if (findings.length) {
  console.error('Possíveis segredos no bundle do frontend:\n' + [...new Set(findings)].map((item) => `- ${item}`).join('\n'));
  process.exit(1);
}
console.log(`Bundle verificado: ${list.length} arquivo(s) sem segredos de banco ou variáveis públicas inesperadas.`);
