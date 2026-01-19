/**
 * Schema-related types for database introspection
 * @packageDocumentation
 */

/**
 * Schema information for a PostgreSQL table column
 *
 * @example
 * ```typescript
 * const column: ColumnSchema = {
 *   name: "user_id",
 *   type: "integer",
 *   nullable: false,
 *   primary_key: true
 * };
 * ```
 */
export interface ColumnSchema {
	/** Column name */
	name: string;
	/** SQL data type (e.g., "integer", "varchar", "timestamp") */
	type: string;
	/** Whether the column allows NULL values */
	nullable?: boolean;
	/** Default value for the column */
	default?: any;
	/** Whether this column is a primary key */
	primary_key?: boolean;
	/** Foreign key reference if this column references another table */
	foreign_key?: {
		/** Referenced table name */
		table: string;
		/** Referenced column name */
		column: string;
	};
}

/**
 * Schema information for a PostgreSQL table
 *
 * @example
 * ```typescript
 * const table: TableSchema = {
 *   name: "users",
 *   columns: [
 *     { name: "id", type: "integer", primary_key: true },
 *     { name: "email", type: "varchar", nullable: false }
 *   ],
 *   indexes: [
 *     { name: "users_email_idx", columns: ["email"], unique: true }
 *   ]
 * };
 * ```
 */
export interface TableSchema {
	/** Table name */
	name: string;
	/** List of columns in the table */
	columns: ColumnSchema[];
	/** Indexes defined on the table */
	indexes?: Array<{
		/** Index name */
		name: string;
		/** Columns included in the index */
		columns: string[];
		/** Whether this is a unique index */
		unique?: boolean;
	}>;
}

/**
 * Schema information for a MongoDB collection
 *
 * @example
 * ```typescript
 * const collection: CollectionSchema = {
 *   name: "orders",
 *   fields: [
 *     { name: "_id", type: "ObjectId", required: true },
 *     { name: "total", type: "number", required: true }
 *   ],
 *   indexes: [
 *     { name: "created_at_idx", fields: ["created_at"] }
 *   ]
 * };
 * ```
 */
export interface CollectionSchema {
	/** Collection name */
	name: string;
	/** Inferred fields from document samples */
	fields?: Array<{
		/** Field name */
		name: string;
		/** Inferred BSON type */
		type: string;
		/** Whether the field appears in all documents */
		required?: boolean;
	}>;
	/** Indexes defined on the collection */
	indexes?: Array<{
		/** Index name */
		name: string;
		/** Fields included in the index */
		fields: string[];
		/** Whether this is a unique index */
		unique?: boolean;
	}>;
}

/**
 * Complete schema for a database (PostgreSQL or MongoDB)
 *
 * @example
 * ```typescript
 * const schema: DatabaseSchema = {
 *   name: "postgres",
 *   type: "postgresql",
 *   tables: [{ name: "users", columns: [...] }]
 * };
 * ```
 */
export interface DatabaseSchema {
	/** Database identifier name */
	name: string;
	/** Database type */
	type: "postgresql" | "mongodb";
	/** Tables (PostgreSQL only) */
	tables?: TableSchema[];
	/** Collections (MongoDB only) */
	collections?: CollectionSchema[];
}

/**
 * Response from the schema introspection endpoint
 *
 * @example
 * ```typescript
 * const schemas = await client.getSchemas();
 * const postgresSchema = schemas.databases.postgres;
 * const mongoSchema = schemas.databases.mongodb;
 * ```
 */
export interface SchemasResponse {
	/** Map of database name to its schema */
	databases: Record<string, DatabaseSchema>;
}
