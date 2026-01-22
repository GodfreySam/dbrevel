/**
 * DbRevel Direct API Fetch Example
 *
 * This example demonstrates how to use the DbRevel API
 * directly with fetch() without the SDK.
 */

import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

async function main() {
  console.log('🚀 DbRevel Direct API Demo\n');

  const baseUrl = process.env.DBREVEL_BASE_URL || 'http://localhost:8000';
  const apiKey = process.env.DBREVEL_API_KEY || 'dbrevel_demo_project_key';

  console.log(`📡 API Endpoint: ${baseUrl}/api/v1/query`);
  console.log(`🔑 Using API Key: ${apiKey ? '***' + apiKey.slice(-4) : 'demo key'}\n`);

  // Example query
  const query = "Get all users";
  console.log(`📝 Query: "${query}"\n`);

  try {
    console.log('⏳ Sending POST request...\n');

    // Make the API request
    const response = await fetch(`${baseUrl}/api/v1/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Project-Key': apiKey,
      },
      body: JSON.stringify({
        intent: query,
        context: null,
        dry_run: false,
      }),
    });

    // Check if request was successful
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(`API Error (${response.status}): ${errorData.message || response.statusText}`);
    }

    // Parse the response
    const result = await response.json();

    // Display results
    console.log('✅ Query Results:');
    console.log(`   Rows returned: ${result.metadata?.rows_returned || 'N/A'}`);
    console.log(`   Execution time: ${result.metadata?.execution_time_ms || 'N/A'}ms`);
    console.log(`   Trace ID: ${result.metadata?.trace_id || 'N/A'}`);

    if (result.metadata?.query_plan?.queries) {
      console.log(`\n📊 Generated Query:`);
      result.metadata.query_plan.queries.forEach((q, idx) => {
        console.log(`   Query ${idx + 1} (${q.database}):`);
        if (q.query_type === 'sql') {
          console.log(`   ${q.query}`);
        } else if (q.query_type === 'mongodb') {
          console.log(`   ${JSON.stringify(q.query, null, 2)}`);
        }
      });
    }

    console.log(`\n📦 Data (first 3 rows):`);
    const data = result.data || [];
    const dataToShow = Array.isArray(data) ? data.slice(0, 3) : [data].slice(0, 3);
    console.log(JSON.stringify(dataToShow, null, 2));

    if (Array.isArray(data) && data.length > 3) {
      console.log(`\n   ... and ${data.length - 3} more rows`);
    }

  } catch (error) {
    console.error('❌ Request failed:', error.message);
    if (error.cause) {
      console.error('   Cause:', error.cause);
    }
    process.exit(1);
  }
}

main().catch(console.error);
