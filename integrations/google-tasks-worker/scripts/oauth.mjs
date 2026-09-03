import { createHash, randomBytes } from "node:crypto";
import { readFile } from "node:fs/promises";
import http from "node:http";
import { spawn } from "node:child_process";

const credentialsPath = process.argv[2];
if (!credentialsPath) {
  console.error("Usage: npm run oauth -- /absolute/path/to/google-oauth-client.json");
  process.exit(1);
}

const credentials = JSON.parse(await readFile(credentialsPath, "utf8"));
const client = credentials.installed ?? credentials.web;
if (!client?.client_id || !client?.client_secret) {
  throw new Error("Expected a Google OAuth client JSON containing installed/web client_id and client_secret.");
}

const port = 53682;
const redirectUri = `http://127.0.0.1:${port}/oauth2/callback`;
const scope = "https://www.googleapis.com/auth/tasks";
const state = randomBytes(24).toString("hex");
const codeVerifier = randomBytes(48).toString("base64url");
const codeChallenge = createHash("sha256").update(codeVerifier).digest("base64url");

const auth = new URL("https://accounts.google.com/o/oauth2/v2/auth");
auth.searchParams.set("client_id", client.client_id);
auth.searchParams.set("redirect_uri", redirectUri);
auth.searchParams.set("response_type", "code");
auth.searchParams.set("scope", scope);
auth.searchParams.set("access_type", "offline");
auth.searchParams.set("prompt", "consent");
auth.searchParams.set("state", state);
auth.searchParams.set("code_challenge", codeChallenge);
auth.searchParams.set("code_challenge_method", "S256");

function openBrowser(url) {
  const command = process.platform === "darwin" ? "open" : process.platform === "win32" ? "cmd" : "xdg-open";
  const args = process.platform === "win32" ? ["/c", "start", "", url] : [url];
  const child = spawn(command, args, { detached: true, stdio: "ignore" });
  child.unref();
}

const code = await new Promise((resolve, reject) => {
  const server = http.createServer((req, res) => {
    try {
      const url = new URL(req.url, redirectUri);
      if (url.pathname !== "/oauth2/callback") {
        res.writeHead(404).end("Not found");
        return;
      }
      if (url.searchParams.get("state") !== state) {
        res.writeHead(400).end("OAuth state mismatch");
        server.close();
        reject(new Error("OAuth state mismatch"));
        return;
      }
      const error = url.searchParams.get("error");
      if (error) {
        res.writeHead(400).end(`Authorization failed: ${error}`);
        server.close();
        reject(new Error(`Authorization failed: ${error}`));
        return;
      }
      const value = url.searchParams.get("code");
      if (!value) {
        res.writeHead(400).end("Missing authorization code");
        return;
      }
      res.writeHead(200, { "content-type": "text/plain" });
      res.end("Google Tasks authorization completed. You can close this tab.");
      server.close();
      resolve(value);
    } catch (error) {
      reject(error);
    }
  });

  server.on("error", reject);
  server.listen(port, "127.0.0.1", () => {
    console.log("Opening Google authorization in your browser...");
    console.log(auth.toString());
    openBrowser(auth.toString());
  });
});

const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
  method: "POST",
  headers: { "content-type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({
    client_id: client.client_id,
    client_secret: client.client_secret,
    code,
    code_verifier: codeVerifier,
    grant_type: "authorization_code",
    redirect_uri: redirectUri,
  }),
});

const token = await tokenResponse.json();
if (!tokenResponse.ok) {
  throw new Error(`Token exchange failed: ${JSON.stringify(token)}`);
}
if (!token.refresh_token) {
  throw new Error("Google did not return a refresh token. Revoke the prior grant and rerun with prompt=consent if necessary.");
}

console.log("\nAuthorization succeeded.");
console.log("Store the following values as Cloudflare Worker secrets. Never commit them to Git:\n");
console.log(`GOOGLE_CLIENT_ID=${client.client_id}`);
console.log(`GOOGLE_CLIENT_SECRET=${client.client_secret}`);
console.log(`GOOGLE_REFRESH_TOKEN=${token.refresh_token}`);
