/**
 * Schema Helper - Convenience class for working with schemas
 */
import type {
	CollectionSchema,
	ColumnSchema,
	DatabaseSchema,
	SchemasResponse,
	TableSchema,
} from "./types/schema";
import {
	findCollectionsByField,
	findTablesByColumn,
	getCollection,
	getCollectionNames,
	getColumn,
	getColumnNames,
	getDatabaseNames,
	getDatabaseSchema,
	getForeignKeyColumns,
	getPrimaryKeyColumns,
	getTable,
	getTableNames,
	getTableRelationships,
	hasCollection,
	hasTable,
} from "./utils/schema";

export class SchemaHelper {
	private schemas: SchemasResponse;

	constructor(schemas: SchemasResponse) {
		this.schemas = schemas;
	}

	/**
	 * Get all database names
	 */
	getDatabaseNames(): string[] {
		return getDatabaseNames(this.schemas);
	}

	/**
	 * Get schema for a specific database
	 */
	getDatabaseSchema(databaseName: string): DatabaseSchema | undefined {
		return getDatabaseSchema(this.schemas, databaseName);
	}

	/**
	 * Get all table names from a database
	 */
	getTableNames(databaseName: string): string[] {
		const schema = this.getDatabaseSchema(databaseName);
		return schema ? getTableNames(schema) : [];
	}

	/**
	 * Get all collection names from a database
	 */
	getCollectionNames(databaseName: string): string[] {
		const schema = this.getDatabaseSchema(databaseName);
		return schema ? getCollectionNames(schema) : [];
	}

	/**
	 * Get table schema
	 */
	getTable(databaseName: string, tableName: string): TableSchema | undefined {
		const schema = this.getDatabaseSchema(databaseName);
		return schema ? getTable(schema, tableName) : undefined;
	}

	/**
	 * Get collection schema
	 */
	getCollection(
		databaseName: string,
		collectionName: string,
	): CollectionSchema | undefined {
		const schema = this.getDatabaseSchema(databaseName);
		return schema ? getCollection(schema, collectionName) : undefined;
	}

	/**
	 * Get column names from a table
	 */
	getColumnNames(databaseName: string, tableName: string): string[] {
		const table = this.getTable(databaseName, tableName);
		return table ? getColumnNames(table) : [];
	}

	/**
	 * Get column schema
	 */
	getColumn(
		databaseName: string,
		tableName: string,
		columnName: string,
	): ColumnSchema | undefined {
		const table = this.getTable(databaseName, tableName);
		return table ? getColumn(table, columnName) : undefined;
	}

	/**
	 * Check if table exists
	 */
	hasTable(databaseName: string, tableName: string): boolean {
		const schema = this.getDatabaseSchema(databaseName);
		return schema ? hasTable(schema, tableName) : false;
	}

	/**
	 * Check if collection exists
	 */
	hasCollection(databaseName: string, collectionName: string): boolean {
		const schema = this.getDatabaseSchema(databaseName);
		return schema ? hasCollection(schema, collectionName) : false;
	}

	/**
	 * Get primary key columns for a table
	 */
	getPrimaryKeyColumns(
		databaseName: string,
		tableName: string,
	): ColumnSchema[] {
		const table = this.getTable(databaseName, tableName);
		return table ? getPrimaryKeyColumns(table) : [];
	}

	/**
	 * Get foreign key columns for a table
	 */
	getForeignKeyColumns(
		databaseName: string,
		tableName: string,
	): ColumnSchema[] {
		const table = this.getTable(databaseName, tableName);
		return table ? getForeignKeyColumns(table) : [];
	}

	/**
	 * Get table relationships (foreign keys)
	 */
	getTableRelationships(
		databaseName: string,
		tableName: string,
	): Array<{
		column: string;
		references: { table: string; column: string };
	}> {
		const schema = this.getDatabaseSchema(databaseName);
		return schema ? getTableRelationships(schema, tableName) : [];
	}

	/**
	 * Find tables containing a specific column name
	 */
	findTablesByColumn(columnName: string): Array<{
		database: string;
		table: TableSchema;
	}> {
		return findTablesByColumn(this.schemas, columnName);
	}

	/**
	 * Find collections containing a specific field name
	 */
	findCollectionsByField(fieldName: string): Array<{
		database: string;
		collection: CollectionSchema;
	}> {
		return findCollectionsByField(this.schemas, fieldName);
	}

	/**
	 * Get all schemas (raw access)
	 */
	getSchemas(): SchemasResponse {
		return this.schemas;
	}
}
