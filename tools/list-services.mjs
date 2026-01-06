#!/usr/bin/env node

import https from 'https';

const API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";
const OWNER_ID = "tea-d473almmcj7s73b7kepg";

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
    console.log('Buscando serviços da workspace...\n');
    
    const services = await apiRequest('GET', `/owners/${OWNER_ID}/services`);
    
    if (Array.isArray(services.data)) {
      services.data.forEach(service => {
        console.log(`Nome: ${service.name}`);
        console.log(`ID: ${service.id}`);
        console.log(`Tipo: ${service.type}`);
        console.log(`URL: ${service.url}`);
        console.log();
      });
    }
    
  } catch (err) {
    console.error('Erro:', err.message);
  }
}

main();
