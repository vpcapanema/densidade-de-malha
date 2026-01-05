#!/usr/bin/env node

import https from 'https';

const API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";
const SERVICE_ID = "srv-d5e1636r433s73arb300"; // densidade-de-malha-relatorio

function apiRequest(method, path) {
  return new Promise((resolve, reject) => {
    const url = new URL(`https://api.render.com/v1${path}`);
    
    const options = {
      hostname: url.hostname,
      path: url.pathname + url.search,
      method,
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${API_KEY}`
      }
    };

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
    req.end();
  });
}

async function main() {
  try {
    console.log(`\nVerificando status do serviço ${SERVICE_ID}...\n`);
    
    // Status do serviço
    const service = await apiRequest('GET', `/services/${SERVICE_ID}`);
    console.log('=== STATUS DO SERVIÇO ===');
    console.log(`Nome: ${service.data.name}`);
    console.log(`Tipo: ${service.data.type}`);
    console.log(`Status: ${service.data.status}`);
    console.log(`URL: ${service.data.url}`);
    console.log();
    
    // Últimos deploys
    console.log('=== ÚLTIMOS DEPLOYS ===\n');
    const deploys = await apiRequest('GET', `/services/${SERVICE_ID}/deploys?limit=5`);
    
    if (Array.isArray(deploys.data)) {
      deploys.data.forEach((item, idx) => {
        const deploy = item.deploy;
        console.log(`Deploy ${idx + 1}:`);
        console.log(`  Status: ${deploy.status}`);
        console.log(`  Criado: ${deploy.createdAt}`);
        console.log(`  Finalizado: ${deploy.finishedAt}`);
        if (deploy.status !== 'live' && deploy.status !== 'build_in_progress') {
          console.log(`  ⚠️ FALHOU!`);
        }
        console.log();
      });
    }
    
    // Eventos recentes
    console.log('=== EVENTOS RECENTES ===\n');
    const events = await apiRequest('GET', `/services/${SERVICE_ID}/events?limit=10`);
    
    if (Array.isArray(events.data)) {
      events.data.slice(0, 3).forEach((item, idx) => {
        const event = item.event;
        console.log(`Evento ${idx + 1}: ${event.type}`);
        console.log(`  Timestamp: ${event.timestamp}`);
        if (event.details?.buildStatus) console.log(`  Build: ${event.details.buildStatus}`);
        if (event.details?.deployStatus) console.log(`  Deploy: ${event.details.deployStatus}`);
        console.log();
      });
    }
    
  } catch (err) {
    console.error('Erro:', err.message);
  }
}

main();
