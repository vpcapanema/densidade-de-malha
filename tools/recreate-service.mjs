#!/usr/bin/env node

import https from 'https';

const API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";
const SERVICE_ID = "srv-d5e1636r433s73arb300";
const OWNER_ID = "tea-d473almmcj7s73b7kepg"; // My Workspace

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
    console.log('Deletando serviço com falha...\n');
    
    const deleteResult = await apiRequest('DELETE', `/services/${SERVICE_ID}`);
    
    if (deleteResult.status === 204 || deleteResult.status === 200) {
      console.log('✅ Serviço deletado com sucesso!\n');
      
      console.log('Aguardando 3 segundos antes de recriar...\n');
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      console.log('Recriando serviço com configuração correta...\n');
      
      const createPayload = {
        type: 'static_site',
        name: 'densidade-de-malha-relatorio',
        ownerId: OWNER_ID,
        repo: 'https://github.com/vpcapanema/densidade-de-malha',
        branch: 'main',
        autoDeploy: 'yes',
        publishPath: 'relatorio'
      };
      
      const createResult = await apiRequest('POST', '/services', createPayload);
      
      if (createResult.status === 201 || createResult.status === 200) {
        console.log('✅ Serviço recriado com sucesso!');
        console.log(`   ID: ${createResult.data.id}`);
        console.log(`   Nome: ${createResult.data.name}`);
        console.log(`   URL: ${createResult.data.url}`);
        console.log(`   PublishPath: ${createResult.data.publishPath}`);
      } else {
        console.log(`❌ Erro ao criar: ${createResult.status}`);
        console.log(JSON.stringify(createResult.data, null, 2));
      }
    } else {
      console.log(`❌ Erro ao deletar: ${deleteResult.status}`);
      console.log(JSON.stringify(deleteResult.data, null, 2));
    }
    
  } catch (err) {
    console.error('Erro:', err.message);
  }
}

main();
