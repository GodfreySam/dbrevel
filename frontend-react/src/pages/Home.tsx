import { useState } from "react";
import { Link } from "react-router-dom";
import "../App.css";
import LanguageSupportTable from "../components/LanguageSupportTable";
import Toast from "../components/Toast/Toast";
import { config } from "../config";
import { useAuth } from "../contexts/AuthContext";
import { apiFetchJson } from "../utils/api";
import Header from "../components/Header";
// removed unused ErrorBanner import

interface QueryResult {
	data: any[];
	metadata: {
		query_plan: {
			queries: Array<{
				database: string;
				query_type: string;
				query: string | any[];
			}>;
		};
		execution_time_ms: number;
		rows_returned: number;
		trace_id: string;
	};
}

export default function Home() {
	const { isAuthenticated, user } = useAuth();
	const [query, setQuery] = useState("");
	const [dryRun, setDryRun] = useState(false);
	const [loading, setLoading] = useState(false);
	const [result, setResult] = useState<QueryResult | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [showCodeExample, setShowCodeExample] = useState(false);
	const [showBeforeAfter, setShowBeforeAfter] = useState(true);
	const [toast, setToast] = useState<{
		message: string;
		type: "success" | "error" | "info";
	} | null>(null);

	const exampleQueries = [
		"Get all users",
		"Show me customers from Lagos",
		"Count orders by status",
		"Find products with price > 1000",
	];

	const executeQuery = async () => {
		if (!query.trim()) {
			setError("Please enter a query");
			return;
		}

		setLoading(true);
		setError(null);
		setResult(null);

		try {
			// Build headers - X-Project-Key is optional (backend uses demo project if omitted)
			const headers: HeadersInit = {
				"Content-Type": "application/json",
			};

			// Include X-Project-Key if configured (for explicit demo project usage)
			if (config.accountKey) {
				headers["X-Project-Key"] = config.accountKey;
			}

			const data = await apiFetchJson<QueryResult>("/query", {
				method: "POST",
				headers,
				body: JSON.stringify({ intent: query, dry_run: dryRun }),
			});
			setResult(data);
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "An unknown error occurred",
			);
		} finally {
			setLoading(false);
		}
	};

	const copyToClipboard = async (text: string, label: string = "Code") => {
		try {
			await navigator.clipboard.writeText(text);
			setToast({ message: `${label} copied to clipboard!`, type: "success" });
		} catch (err) {
			console.error("Failed to copy:", err);
			setToast({
				message: `Failed to copy ${label}. Please try again.`,
				type: "error",
			});
		}
	};

	const generateCurl = () => {
		// Use double quotes for JSON to work cross-platform (Windows compatibility)
		const jsonPayload = JSON.stringify({ intent: query, dry_run: dryRun });
		return `curl -X POST "${config.apiUrl}/query" \\
  -H "Content-Type: application/json" \\
  -H "X-Project-Key: ${config.accountKey}" \\
  -d '${jsonPayload}'`;
	};

	const generateSDKCode = () => {
		return `import { DbRevelClient } from '@dbrevel/sdk';

const client = new DbRevelClient({
  baseUrl: '${config.baseUrl}',
  apiKey: '${config.accountKey}',
});

const result = await client.query('${query}', {
  dryRun: ${dryRun}
});

console.log(result.data);`;
	};

	const generateFetchCode = () => {
		return `const response = await fetch('${config.apiUrl}/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Project-Key': '${config.accountKey}',
  },
  body: JSON.stringify({
    intent: '${query}',
    dry_run: ${dryRun},
  }),
});

const result = await response.json();`;
	};

	return (
		<div className="app-wrapper">
			{/* Header with Logo */}
			<Header />

			{/* Authenticated User Banner */}
			{isAuthenticated && (
				<div
					style={{
						background: "linear-gradient(135deg, #6a9d3a 0%, #5a8d2a 100%)",
						color: "white",
						padding: "16px 20px",
						textAlign: "center",
						fontSize: "14px",
					}}
				>
					<div
						style={{
							maxWidth: "1200px",
							margin: "0 auto",
							display: "flex",
							justifyContent: "space-between",
							alignItems: "center",
							flexWrap: "wrap",
							gap: "12px",
						}}
					>
						<span>
							👋 Welcome back
							{user?.account_name &&
							user.account_name !== "DbRevel Demo Account"
								? `, ${user.account_name}`
								: user?.email
								? `, ${user.email.split("@")[0]}`
								: ""}
							! You're logged in. Test the demo below or{" "}
							<Link
								to="/dashboard"
								style={{
									color: "white",
									textDecoration: "underline",
									fontWeight: "600",
								}}
							>
								go to your dashboard
							</Link>
							.
						</span>
						<Link
							to="/dashboard"
							style={{
								background: "white",
								color: "#6a9d3a",
								padding: "8px 20px",
								borderRadius: "6px",
								textDecoration: "none",
								fontWeight: "600",
								fontSize: "14px",
								whiteSpace: "nowrap",
							}}
						>
							Go to Dashboard →
						</Link>
					</div>
				</div>
			)}

			{/* Intro Section */}
			<section className="intro-section">
				<div className="container">
					<div className="intro-content">
						<h1>
							Stop Writing Database Queries.
							<br />
							Start Using an API.
						</h1>
						<p className="intro-subtitle">
							{isAuthenticated
								? "You're testing with the demo tenant. Try a query below or go to your dashboard to use your own credentials."
								: "DbRevel converts natural language into secure, optimized queries—eliminating 60% of backend boilerplate. No database expertise needed. Just simple HTTP requests."}
						</p>
						<div className="intro-cta">
							<Link to="/docs" className="cta-btn primary">
								View API Docs
							</Link>
							<button
								onClick={() => setShowCodeExample(!showCodeExample)}
								className="cta-btn secondary"
							>
								Try SDK
							</button>
							{isAuthenticated ? (
								<Link to="/dashboard" className="cta-btn primary">
									Go to Dashboard
								</Link>
							) : (
								<Link to="/signup" className="cta-btn primary">
									Get Started
								</Link>
							)}
						</div>
					</div>
				</div>
			</section>

			{/* Before/After Comparison */}
			{showBeforeAfter && (
				<section className="comparison-section">
					<div className="container">
						<h2>Before vs. After</h2>
						<div className="comparison-grid">
							<div className="comparison-item before">
								<div className="comparison-badge">Before</div>
								<h3>Traditional Approach</h3>
								<ul>
									<li>Write complex SQL queries</li>
									<li>Handle database connections</li>
									<li>Manage query optimization</li>
									<li>Implement security checks</li>
									<li>Debug query errors</li>
								</ul>
								<div className="code-example">
									<div className="code-label">Complex SQL:</div>
									<pre className="code-block">
										{`// Complex SQL query
SELECT u.id, u.name, u.email,
       COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.city = 'Lagos'
GROUP BY u.id, u.name, u.email
HAVING COUNT(o.id) > 5
ORDER BY order_count DESC;`}
									</pre>
								</div>
							</div>

							<div className="comparison-item after">
								<div className="comparison-badge">After</div>
								<h3>With DbRevel</h3>
								<ul>
									<li>Natural language queries</li>
									<li>Automatic optimization</li>
									<li>Built-in security</li>
									<li>Multi-database support</li>
									<li>Simple API calls</li>
								</ul>
								<div className="code-example">
									<div className="code-label">Simple API Call:</div>
									<pre className="code-block">
										{`// Natural language API call
const result = await client.query(
  "Get users from Lagos with more than 5 orders"
);

console.log(result.data);`}
									</pre>
								</div>
							</div>
						</div>
						<button
							className="toggle-comparison"
							onClick={() => setShowBeforeAfter(false)}
						>
							Hide Comparison
						</button>
					</div>
				</section>
			)}

			{!showBeforeAfter && (
				<button
					className="toggle-comparison"
					onClick={() => setShowBeforeAfter(true)}
				>
					Show Before/After Comparison
				</button>
			)}

			{/* API Service Section */}
			<section className="service-section">
				<div className="container">
					<h2>API-as-a-Service</h2>
					<p className="service-description">
						DbRevel is a complete API service that eliminates the need for
						writing conventional database queries. Connect your databases and
						start querying with natural language.
					</p>
					<div className="service-grid">
						<div className="service-card">
							<h3>No Database Expertise Needed</h3>
							<p>
								Just describe what you want in plain English. DbRevel handles
								the rest.
							</p>
						</div>
						<div className="service-card">
							<h3>Simple HTTP Requests</h3>
							<p>
								Standard REST API. Works with any language, framework, or tool.
							</p>
						</div>
						<div className="service-card">
							<h3>Works with Your Databases</h3>
							<p>
								Connect your existing PostgreSQL or MongoDB databases. No
								migration needed.
							</p>
						</div>
						<div className="service-card">
							<h3>Multi-Tenant SaaS Ready</h3>
							<p>
								Built for scale. Each customer has isolated databases and
								configuration.
							</p>
						</div>
					</div>
				</div>
			</section>

			{/* Code Examples Modal */}
			{showCodeExample && (
				<div
					className="modal-overlay"
					onClick={() => setShowCodeExample(false)}
				>
					<div className="modal-content" onClick={(e) => e.stopPropagation()}>
						<div className="modal-header">
							<h3>SDK Integration Examples</h3>
							<button
								className="close-btn"
								onClick={() => setShowCodeExample(false)}
							>
								×
							</button>
						</div>
						<div className="code-examples">
							<div className="code-example">
								<div className="code-header">
									<h4>TypeScript SDK</h4>
									<button
										onClick={() =>
											copyToClipboard(generateSDKCode(), "SDK code")
										}
										className="copy-btn"
									>
										Copy
									</button>
								</div>
								<pre className="code-block">{generateSDKCode()}</pre>
							</div>
							<div className="code-example">
								<div className="code-header">
									<h4>JavaScript Fetch</h4>
									<button
										onClick={() =>
											copyToClipboard(generateFetchCode(), "Fetch code")
										}
										className="copy-btn"
									>
										Copy
									</button>
								</div>
								<pre className="code-block">{generateFetchCode()}</pre>
							</div>
							<div className="code-example">
								<div className="code-header">
									<h4>cURL</h4>
									<button
										onClick={() =>
											copyToClipboard(generateCurl(), "cURL command")
										}
										className="copy-btn"
									>
										Copy
									</button>
								</div>
								<pre className="code-block">{generateCurl()}</pre>
							</div>
						</div>
						<LanguageSupportTable />
					</div>
				</div>
			)}

			{/* Testing Playground */}
			<section className="playground-section">
				<div className="container">
					<div className="playground-header">
						<h2>Test the API</h2>
						<Link to="/docs" className="docs-link">
							View API Documentation →
						</Link>
					</div>
					<div className="query-section">
						{isAuthenticated && (
							<div
								style={{
									background: "#fff3cd",
									border: "1px solid #ffc107",
									borderRadius: "8px",
									padding: "16px",
									marginBottom: "24px",
									fontSize: "14px",
									color: "#856404",
								}}
							>
								<strong>🧪 Demo Mode:</strong> You're testing with the demo
								tenant data. Queries will execute against sample data. To use
								your own databases,{" "}
								<Link
									to="/dashboard"
									style={{
										color: "#856404",
										textDecoration: "underline",
										fontWeight: "600",
									}}
								>
									go to your dashboard
								</Link>
								.
							</div>
						)}
						<div className="input-group">
							<label htmlFor="queryInput">
								Enter your natural language query:
							</label>
							<textarea
								id="queryInput"
								value={query}
								onChange={(e) => setQuery(e.target.value)}
								placeholder="e.g., Get all users from Lagos"
								rows={4}
							/>
							<div className="example-queries">
								<span>Try:</span>
								{exampleQueries.map((example, idx) => (
									<button
										key={idx}
										onClick={() => setQuery(example)}
										className="example-btn"
									>
										{example}
									</button>
								))}
							</div>
						</div>

						<div className="query-options">
							<label>
								<input
									type="checkbox"
									checked={dryRun}
									onChange={(e) => setDryRun(e.target.checked)}
								/>
								Dry run (validate only)
							</label>
						</div>

						<button
							onClick={executeQuery}
							disabled={loading}
							className="submit-btn"
						>
							{loading ? "Executing..." : "Execute Query"}
						</button>

						{error && <div className="error-message">{error}</div>}

						{result && (
							<div className="result-section">
								<div className="result-header">
									<h3>Query Results</h3>
									<button
										onClick={() =>
											copyToClipboard(generateCurl(), "cURL command")
										}
										className="action-btn"
										style={{ marginLeft: "auto" }}
									>
										Copy as cURL
									</button>
								</div>
								<div className="metadata">
									<p>
										<strong>Execution Time:</strong>{" "}
										{result.metadata.execution_time_ms.toFixed(2)}ms
									</p>
									<p>
										<strong>Rows Returned:</strong>{" "}
										{result.metadata.rows_returned}
									</p>
									<p>
										<strong>Trace ID:</strong> {result.metadata.trace_id}
									</p>
								</div>
								{result.metadata.query_plan.queries.length > 0 && (
									<div className="generated-query">
										<h4>Generated Query (What DbRevel Created):</h4>
										<pre>
											{typeof result.metadata.query_plan.queries[0].query ===
											"string"
												? result.metadata.query_plan.queries[0].query
												: JSON.stringify(
														result.metadata.query_plan.queries[0].query,
														null,
														2,
												  )}
										</pre>
									</div>
								)}
								{result.data.length > 0 && (
									<div className="data-section">
										<h4>Data ({result.data.length} rows):</h4>
										<div className="table-container">
											<table>
												<thead>
													<tr>
														{Object.keys(result.data[0]).map((key) => (
															<th key={key}>{key}</th>
														))}
													</tr>
												</thead>
												<tbody>
													{result.data.slice(0, 100).map((row, idx) => (
														<tr key={idx}>
															{Object.values(row).map((cell: any, cellIdx) => (
																<td key={cellIdx}>{String(cell ?? "")}</td>
															))}
														</tr>
													))}
												</tbody>
											</table>
											{result.data.length > 100 && (
												<p className="data-note">
													Showing first 100 of {result.data.length} rows
												</p>
											)}
										</div>
									</div>
								)}
							</div>
						)}
					</div>
				</div>
			</section>

			{/* Footer */}
			<footer className="footer">
				<div className="container">
					<div className="footer-content">
						<Link to="/">
							<img
								src="/assets/logo-horizontal.svg"
								alt="DBRevel - AI-Powered Database SDK"
								className="footer-logo"
								width="160"
								height="48"
							/>
						</Link>
						<p>
							AI-Powered Database SDK - Talk to your database in plain English
						</p>
						<div className="footer-links">
							<Link to="/docs" className="footer-link">
								API Documentation
							</Link>
							<a href="mailto:support@dbrevel.io" className="footer-link">
								Support
							</a>
						</div>
					</div>
				</div>
			</footer>

			{/* Toast Notifications */}
			{toast && (
				<Toast
					message={toast.message}
					type={toast.type}
					onClose={() => setToast(null)}
				/>
			)}
		</div>
	);
}
