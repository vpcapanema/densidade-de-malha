#!/usr/bin/env node

import https from 'https';

const API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";
const SERVICE_ID = "srv-d5e2346mcj7s73b2mk8g";

function apiRequest(method, path, body = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(`https://api.render.com/v1${path}`);
    const bodyStr = body ? JSON.stringify(body) : null;
    
    const options = {
      hostname: url.hostname,
      path: url.pathname + url.search,
      method,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`
      }
    };

    if (bodyStr) {
      options.headers['Content-Length'] = Buffer.byteLength(bodyStr);
    }

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } catch (e) {
          resolve({ status: res.statusCode, raw: data });
        }
      });
    });

    req.on('error', reject);
    if (bodyStr) req.write(bodyStr);
    req.end();
  });
}

async function main() {
  try {
    console.log('Atualizando configuração do serviço...\n');
    
    // Obter detalhes atuais
    const current = await apiRequest('GET', `/services/${SERVICE_ID}`);
    console.log('Serviço atual:');
    console.log(`  Nome: ${current.data.name}`);
    console.log(`  Tipo: ${current.data.type}`);
    console.log(`  PublishPath: ${current.data.publishPath || 'não definido'}`);
    console.log();
    
    // Atualizar com o publishPath correto
    const updatePayload = {
      publishPath: 'relatorio'
    };
    
    console.log('Atualizando com publishPath: relatorio\n');
    const updated = await apiRequest('PATCH', `/services/${SERVICE_ID}`, updatePayload);
    
    if (updated.status === 200) {
      console.log('✅ Serviço atualizado com sucesso!');
      console.log(`  PublishPath agora: ${updated.data.publishPath || 'relatorio'}`);
      console.log('\nRender iniciará novo deploy automaticamente.');
    } else {
      console.log(`❌ Erro ao atualizar: ${updated.status}`);
      console.log(JSON.stringify(updated.data, null, 2));
    }
    
  } catch (err) {
    console.error('Erro:', err.message);
  }
}

main();
