import {
	createContext,
	ReactNode,
	useCallback,
	useContext,
	useEffect,
	useState,
} from "react";
import { apiFetch, apiFetchJson } from "../utils/api";
import { parseApiError } from "../utils/handleApiError";

interface User {
	id: string;
	email: string;
	account_id: string;
	account_name: string;
	created_at: string;
	last_login?: string;
	email_verified?: boolean;
	role?: string; // "user" or "admin"
}

interface AuthContextType {
	user: User | null;
	token: string | null;
	isAuthenticated: boolean;
	isAdmin: boolean;
	loading: boolean;
	login: (email: string, password: string) => Promise<void>;
	register: (email: string, password: string, name: string) => Promise<string>; // Returns email for verification
	verifyEmail: (email: string, otp: string) => Promise<void>;
	resendVerification: (email: string) => Promise<void>;
	logout: () => void;
	refreshUser: () => Promise<void>;
	adminRequestOTP: (email: string) => Promise<void>;
	adminVerifyOTP: (email: string, otp: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "dbrevel_auth_token";
const USER_KEY = "dbrevel_user";

export function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<User | null>(null);
	const [token, setToken] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);

	// Load from localStorage on mount and validate token
	useEffect(() => {
		const loadAndValidateToken = async () => {
			const storedToken = localStorage.getItem(TOKEN_KEY);
			const storedUser = localStorage.getItem(USER_KEY);

			if (storedToken && storedUser) {
				setToken(storedToken);
				try {
					const parsedUser = JSON.parse(storedUser);
					setUser(parsedUser);

					// Validate token by fetching user info
					// This ensures the token is still valid and user state is up-to-date
					try {
						const { apiFetchJson } = await import("../utils/api");
						const userData = await apiFetchJson<User>(
							"/auth/me",
							{
								headers: {
									Authorization: `Bearer ${storedToken}`,
								},
							},
							() => {
								// Token invalid, clear it
								localStorage.removeItem(TOKEN_KEY);
								localStorage.removeItem(USER_KEY);
								setToken(null);
								setUser(null);
							},
						);
						// Update user with latest data from server
						setUser(userData);
						localStorage.setItem(USER_KEY, JSON.stringify(userData));
					} catch (error) {
						// Token validation failed (401/403/404), clear invalid token
						console.warn("Token validation failed on app load:", error);
						localStorage.removeItem(TOKEN_KEY);
						localStorage.removeItem(USER_KEY);
						setToken(null);
						setUser(null);
					}
				} catch {
					// Invalid stored user, clear it
					localStorage.removeItem(TOKEN_KEY);
					localStorage.removeItem(USER_KEY);
					setToken(null);
					setUser(null);
				}
			}
			setLoading(false);
		};

		loadAndValidateToken();
	}, []);

