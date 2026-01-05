#!/usr/bin/env node

import https from 'https';

const API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";
const SERVICE_ID = "srv-d4kb3u0gjchc73a2kag0";

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
    console.log(`Deletando serviço ${SERVICE_ID}...\n`);
    const result = await apiRequest('DELETE', `/services/${SERVICE_ID}`);
    
    if (result.status === 200 || result.status === 204) {
      console.log('✅ Serviço deletado com sucesso!');
      console.log(`\nStatus: ${result.status}`);
      if (result.data) {
        console.log(JSON.stringify(result.data, null, 2));
      }
    } else {
      console.log(`❌ Erro ao deletar: ${result.status}`);
      console.log(JSON.stringify(result.data, null, 2));
    }
  } catch (err) {
    console.error('Erro:', err.message);
  }
}

main();
