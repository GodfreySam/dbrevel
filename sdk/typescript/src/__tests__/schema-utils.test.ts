/**
 * Unit tests for schema utilities
 */
import {
	getTableNames,
	getCollectionNames,
	getColumnNames,
	getColumn,
	getTable,
	getCollection,
	hasTable,
	hasCollection,
	getPrimaryKeyColumns,
	getForeignKeyColumns,
	getDatabaseNames,
	getDatabaseSchema,
	findTablesByColumn,
	getTableRelationships,
} from "../utils/schema";
import type {
	DatabaseSchema,
	SchemasResponse,
	TableSchema,
	ColumnSchema,
} from "../types/schema";

describe("Schema Utilities", () => {
	const mockTableSchema: TableSchema = {
		name: "users",
		columns: [
			{
				name: "id",
				type: "integer",
				primary_key: true,
			},
			{
				name: "email",
				type: "varchar",
				nullable: false,
			},
			{
				name: "name",
				type: "varchar",
			},
			{
				name: "role_id",
				type: "integer",
				foreign_key: {
					table: "roles",
					column: "id",
				},
			},
		],
	};

	const mockPostgresSchema: DatabaseSchema = {
		name: "postgres",
		type: "postgresql",
		tables: [mockTableSchema],
	};

	const mockMongoSchema: DatabaseSchema = {
		name: "mongo",
		type: "mongodb",
		collections: [
			{
				name: "products",
				fields: [
					{ name: "name", type: "string" },
					{ name: "price", type: "number" },
				],
			},
		],
	};

	const mockSchemasResponse: SchemasResponse = {
		databases: {
			postgres: mockPostgresSchema,
			mongo: mockMongoSchema,
		},
	};

	describe("getTableNames", () => {
		it("should return table names from PostgreSQL schema", () => {
			const names = getTableNames(mockPostgresSchema);
			expect(names).toEqual(["users"]);
		});

		it("should return empty array for MongoDB schema", () => {
			const names = getTableNames(mockMongoSchema);
			expect(names).toEqual([]);
		});
	});

	describe("getCollectionNames", () => {
		it("should return collection names from MongoDB schema", () => {
			const names = getCollectionNames(mockMongoSchema);
			expect(names).toEqual(["products"]);
		});

		it("should return empty array for PostgreSQL schema", () => {
			const names = getCollectionNames(mockPostgresSchema);
			expect(names).toEqual([]);
		});
	});

	describe("getColumnNames", () => {
		it("should return column names", () => {
			const names = getColumnNames(mockTableSchema);
			expect(names).toEqual(["id", "email", "name", "role_id"]);
		});
	});

	describe("getColumn", () => {
		it("should return column schema", () => {
			const column = getColumn(mockTableSchema, "email");
			expect(column?.name).toBe("email");
			expect(column?.type).toBe("varchar");
		});

		it("should return undefined for non-existent column", () => {
			const column = getColumn(mockTableSchema, "nonexistent");
			expect(column).toBeUndefined();
		});
	});

	describe("getTable", () => {
		it("should return table schema", () => {
			const table = getTable(mockPostgresSchema, "users");
			expect(table?.name).toBe("users");
		});

		it("should return undefined for non-existent table", () => {
			const table = getTable(mockPostgresSchema, "nonexistent");
			expect(table).toBeUndefined();
		});
	});

	describe("getCollection", () => {
		it("should return collection schema", () => {
			const collection = getCollection(mockMongoSchema, "products");
			expect(collection?.name).toBe("products");
		});

		it("should return undefined for non-existent collection", () => {
			const collection = getCollection(mockMongoSchema, "nonexistent");
			expect(collection).toBeUndefined();
		});
	});

	describe("hasTable", () => {
		it("should return true for existing table", () => {
			expect(hasTable(mockPostgresSchema, "users")).toBe(true);
		});

		it("should return false for non-existent table", () => {
			expect(hasTable(mockPostgresSchema, "nonexistent")).toBe(false);
		});
	});

	describe("hasCollection", () => {
		it("should return true for existing collection", () => {
			expect(hasCollection(mockMongoSchema, "products")).toBe(true);
		});

		it("should return false for non-existent collection", () => {
			expect(hasCollection(mockMongoSchema, "nonexistent")).toBe(false);
		});
	});

	describe("getPrimaryKeyColumns", () => {
		it("should return primary key columns", () => {
			const primaryKeys = getPrimaryKeyColumns(mockTableSchema);
			expect(primaryKeys).toHaveLength(1);
			expect(primaryKeys[0].name).toBe("id");
		});
	});

	describe("getForeignKeyColumns", () => {
		it("should return foreign key columns", () => {
			const foreignKeys = getForeignKeyColumns(mockTableSchema);
			expect(foreignKeys).toHaveLength(1);
			expect(foreignKeys[0].name).toBe("role_id");
		});
	});

	describe("getDatabaseNames", () => {
		it("should return all database names", () => {
			const names = getDatabaseNames(mockSchemasResponse);
			expect(names).toEqual(["postgres", "mongo"]);
		});
	});

	describe("getDatabaseSchema", () => {
		it("should return database schema", () => {
			const schema = getDatabaseSchema(mockSchemasResponse, "postgres");
			expect(schema?.name).toBe("postgres");
		});

		it("should return undefined for non-existent database", () => {
			const schema = getDatabaseSchema(mockSchemasResponse, "nonexistent");
			expect(schema).toBeUndefined();
		});
	});

	describe("findTablesByColumn", () => {
		it("should find tables containing column", () => {
			const results = findTablesByColumn(mockSchemasResponse, "email");
			expect(results).toHaveLength(1);
			expect(results[0].database).toBe("postgres");
			expect(results[0].table.name).toBe("users");
		});

		it("should return empty array for non-existent column", () => {
			const results = findTablesByColumn(mockSchemasResponse, "nonexistent");
			expect(results).toEqual([]);
		});
	});

	describe("getTableRelationships", () => {
		it("should return table relationships", () => {
			const relationships = getTableRelationships(mockPostgresSchema, "users");
			expect(relationships).toHaveLength(1);
			expect(relationships[0].column).toBe("role_id");
			expect(relationships[0].references.table).toBe("roles");
		});

		it("should return empty array for non-existent table", () => {
			const relationships = getTableRelationships(
				mockPostgresSchema,
				"nonexistent",
			);
			expect(relationships).toEqual([]);
		});
	});
});
