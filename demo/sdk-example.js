/**
 * DbRevel SDK Example
 *
 * This example demonstrates how to use the DbRevel SDK
 * to execute natural language queries against your database.
 */

import { DbRevelClient } from '@dbrevel/sdk';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

async function main() {
  console.log('🚀 DbRevel SDK Demo\n');

  // Initialize the client
  const client = new DbRevelClient({
    baseUrl: process.env.DBREVEL_BASE_URL || 'http://localhost:8000',
    apiKey: process.env.DBREVEL_API_KEY || 'dbrevel_demo_project_key',
  });

  console.log(`📡 Connected to: ${process.env.DBREVEL_BASE_URL || 'http://localhost:8000'}`);
  console.log(`🔑 Using API Key: ${process.env.DBREVEL_API_KEY ? '***' + process.env.DBREVEL_API_KEY.slice(-4) : 'demo key'}\n`);

  // Example queries to try
  const queries = [
    "Get all users",
    "Get customers in Lagos with more than 5 orders",
    "Show products with price over 100",
    "Count orders by status",
  ];

  // Run the first query as an example
  const query = queries[0];
  console.log(`📝 Query: "${query}"\n`);

  try {
    console.log('⏳ Executing query...\n');

    // Execute the query
    const result = await client.query(query);

    // Display results
    console.log('✅ Query Results:');
    console.log(`   Rows returned: ${result.metadata.rows_returned}`);
    console.log(`   Execution time: ${result.metadata.execution_time_ms}ms`);
    console.log(`   Trace ID: ${result.metadata.trace_id}`);

    if (result.metadata.query_plan && result.metadata.query_plan.queries) {
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
    const dataToShow = Array.isArray(result.data)
      ? result.data.slice(0, 3)
      : [result.data].slice(0, 3);
    console.log(JSON.stringify(dataToShow, null, 2));

    if (result.data.length > 3) {
      console.log(`\n   ... and ${result.data.length - 3} more rows`);
    }

  } catch (error) {
    console.error('❌ Query failed:', error.message);
    if (error.response) {
      console.error('   Status:', error.response.status);
      console.error('   Details:', error.response.data);
    }
    process.exit(1);
  }
}

main().catch(console.error);
