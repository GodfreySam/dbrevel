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

	const testConnection = async () => {
		setIsTesting(true);
		setResults(null);

		try {
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
					body: JSON.stringify({
						project_id: project.id,
					}),
				},
				logout,
			);

			const formattedResults: { postgres?: string; mongodb?: string } = {};

			if (result.postgres) {
				if (result.postgres.success) {
					const preview = result.postgres.schema_preview;
					const tableCount = preview?.table_count || 0;
					const dbName = preview?.database_name || "database";
					formattedResults.postgres = `Success: Connected to ${dbName} (${tableCount} tables)`;
				} else {
					formattedResults.postgres = `Error: ${
						result.postgres.error || "Connection failed"
					}`;
				}
			}

			if (result.mongodb) {
				if (result.mongodb.success) {
					const preview = result.mongodb.schema_preview;
					const collCount = preview?.collection_count || 0;
					const dbName = preview?.database_name || "database";
					formattedResults.mongodb = `Success: Connected to ${dbName} (${collCount} collections)`;
				} else {
					formattedResults.mongodb = `Error: ${
						result.mongodb.error || "Connection failed"
					}`;
				}
			}

			setResults(formattedResults);
		} catch (err) {
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

	const hasPostgres =
		(project.postgres_url || "").trim() !== "" &&
		project.postgres_url !== "***";
	const hasMongo =
		(project.mongodb_url || "").trim() !== "" && project.mongodb_url !== "***";
	const canTest = hasPostgres || hasMongo;

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
							<strong>PostgreSQL:</strong> {results.postgres}
						</div>
					)}
					{results.mongodb && (
						<div
							className={`connection-result ${
								results.mongodb.includes("Success") ? "success" : "error"
							}`}
						>
							<strong>MongoDB:</strong> {results.mongodb}
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
