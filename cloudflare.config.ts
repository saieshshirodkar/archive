import { defineConfig } from "cf/config";

/**
 * Secret-like files were detected but not read or migrated: .env.local. Only `secrets.required` entries are migrated.
 * @see https://developers.cloudflare.com/workers/configuration/secrets/
 */

export default defineConfig({
	worker: {
		name: "saiesh-archive",
		compatibilityDate: "2026-11-14",
	},
});