	const login = async (email: string, password: string) => {
		// Clear any existing tokens before login to avoid conflicts
		localStorage.removeItem(TOKEN_KEY);
		localStorage.removeItem(USER_KEY);
		setToken(null);
		setUser(null);

		const response = await apiFetch("/auth/login", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ email, password }),
		});

		if (!response.ok) {
			const msg = await parseApiError(response);
			if (response.status === 403 && msg?.toLowerCase().includes("verified")) {
				throw new Error("EMAIL_NOT_VERIFIED");
			}
			throw new Error(msg || "Login failed");
		}

		const data = await response.json();
		setToken(data.access_token);
		setUser(data.user);
		localStorage.setItem(TOKEN_KEY, data.access_token);
		localStorage.setItem(USER_KEY, JSON.stringify(data.user));
	};

	const register = async (
		email: string,
		password: string,
		name: string,
	): Promise<string> => {
		await apiFetchJson<void>("/auth/register", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ email, password, name }),
		});
		return email;
	};

	const verifyEmail = async (email: string, otp: string) => {
		const data = await apiFetchJson<{ access_token: string; user: User }>(
			"/auth/verify-email",
			{
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ email, otp }),
			},
		);

		// Clear any old tokens and user data before setting new one
		// This ensures we don't have stale tokens from before verification
		localStorage.removeItem(TOKEN_KEY);
		localStorage.removeItem(USER_KEY);
		setToken(null);
		setUser(null);

		// Set new token and user from verification response
		const newToken = data.access_token;
		const newUser = data.user;

		setToken(newToken);
		setUser(newUser);
		localStorage.setItem(TOKEN_KEY, newToken);
		localStorage.setItem(USER_KEY, JSON.stringify(newUser));

		// Validate the new token immediately to ensure it works
		try {
			const { apiFetchJson } = await import("../utils/api");
			const validatedUser = await apiFetchJson<User>(
				"/auth/me",
				{
					headers: {
						Authorization: `Bearer ${newToken}`,
					},
				},
				() => {
					// If validation fails, clear everything
					localStorage.removeItem(TOKEN_KEY);
					localStorage.removeItem(USER_KEY);
					setToken(null);
					setUser(null);
				},
			);
			// Update with validated user data
			setUser(validatedUser);
			localStorage.setItem(USER_KEY, JSON.stringify(validatedUser));
			console.log(
				"Email verified successfully. Token validated and user updated.",
			);
		} catch (error) {
			console.error("Token validation failed after email verification:", error);
			// Clear invalid token
			localStorage.removeItem(TOKEN_KEY);
			localStorage.removeItem(USER_KEY);
			setToken(null);
			setUser(null);
			throw new Error(
				"Email verification succeeded but token validation failed. Please try logging in.",
			);
		}
	};

	const resendVerification = async (email: string) => {
		// FastAPI POST with simple type expects it in the body as form data or query
		// Using query parameter for consistency
		await apiFetchJson<void>(
			`/auth/resend-verification?email=${encodeURIComponent(email)}`,
			{ method: "POST", headers: { "Content-Type": "application/json" } },
		);
	};

	const logout = useCallback(() => {
		setToken(null);
		setUser(null);
		localStorage.removeItem(TOKEN_KEY);
		localStorage.removeItem(USER_KEY);
	}, []);

	const refreshUser = useCallback(async () => {
		if (!token) return;

		try {
			const { apiFetchJson } = await import("../utils/api");
			const userData = await apiFetchJson<User>(
				"/auth/me",
				{
					headers: {
						Authorization: `Bearer ${token}`,
					},
				},
				logout, // Handle 401 by logging out
			);
			setUser(userData);
			localStorage.setItem(USER_KEY, JSON.stringify(userData));
		} catch {
			// Token invalid or other error, logout
			logout();
		}
	}, [token, logout]);

	// Admin authentication methods
	const adminRequestOTP = async (email: string) => {
		await apiFetchJson<void>("/admin/request-otp", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ email }),
		});
	};

	const adminVerifyOTP = async (email: string, otp: string) => {
		const data = await apiFetchJson<{ access_token: string; user: User }>(
			"/admin/verify-otp",
			{
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ email, otp }),
			},
		);
		setToken(data.access_token);
		setUser(data.user);
		localStorage.setItem(TOKEN_KEY, data.access_token);
		localStorage.setItem(USER_KEY, JSON.stringify(data.user));
	};

	// Compute isAdmin from user role
	const isAdmin = user?.role === "admin";

	return (
		<AuthContext.Provider
			value={{
				user,
				token,
				isAuthenticated: !!user && !!token,
				isAdmin,
				loading,
				login,
				register,
				verifyEmail,
				resendVerification,
				logout,
				refreshUser,
				adminRequestOTP,
				adminVerifyOTP,
			}}
		>
			{children}
		</AuthContext.Provider>
	);
}

export function useAuth() {
	const context = useContext(AuthContext);
	if (context === undefined) {
		throw new Error("useAuth must be used within an AuthProvider");
	}
	return context;
}
