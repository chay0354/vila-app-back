// Test script to verify inspection task saving
// Run with: node test_inspection_save.js

const https = require('https');
const http = require('http');

const API_BASE_URL = process.env.API_BASE_URL || 'https://vila-app-back.vercel.app';
const INSPECTION_ID = 'INSP-39d40125-ec41-4815-b9d7-d33970b91b5a';

// Test data - mark tasks 1, 2, 3 as completed
const testPayload = {
  id: INSPECTION_ID,
  orderId: 'test-order-id',
  unitNumber: 'הודולה 2',
  guestName: 'רמי',
  departureDate: '2024-12-25',
  status: 'דורש ביקורת היום',
  tasks: [
    { id: '1', name: 'לשים כלור בבריכה', completed: true },
    { id: '2', name: 'להוסיף מים בבריכה', completed: true },
    { id: '3', name: 'לנקות רובוט ולהפעיל', completed: true },
    { id: '4', name: 'לנקות רשת פנים המנוע', completed: false },
    { id: '5', name: 'לעשות בקווש שטיפה לפילטר', completed: false },
    { id: '6', name: 'לטאטא הבק מהמדרגות ומשטחי רביצה', completed: false },
    { id: '7', name: 'לשים כלור בגקוזי', completed: false },
    { id: '8', name: 'להוסיף מים בגקוזי', completed: false },
    { id: '9', name: 'לנקות רובוט גקוזי ולהפעיל', completed: false },
    { id: '10', name: 'לנקות רשת פנים המנוע גקוזי', completed: false },
    { id: '11', name: 'לעשות בקווש שטיפה לפילטר גקוזי', completed: false },
    { id: '12', name: 'לטאטא הבק מהמדרגות ומשטחי רביצה גקוזי', completed: false },
    { id: '13', name: 'ניקיון חדרים', completed: false },
    { id: '14', name: 'ניקיון מטבח', completed: false },
    { id: '15', name: 'ניקיון שירותים', completed: false },
    { id: '16', name: 'פינוי זבל לפח אשפה פנים וחוץ הוילה', completed: false },
    { id: '17', name: 'בדיקת מכשירים', completed: false },
    { id: '18', name: 'בדיקת מצב ריהוט', completed: false },
    { id: '19', name: 'החלפת מצעים', completed: false },
    { id: '20', name: 'החלפת מגבות', completed: false },
    { id: '21', name: 'בדיקת מלאי', completed: false },
    { id: '22', name: 'לבדוק תקינות חדרים', completed: false },
    { id: '23', name: 'כיבוי אורות פנים וחוץ הוילה', completed: false },
    { id: '24', name: 'לנעול דלת ראשית', completed: false },
  ]
};

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

async function testSave() {
  console.log('🧪 Testing Inspection Task Save Functionality\n');
  console.log('='.repeat(60));
  
  // Step 1: Save inspection with tasks 1, 2, 3 marked as completed
  console.log('\n📤 Step 1: Saving inspection with tasks 1, 2, 3 completed...');
  console.log('Payload:', JSON.stringify({
    ...testPayload,
    tasks: testPayload.tasks.slice(0, 3).map(t => ({ id: t.id, name: t.name.substring(0, 20), completed: t.completed }))
  }, null, 2));
  
  try {
    const saveResponse = await makeRequest(`${API_BASE_URL}/api/inspections`, {
      method: 'POST',
    }, testPayload);
    
    console.log(`\n✅ Save Response Status: ${saveResponse.status}`);
    console.log('Response Data:', JSON.stringify(saveResponse.data, null, 2));
    
    if (saveResponse.status !== 200 && saveResponse.status !== 201) {
      console.error('❌ Save failed!');
      return;
    }
    
    // Check response
    if (saveResponse.data && saveResponse.data.tasks) {
      const completedCount = saveResponse.data.tasks.filter(t => t.completed).length;
      const totalCount = saveResponse.data.tasks.length;
      console.log(`\n📊 Save Summary: ${completedCount}/${totalCount} tasks completed`);
      
      // Verify tasks 1, 2, 3 are completed
      const task1 = saveResponse.data.tasks.find(t => t.id === '1');
      const task2 = saveResponse.data.tasks.find(t => t.id === '2');
      const task3 = saveResponse.data.tasks.find(t => t.id === '3');
      
      console.log('\n🔍 Verification:');
      console.log(`  Task 1 (${task1?.name}): completed=${task1?.completed} ${task1?.completed ? '✅' : '❌'}`);
      console.log(`  Task 2 (${task2?.name}): completed=${task2?.completed} ${task2?.completed ? '✅' : '❌'}`);
      console.log(`  Task 3 (${task3?.name}): completed=${task3?.completed} ${task3?.completed ? '✅' : '❌'}`);
    }
    
  } catch (error) {
    console.error('❌ Error saving:', error.message);
    return;
  }
  
  // Step 2: Wait a bit for database to update
  console.log('\n⏳ Waiting 2 seconds for database to update...');
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  // Step 3: Load inspection to verify it was saved
  console.log('\n📥 Step 2: Loading inspection to verify save...');
  try {
    const loadResponse = await makeRequest(`${API_BASE_URL}/api/inspections`, {
      method: 'GET',
    });
    
    console.log(`\n✅ Load Response Status: ${loadResponse.status}`);
    
    if (loadResponse.data && Array.isArray(loadResponse.data)) {
      const inspection = loadResponse.data.find(i => i.id === INSPECTION_ID);
      
      if (inspection) {
        console.log(`\n📋 Found inspection: ${inspection.id}`);
        console.log(`   Tasks loaded: ${inspection.tasks?.length || 0}`);
        
        if (inspection.tasks && inspection.tasks.length > 0) {
          const completedCount = inspection.tasks.filter(t => t.completed).length;
          console.log(`   Completed tasks: ${completedCount}`);
          
          // Check tasks 1, 2, 3
          const task1 = inspection.tasks.find(t => String(t.id) === '1');
          const task2 = inspection.tasks.find(t => String(t.id) === '2');
          const task3 = inspection.tasks.find(t => String(t.id) === '3');
          
          console.log('\n🔍 Verification after load:');
          console.log(`  Task 1: completed=${task1?.completed} ${task1?.completed ? '✅' : '❌'}`);
          console.log(`  Task 2: completed=${task2?.completed} ${task2?.completed ? '✅' : '❌'}`);
          console.log(`  Task 3: completed=${task3?.completed} ${task3?.completed ? '✅' : '❌'}`);
          
          if (task1?.completed && task2?.completed && task3?.completed) {
            console.log('\n🎉 SUCCESS! Tasks are being saved and loaded correctly!');
          } else {
            console.log('\n❌ FAILURE! Tasks are not persisting correctly.');
            console.log('\n📝 Task details:');
            console.log('   Task 1:', JSON.stringify(task1, null, 2));
            console.log('   Task 2:', JSON.stringify(task2, null, 2));
            console.log('   Task 3:', JSON.stringify(task3, null, 2));
          }
        } else {
          console.log('❌ No tasks found in loaded inspection!');
        }
      } else {
        console.log(`❌ Inspection ${INSPECTION_ID} not found in response!`);
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
testSave().catch(console.error);

