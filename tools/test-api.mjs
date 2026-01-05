#!/usr/bin/env node

import https from 'https';

const API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";

function testAPI() {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.render.com',
      path: '/v1/owners',
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${API_KEY}`,
        'User-Agent': 'Node.js'
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        console.log(`Status: ${res.statusCode}`);
        console.log(`Headers: ${JSON.stringify(res.headers)}`);
        console.log(`Body: ${data}`);
        resolve();
      });
    });

    req.on('error', (err) => {
      console.error('Erro de conexão:', err.message);
      reject(err);
    });
    
    req.end();
  });
}

testAPI().catch(console.error);
