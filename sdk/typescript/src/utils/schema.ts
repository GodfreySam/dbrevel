/**
 * Schema utility functions
 */
import type {
	CollectionSchema,
	ColumnSchema,
	DatabaseSchema,
	SchemasResponse,
	TableSchema,
} from "../types/schema";

/**
 * Get all table names from a database schema
 */
export function getTableNames(schema: DatabaseSchema): string[] {
	if (schema.type === "postgresql" && schema.tables) {
		return schema.tables.map((table) => table.name);
	}
	return [];
}

/**
 * Get all collection names from a database schema
 */
export function getCollectionNames(schema: DatabaseSchema): string[] {
	if (schema.type === "mongodb" && schema.collections) {
		return schema.collections.map((collection) => collection.name);
	}
	return [];
}

/**
 * Get column names from a table schema
 */
export function getColumnNames(table: TableSchema): string[] {
	return table.columns.map((column) => column.name);
}

/**
 * Get column schema by name
 */
export function getColumn(
	table: TableSchema,
	columnName: string,
): ColumnSchema | undefined {
	return table.columns.find((col) => col.name === columnName);
}

/**
 * Get table schema by name
 */
export function getTable(
	schema: DatabaseSchema,
	tableName: string,
): TableSchema | undefined {
	if (schema.type === "postgresql" && schema.tables) {
		return schema.tables.find((table) => table.name === tableName);
	}
	return undefined;
}

/**
 * Get collection schema by name
 */
export function getCollection(
	schema: DatabaseSchema,
	collectionName: string,
): CollectionSchema | undefined {
	if (schema.type === "mongodb" && schema.collections) {
		return schema.collections.find(
			(collection) => collection.name === collectionName,
		);
	}
	return undefined;
}

/**
 * Check if a table exists in a schema
 */
export function hasTable(schema: DatabaseSchema, tableName: string): boolean {
	return getTable(schema, tableName) !== undefined;
}

/**
 * Check if a collection exists in a schema
 */
export function hasCollection(
	schema: DatabaseSchema,
	collectionName: string,
): boolean {
	return getCollection(schema, collectionName) !== undefined;
}

/**
 * Get primary key columns for a table
 */
export function getPrimaryKeyColumns(table: TableSchema): ColumnSchema[] {
	return table.columns.filter((col) => col.primary_key === true);
}

/**
 * Get foreign key columns for a table
 */
export function getForeignKeyColumns(table: TableSchema): ColumnSchema[] {
	return table.columns.filter((col) => col.foreign_key !== undefined);
}

/**
 * Get all database names from schemas response
 */
export function getDatabaseNames(schemas: SchemasResponse): string[] {
	return Object.keys(schemas.databases);
}

/**
 * Get schema for a specific database from schemas response
 */
export function getDatabaseSchema(
	schemas: SchemasResponse,
	databaseName: string,
): DatabaseSchema | undefined {
	return schemas.databases[databaseName];
}

/**
 * Find tables/collections by column/field name across all databases
 */
export function findTablesByColumn(
	schemas: SchemasResponse,
	columnName: string,
): Array<{ database: string; table: TableSchema }> {
	const results: Array<{ database: string; table: TableSchema }> = [];

	for (const [dbName, schema] of Object.entries(schemas.databases)) {
		if (schema.type === "postgresql" && schema.tables) {
			for (const table of schema.tables) {
				if (table.columns.some((col) => col.name === columnName)) {
					results.push({ database: dbName, table });
				}
			}
		}
	}

	return results;
}

/**
 * Find collections by field name across all databases
 */
export function findCollectionsByField(
	schemas: SchemasResponse,
	fieldName: string,
): Array<{ database: string; collection: CollectionSchema }> {
	const results: Array<{ database: string; collection: CollectionSchema }> = [];

	for (const [dbName, schema] of Object.entries(schemas.databases)) {
		if (schema.type === "mongodb" && schema.collections) {
			for (const collection of schema.collections) {
				if (collection.fields?.some((field) => field.name === fieldName)) {
					results.push({ database: dbName, collection });
				}
			}
		}
	}

	return results;
}

/**
 * Get all relationships (foreign keys) for a table
 */
export function getTableRelationships(
	schema: DatabaseSchema,
	tableName: string,
): Array<{
	column: string;
	references: { table: string; column: string };
}> {
	const table = getTable(schema, tableName);
	if (!table) {
		return [];
	}

	return table.columns
		.filter((col) => col.foreign_key)
		.map((col) => ({
			column: col.name,
			references: col.foreign_key!,
		}));
}
