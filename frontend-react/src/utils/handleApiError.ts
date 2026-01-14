export async function parseApiError(response: Response): Promise<string> {
	// Try to parse JSON body
	let data: any = null;
	try {
		data = await response.clone().json();
	} catch (e) {
		// Not JSON or empty
		data = null;
	}

	// Common FastAPI error shapes:
	// 1) { detail: "message" }
	// 2) { detail: [ { loc: [...], msg: "...", type: "..." }, ... ] }
	// 3) { detail: { ... } } or { errors: { field: ["msg"] } }
	// 4) { message: "..." } or { error: "..." }

	if (data) {
		if (typeof data.detail === "string") return data.detail;

		if (Array.isArray(data.detail)) {
			// Validation errors from pydantic / FastAPI
			const msgs = data.detail
				.map((item: any) => {
					if (typeof item === "string") return item;
					if (item.msg) return item.msg;
					if (item.message) return item.message;
					if (item.detail) return item.detail;
					return JSON.stringify(item);
				})
				.filter(Boolean);
			if (msgs.length) return msgs.join("; ");
		}

		if (typeof data.message === "string") return data.message;
		if (typeof data.error === "string") return data.error;

		// Flatten errors object if present
		if (typeof data.errors === "object" && data.errors !== null) {
			const entries = Object.entries(data.errors).map(([k, v]) => {
				if (Array.isArray(v)) return `${k}: ${v.join(", ")}`;
				return `${k}: ${String(v)}`;
			});
			if (entries.length) return entries.join("; ");
		}

		// Fallback: if detail exists but is object
		if (data.detail && typeof data.detail === "object") {
			try {
				return JSON.stringify(data.detail);
			} catch (e) {
				// ignore
			}
		}
	}

	// Use status text if available
	if (response.status) {
		return `Request failed (${response.status} ${response.statusText || ""})`;
	}

	return "An unknown error occurred";
}
