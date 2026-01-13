/**
 * Schema-related types
 */

export interface ColumnSchema {
	name: string;
	type: string;
	nullable?: boolean;
	default?: any;
	primary_key?: boolean;
	foreign_key?: {
		table: string;
		column: string;
	};
}

export interface TableSchema {
	name: string;
	columns: ColumnSchema[];
	indexes?: Array<{
		name: string;
		columns: string[];
		unique?: boolean;
	}>;
}

export interface CollectionSchema {
	name: string;
	fields?: Array<{
		name: string;
		type: string;
		required?: boolean;
	}>;
	indexes?: Array<{
		name: string;
		fields: string[];
		unique?: boolean;
	}>;
}

export interface DatabaseSchema {
	name: string;
	type: "postgresql" | "mongodb";
	tables?: TableSchema[];
	collections?: CollectionSchema[];
}

export interface SchemasResponse {
	databases: Record<string, DatabaseSchema>;
}
