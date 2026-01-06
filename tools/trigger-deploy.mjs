#!/usr/bin/env node

import https from 'https';

const API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";
const SERVICE_ID = "srv-d5e1636r433s73arb300";

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
    console.log('Acionando novo deploy...\n');
    
    const result = await apiRequest('POST', `/services/${SERVICE_ID}/deploys`);
    
    if (result.status === 201 || result.status === 200) {
      console.log('✅ Deploy acionado com sucesso!');
      if (result.data.id) {
        console.log(`   Deploy ID: ${result.data.id}`);
      }
    } else {
      console.log(`Status: ${result.status}`);
      console.log(JSON.stringify(result.data, null, 2));
    }
    
  } catch (err) {
    console.error('Erro:', err.message);
  }
}

main();
