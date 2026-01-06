#!/usr/bin/env node

import https from 'https';

const API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";
const SERVICE_ID = "srv-d5e1636r433s73arb300";
const DEPLOY_ID = "dep-d5euqzc5clsd73ard8lg"; // Deploy mais recente

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
    // Tentar obter logs
    console.log('Buscando logs do deploy mais recente...\n');
    
    const deploys = await apiRequest('GET', `/services/${SERVICE_ID}/deploys?limit=1`);
    if (deploys.data[0]) {
      const latestDeployId = deploys.data[0].deploy.id;
      console.log(`Deploy ID: ${latestDeployId}\n`);
      
      // Tentar obter build logs
      const logs = await apiRequest('GET', `/services/${SERVICE_ID}/deploys/${latestDeployId}`);
      console.log('Detalhes do Deploy:');
      console.log(JSON.stringify(logs.data, null, 2));
    }
    
  } catch (err) {
    console.error('Erro:', err.message);
  }
}

main();
