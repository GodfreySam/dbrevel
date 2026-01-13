/**
 * Language Support Table Component
 * Displays SDK language support status (Available vs Coming Soon)
 */

interface LanguageSupport {
	language: string;
	status: "available" | "coming-soon";
	link?: string;
}

const languages: LanguageSupport[] = [
	{
		language: "TypeScript/JavaScript",
		status: "available",
		link: "https://www.npmjs.com/package/@dbrevel/sdk",
	},
	{ language: "Python", status: "coming-soon" },
	{ language: "Go", status: "coming-soon" },
	{ language: "Java", status: "coming-soon" },
	{ language: "C# / .NET", status: "coming-soon" },
	{ language: "Ruby", status: "coming-soon" },
	{ language: "PHP", status: "coming-soon" },
	{ language: "Rust", status: "coming-soon" },
	{ language: "Swift", status: "coming-soon" },
	{ language: "Kotlin", status: "coming-soon" },
];

interface LanguageSupportTableProps {
	className?: string;
}

export default function LanguageSupportTable({
	className = "",
}: LanguageSupportTableProps) {
	return (
		<div className={`language-support-table ${className}`}>
			<h4>SDK Language Support</h4>
			<p className="language-support-note">
				<strong>Note:</strong> The DbRevel API supports all languages via
				standard HTTP requests. Official SDKs provide type safety, error
				handling, and convenience methods.
			</p>
			<table className="sdk-languages-table">
				<thead>
					<tr>
						<th>Language</th>
						<th>Official SDK</th>
						<th>API Support</th>
					</tr>
				</thead>
				<tbody>
					{languages.map((lang) => (
						<tr key={lang.language}>
							<td>
								{lang.link ? (
									<a
										href={lang.link}
										target="_blank"
										rel="noopener noreferrer"
										className="language-link"
									>
										{lang.language}
									</a>
								) : (
									lang.language
								)}
							</td>
							<td>
								<span className={`status-badge status-${lang.status}`}>
									{lang.status === "available" ? "Available" : "Coming Soon"}
								</span>
							</td>
							<td>
								<span className="status-badge status-available">
									✓ Supported
								</span>
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}
