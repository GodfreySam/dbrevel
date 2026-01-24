import { useEffect } from "react";
import "./DatabaseInput.css";

export type DatabaseType = "postgres" | "mongodb" | "mysql" | "redis" | "other";

export interface DatabaseConfig {
	id: string; // Unique ID for this database entry
	type: DatabaseType;
	connection_url: string;
}

interface DatabaseInputProps {
	databases: DatabaseConfig[];
	onChange: (databases: DatabaseConfig[]) => void;
	existingDatabases?: { postgres_url?: string; mongodb_url?: string }; // For backward compatibility
}

const DATABASE_TYPES: { value: DatabaseType; label: string; placeholder: string }[] = [
	{ value: "postgres", label: "PostgreSQL", placeholder: "postgresql://user:password@host:5432/dbname" },
	{ value: "mongodb", label: "MongoDB", placeholder: "mongodb+srv://user:password@host/dbname" },
	{ value: "mysql", label: "MySQL", placeholder: "mysql://user:password@host:3306/dbname" },
	{ value: "redis", label: "Redis", placeholder: "redis://user:password@host:6379" },
	{ value: "other", label: "Other", placeholder: "connection://string" },
];

export default function DatabaseInput({
	databases,
	onChange,
	existingDatabases,
}: DatabaseInputProps) {
	// Initialize from existing databases (backward compatibility) - only if databases is empty
	// This is a fallback for cases where parent component doesn't initialize
	useEffect(() => {
		if (databases.length === 0 && existingDatabases) {
			const initial: DatabaseConfig[] = [];
			if (existingDatabases.postgres_url && existingDatabases.postgres_url !== "***" && existingDatabases.postgres_url.trim()) {
				initial.push({
					id: `existing-postgres-${Date.now()}`,
					type: "postgres",
					connection_url: "", // Don't show masked URLs
				});
			}
			if (existingDatabases.mongodb_url && existingDatabases.mongodb_url !== "***" && existingDatabases.mongodb_url.trim()) {
				initial.push({
					id: `existing-mongodb-${Date.now()}`,
					type: "mongodb",
					connection_url: "", // Don't show masked URLs
				});
			}
			if (initial.length > 0) {
				onChange(initial);
			}
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []); // Only run once on mount

	const addDatabase = () => {
		const newDb: DatabaseConfig = {
			id: `db-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
			type: "postgres",
			connection_url: "",
		};
		onChange([...databases, newDb]);
	};

	const removeDatabase = (id: string) => {
		onChange(databases.filter((db) => db.id !== id));
	};

	const updateDatabase = (id: string, updates: Partial<DatabaseConfig>) => {
		onChange(
			databases.map((db) => (db.id === id ? { ...db, ...updates } : db))
		);
	};

	return (
		<div className="database-input-container">
			<div className="database-input-header">
				<label>Databases</label>
				<button
					type="button"
					onClick={addDatabase}
					className="add-database-btn"
				>
					+ Add Database
				</button>
			</div>

			{databases.length === 0 && (
				<div className="database-input-empty">
					<p>No databases configured. Click "Add Database" to add one.</p>
				</div>
			)}

			{databases.map((db) => (
				<div key={db.id} className="database-input-item">
					<div className="database-input-row">
						<div className="database-type-select">
							<label htmlFor={`db-type-${db.id}`}>Type</label>
							<select
								id={`db-type-${db.id}`}
								value={db.type}
								onChange={(e) =>
									updateDatabase(db.id, {
										type: e.target.value as DatabaseType,
										connection_url: "", // Clear URL when type changes
									})
								}
							>
								{DATABASE_TYPES.map((type) => (
									<option key={type.value} value={type.value}>
										{type.label}
									</option>
								))}
							</select>
						</div>

						<div className="database-url-input">
							<label htmlFor={`db-url-${db.id}`}>
								Connection URL
								{db.id.startsWith("existing-") && !db.connection_url && (
									<span className="existing-db-badge"> (Existing - leave blank to keep)</span>
								)}
							</label>
							<div className="database-url-row">
								<input
									type="text"
									id={`db-url-${db.id}`}
									value={db.connection_url}
									onChange={(e) =>
										updateDatabase(db.id, {
											connection_url: e.target.value,
										})
									}
									placeholder={
										db.id.startsWith("existing-") && !db.connection_url
											? "Leave blank to keep existing, or enter new URL to update"
											: DATABASE_TYPES.find((t) => t.value === db.type)
												?.placeholder || "Enter connection string"
									}
								/>
								<button
									type="button"
									onClick={() => removeDatabase(db.id)}
									className="remove-database-btn"
									title="Remove database"
								>
									×
								</button>
							</div>
						</div>
					</div>
				</div>
			))}

			<span className="form-hint">
				You can add multiple databases of the same or different types. At least one database is recommended.
			</span>
		</div>
	);
}
