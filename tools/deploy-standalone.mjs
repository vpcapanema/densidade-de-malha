#!/usr/bin/env node

/**
 * Deploy automático para Render via API
 * Executa synchronously e printa resultado
 */

import https from 'https';

const API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d";
const API_BASE = "https://api.render.com/v1";

function apiRequest(method, path, body = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(`${API_BASE}${path}`);
    const bodyStr = body ? JSON.stringify(body) : null;
    
    const options = {
      method,
      hostname: url.hostname,
      path: url.pathname + url.search,
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${API_KEY}`,
        ...(bodyStr ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(bodyStr) } : {})
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode >= 400) {
            reject(new Error(`API Error (${res.statusCode}): ${JSON.stringify(parsed)}`));
          } else {
            resolve(parsed);
          }
        } catch (e) {
          if (res.statusCode >= 400) {
            reject(new Error(`API Error (${res.statusCode}): ${data}`));
          } else {
            resolve({ raw: data });
          }
        }
      });
    });

    req.on('error', reject);
    if (bodyStr) {
      console.log(`\nEnviando POST /services com ${Buffer.byteLength(bodyStr)} bytes`);
      console.log(`Content-Length header: ${Buffer.byteLength(bodyStr)}`);
      req.write(bodyStr);
    }
    req.end();
  });
}

async function main() {
  try {
    console.log('Buscando workspace "My Workspace"...');
    const response = await apiRequest('GET', '/owners');
    const owners = Array.isArray(response) ? response : response.owners || [];
    console.log(`Encontrados ${owners.length} workspaces`);
    
    const workspace = owners.find(o => o.owner?.name === 'My Workspace' || o.name === 'My Workspace');
    if (!workspace) {
      console.error('Workspace "My Workspace" não encontrado');
      console.error('Resposta da API:', JSON.stringify(response, null, 2));
      process.exit(1);
    }
    
    const ownerId = workspace.owner?.id || workspace.id;
    console.log(`✓ Workspace ID: ${ownerId}`);
    
    const payload = {
      type: 'static_site',
      name: 'densidade-de-malha-relatorio',
      ownerId,
      repo: 'https://github.com/vpcapanema/densidade-de-malha',
      branch: 'main',
      autoDeploy: 'yes',
      publishPath: 'relatorio'
    };
    
    console.log('\nPayload:');
    console.log(JSON.stringify(payload, null, 2));
    console.log('\nCriando Static Site...');
    const result = await apiRequest('POST', '/services', payload);
    
    console.log('\n✓ Serviço criado com sucesso!');
    console.log(JSON.stringify({
      serviceId: result.service?.id,
      name: result.service?.name,
      dashboardUrl: result.service?.dashboardUrl,
      url: result.service?.serviceDetails?.url,
      deployId: result.deployId
    }, null, 2));
    
  } catch (err) {
    console.error('Erro:', err.message);
    process.exit(1);
  }
}

main();
