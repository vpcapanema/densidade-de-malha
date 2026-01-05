#!/usr/bin/env node
/**
 * Simples servidor que roda o script de deploy
 * Acesse http://localhost:3000/deploy para executar
 */

import http from 'http';
import { spawn } from 'child_process';
import path from 'path';

const server = http.createServer((req, res) => {
  if (req.url === '/deploy' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.write('Iniciando deploy...\n\n');
    
    const scriptPath = path.join(path.dirname(import.meta.url).replace('file:///', ''), 'render-create-static-site.mjs');
    
    const child = spawn('node', ['tools/render-create-static-site.mjs', '--owner-name', 'My Workspace'], {
      cwd: 'D:\\densidade _de_malha',
      env: { ...process.env, RENDER_API_KEY: 'rnd_EuGyhhngRII85XsgYwJTRitPxn2d' },
      shell: true
    });
    
    child.stdout.on('data', (data) => {
      res.write(data.toString());
    });
    
    child.stderr.on('data', (data) => {
      res.write(`ERROR: ${data.toString()}`);
    });
    
    child.on('close', (code) => {
      res.write(`\n\nProcesso finalizado com código: ${code}\n`);
      res.end();
    });
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

const PORT = 3000;
server.listen(PORT, () => {
  console.log(`Servidor rodando em http://localhost:${PORT}`);
  console.log(`Acesse http://localhost:${PORT}/deploy para executar o deploy`);
});
