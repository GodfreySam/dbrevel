import { Link } from "react-router-dom";

export default function SdkIntegrationGuide() {
	return (
		<section className="dashboard-section">
			<h2>SDK Integration</h2>
			<div className="info-card">
				<p style={{ marginBottom: "16px" }}>
					Use your project's API key to integrate with the DbRevel SDK:
				</p>
				<pre className="code-snippet">
					{`import { DbRevelClient } from '@dbrevel/sdk';

const client = new DbRevelClient({
  apiKey: 'your_project_api_key_here'
});

// Query using natural language
const result = await client.query('Get all users from Lagos');`}
				</pre>
				<p style={{ marginTop: "16px", fontSize: "14px", color: "#666" }}>
					Learn more in our <Link to="/docs">documentation</Link>.
				</p>
			</div>
		</section>
	);
}
