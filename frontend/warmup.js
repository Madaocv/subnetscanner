#!/usr/bin/env node

const http = require('http');

// Список сторінок для warm-up
const pages = [
  '/',
  '/device-types',
  '/sites'
];

const baseUrl = 'http://localhost:3000';

function warmupPage(path) {
  return new Promise((resolve, reject) => {
    console.log(`🔥 Warming up: ${path}`);
    const startTime = Date.now();
    
    const req = http.get(`${baseUrl}${path}`, (res) => {
      const duration = Date.now() - startTime;
      console.log(`✅ ${path} - ${res.statusCode} (${duration}ms)`);
      resolve();
    });
    
    req.on('error', (err) => {
      console.log(`❌ ${path} - Error: ${err.message}`);
      resolve(); // Continue with other pages even if one fails
    });
    
    req.setTimeout(30000, () => {
      console.log(`⏰ ${path} - Timeout`);
      req.destroy();
      resolve();
    });
  });
}

async function warmupAll() {
  console.log('🚀 Starting Next.js page warm-up...');
  
  // Wait for Next.js to be ready
  console.log('⏳ Waiting for Next.js to be ready...');
  await new Promise(resolve => setTimeout(resolve, 5000));
  
  // Warm up each page
  for (const page of pages) {
    await warmupPage(page);
    await new Promise(resolve => setTimeout(resolve, 1000)); // Small delay between requests
  }
  
  console.log('🎉 Warm-up completed!');
}

warmupAll().catch(console.error);
