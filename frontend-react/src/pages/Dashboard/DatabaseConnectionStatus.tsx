import { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { ProjectDetail } from "../../types/api";
import { apiFetchJson } from "../../utils/api";

interface DatabaseConnectionStatusProps {
	project: ProjectDetail;
}

export default function DatabaseConnectionStatus({
	project,
}: DatabaseConnectionStatusProps) {
	const { token, logout } = useAuth();
	const [isTesting, setIsTesting] = useState(false);
	const [results, setResults] = useState<{
		postgres?: string;
		mongodb?: string;
	} | null>(null);

	// Helper to validate URL strings more strictly
	const isValidUrl = (url: string | null | undefined) => {
		if (!url) return false;
		const trimmed = url.trim();
		return (
			trimmed !== "" &&
			trimmed !== "***" &&
			trimmed.toLowerCase() !== "none" &&
			trimmed.toLowerCase() !== "null"
		);
	};

	// Check both legacy fields and new databases array
	const hasPostgresLegacy = isValidUrl(project.postgres_url);
	const hasMongoLegacy = isValidUrl(project.mongodb_url);
	
	// Check new format (databases array)
	const hasPostgresNew = project.databases?.some(
		(db) => db.type.toLowerCase() === "postgres" && isValidUrl(db.connection_url)
	) || false;
	const hasMongoNew = project.databases?.some(
		(db) => db.type.toLowerCase() === "mongodb" && isValidUrl(db.connection_url)
	) || false;

	const hasPostgres = hasPostgresLegacy || hasPostgresNew;
	const hasMongo = hasMongoLegacy || hasMongoNew;

	const testConnection = async () => {
		setIsTesting(true);
		setResults(null);

		try {
			console.log("[DatabaseConnectionStatus] Testing connection for project:", project.id);
			console.log("[DatabaseConnectionStatus] Token exists:", !!token);
			console.log("[DatabaseConnectionStatus] Token preview:", token ? `${token.substring(0, 20)}...` : "NO TOKEN");
			console.log("[DatabaseConnectionStatus] Request payload:", { project_id: project.id });
			
			// First, test if we can reach the backend at all
			try {
				console.log("[DatabaseConnectionStatus] Testing ping endpoint first...");
				const pingResult = await apiFetchJson("/projects/test-ping", {
					method: "GET",
					headers: {
						Authorization: `Bearer ${token}`,
					},
				}, logout);
				console.log("[DatabaseConnectionStatus] Ping result:", pingResult);
			} catch (pingError) {
				console.error("[DatabaseConnectionStatus] Ping test failed:", pingError);
			}
			
			const requestBody = {
				project_id: project.id,
			};
			console.log("[DatabaseConnectionStatus] Sending POST request with body:", requestBody);
			console.log("[DatabaseConnectionStatus] Body as JSON string:", JSON.stringify(requestBody));
			
			const result = await apiFetchJson<{
				postgres?: { success: boolean; error?: string; schema_preview?: any };
				mongodb?: { success: boolean; error?: string; schema_preview?: any };
			}>(
				"/projects/test-connection",
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						Authorization: `Bearer ${token}`,
					},
					body: JSON.stringify(requestBody),
				},
				logout,
			);
			console.log("[DatabaseConnectionStatus] Test connection result:", result);

			const formattedResults: { postgres?: string; mongodb?: string } = {};

			if (result.postgres) {
				if (result.postgres.success) {
					const preview = result.postgres.schema_preview;
					const tableCount = preview?.table_count;
					const dbName = preview?.database_name || "database";
					// Handle fast test (table_count is null) vs full introspection
					if (tableCount !== null && tableCount !== undefined) {
						formattedResults.postgres = `Success: Connected to ${dbName} (${tableCount} tables)`;
					} else {
						formattedResults.postgres = `Success: Connected to ${dbName}`;
					}
				} else {
					formattedResults.postgres = `Error: ${
						result.postgres.error || "Connection failed"
					}`;
				}
			}

			if (result.mongodb) {
				if (result.mongodb.success) {
					const preview = result.mongodb.schema_preview;
					const collCount = preview?.collection_count;
					const dbName = preview?.database_name || "database";
					// Handle lightweight test (collection_count is null) vs full introspection
					if (collCount !== null && collCount !== undefined) {
						formattedResults.mongodb = `Success: Connected to ${dbName} (${collCount} collections)`;
					} else {
						formattedResults.mongodb = `Success: Connected to ${dbName}`;
					}
				} else {
					formattedResults.mongodb = `Error: ${
						result.mongodb.error || "Connection failed"
					}`;
				}
			}

			setResults(formattedResults);
		} catch (err) {
			console.error("Test connection error:", err);
			const errorMessage =
				err instanceof Error ? err.message : "Connection test failed";
			setResults({
				postgres: `Error: ${errorMessage}`,
				mongodb: `Error: ${errorMessage}`,
			});
		} finally {
			setIsTesting(false);
		}
	};

	const canTest = hasPostgres || hasMongo;

	// Helper to format raw backend errors into user-friendly messages
	const formatError = (msg: string) => {
		if (msg.includes("'str' object has no attribute 'name'")) {
			return "Configuration Error: The server encountered an invalid database configuration.";
		}
		if (msg.includes("DNS operation timed out")) {
			return "Connection Failed: Could not resolve the database hostname. Please check the URL.";
		}
		return msg;
	};

	return (
		<div className="database-status-section">
			<div
				className="db-status-header"
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					marginBottom: "12px",
				}}
			>
				<label>Database Connections</label>
				<button
					onClick={testConnection}
					className="test-connection-btn"
					disabled={isTesting || !canTest}
					title={
						canTest
							? "Test database connections"
							: "Configure databases to test"
					}
				>
					{isTesting ? "Testing..." : "Test Connections"}
				</button>
			</div>

			{results && (
				<div className="connection-results">
					{results.postgres && (
						<div
							className={`connection-result ${
								results.postgres.includes("Success") ? "success" : "error"
							}`}
						>
							<strong>PostgreSQL:</strong> {formatError(results.postgres)}
						</div>
					)}
					{results.mongodb && (
						<div
							className={`connection-result ${
								results.mongodb.includes("Success") ? "success" : "error"
							}`}
						>
							<strong>MongoDB:</strong> {formatError(results.mongodb)}
						</div>
					)}
				</div>
			)}

			<div className="database-info">
				<div className="db-item">
					<span className="db-label">PostgreSQL</span>
					<span className="db-value">
						{hasPostgres ? "Configured" : "Not configured"}
					</span>
				</div>
				<div className="db-item">
					<span className="db-label">MongoDB</span>
					<span className="db-value">
						{hasMongo ? "Configured" : "Not configured"}
					</span>
				</div>
			</div>
		</div>
	);
}
