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
    console.log(`\n${'='.repeat(60)}`);
    console.log(`VERIFICANDO DEPLOY - densidade-de-malha-relatorio`);
    console.log(`${'='.repeat(60)}\n`);
    
    // Status do serviço
    const service = await apiRequest('GET', `/services/${SERVICE_ID}`);
    console.log('📋 STATUS DO SERVIÇO:');
    console.log(`   Nome: ${service.data.name}`);
    console.log(`   Tipo: ${service.data.type}`);
    console.log(`   URL: ${service.data.url}`);
    console.log();
    
    // Últimos deploys
    console.log('📦 ÚLTIMOS 5 DEPLOYS:\n');
    const deploys = await apiRequest('GET', `/services/${SERVICE_ID}/deploys?limit=5`);
    
    if (Array.isArray(deploys.data)) {
      deploys.data.forEach((item, idx) => {
        const deploy = item.deploy;
        const status = deploy.status;
        let emoji = '❌';
        if (status === 'live') emoji = '✅';
        else if (status === 'build_in_progress' || status === 'deploy_in_progress') emoji = '⏳';
        
        console.log(`${emoji} Deploy ${idx + 1}:`);
        console.log(`   Status: ${status}`);
        console.log(`   Criado: ${deploy.createdAt}`);
        console.log(`   Finalizado: ${deploy.finishedAt || 'Em progresso...'}`);
        console.log();
      });
    }
    
    // Eventos recentes
    console.log('📊 EVENTOS RECENTES:\n');
    const events = await apiRequest('GET', `/services/${SERVICE_ID}/events?limit=5`);
    
    if (Array.isArray(events.data)) {
      events.data.forEach((item, idx) => {
        const event = item.event;
        console.log(`${idx + 1}. ${event.type}`);
        console.log(`   Timestamp: ${event.timestamp}`);
        if (event.details?.buildStatus) console.log(`   Build Status: ${event.details.buildStatus}`);
        if (event.details?.deployStatus) console.log(`   Deploy Status: ${event.details.deployStatus}`);
        console.log();
      });
    }
    
    console.log(`${'='.repeat(60)}`);
    
  } catch (err) {
    console.error('❌ Erro:', err.message);
  }
}

main();
