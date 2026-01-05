#!/usr/bin/env node

// Wrapper para criar Static Site com chave já embutida
// Este arquivo contém a chave para facilitar a execução

process.env.RENDER_API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";

// Importa e executa o script principal
import('./render-create-static-site.mjs')
  .then(module => {
    // O módulo já executa on load, então só precisamos esperar
    console.log('\nScript concluído.');
    process.exit(0);
  })
  .catch(err => {
    console.error('Erro ao executar:', err);
    process.exit(1);
  });
