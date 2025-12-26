// Test script to check a specific inspection
// Run with: node test_specific_inspection.js

const https = require('https');
const http = require('http');

const API_BASE_URL = process.env.API_BASE_URL || 'https://vila-app-back.vercel.app';
const INSPECTION_ID = 'INSP-291e0855-91b5-412e-be5f-658f83149bd7';

function makeRequest(url, options, data) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const isHttps = urlObj.protocol === 'https:';
    const client = isHttps ? https : http;
    
    const reqOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port || (isHttps ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    };

    const req = client.request(reqOptions, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try {
          const parsed = body ? JSON.parse(body) : null;
          resolve({ status: res.statusCode, headers: res.headers, data: parsed, raw: body });
        } catch (e) {
          resolve({ status: res.statusCode, headers: res.headers, data: body, raw: body });
        }
      });
    });

    req.on('error', reject);
    
    if (data) {
      req.write(JSON.stringify(data));
    }
    
    req.end();
  });
}

async function testSpecificInspection() {
  console.log('🔍 Testing specific inspection:', INSPECTION_ID);
  console.log('='.repeat(60));
  
  // Load all inspections
  console.log('\n📥 Loading all inspections...');
  try {
    const loadResponse = await makeRequest(`${API_BASE_URL}/api/inspections`, {
      method: 'GET',
    });
    
    console.log(`\n✅ Load Response Status: ${loadResponse.status}`);
    
    if (loadResponse.data && Array.isArray(loadResponse.data)) {
      const inspection = loadResponse.data.find(i => i.id === INSPECTION_ID);
      
      if (inspection) {
        console.log(`\n📋 Found inspection: ${inspection.id}`);
        console.log(`   Unit: ${inspection.unit_number || inspection.unitNumber}`);
        console.log(`   Guest: ${inspection.guest_name || inspection.guestName}`);
        console.log(`   Tasks loaded: ${inspection.tasks?.length || 0}`);
        
        if (inspection.tasks && inspection.tasks.length > 0) {
          const completedCount = inspection.tasks.filter(t => t.completed).length;
          console.log(`   Completed tasks: ${completedCount}`);
          
          // Show first few tasks
          console.log('\n📝 First 5 tasks:');
          inspection.tasks.slice(0, 5).forEach(t => {
            console.log(`   Task ${t.id} (${t.name}): completed=${t.completed}`);
          });
        } else {
          console.log('\n❌ No tasks found for this inspection!');
          console.log('   This means either:');
          console.log('   1. Tasks were not saved to the database');
          console.log('   2. The backend query is not finding them');
          console.log('   3. There is a mismatch in inspection_id');
        }
      } else {
        console.log(`\n❌ Inspection ${INSPECTION_ID} not found in response!`);
        console.log('   Available inspections:');
        loadResponse.data.forEach(i => {
          console.log(`   - ${i.id} (${i.unit_number || i.unitNumber})`);
        });
      }
    } else {
      console.log('❌ Invalid response format:', loadResponse.data);
    }
  } catch (error) {
    console.error('❌ Error loading:', error.message);
  }
  
  console.log('\n' + '='.repeat(60));
  console.log('✅ Test completed!');
}

// Run the test
testSpecificInspection().catch(console.error);





