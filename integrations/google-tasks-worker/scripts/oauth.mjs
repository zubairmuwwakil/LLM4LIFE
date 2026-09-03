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
const client = credentials.installed;
if (!client?.client_id || !client?.client_secret) {
  if (credentials.web) {
    throw new Error(
      "This JSON is for a Google OAuth Web application. Create an OAuth Client ID with Application type = Desktop app, download that JSON, and rerun this command. Do not manually add a loopback redirect URI to a Web client for this helper.",
    );
  }
  throw new Error(
    "Expected a Google OAuth Desktop app client JSON containing an installed client_id and client_secret.",
  );
}

const scope = "https://www.googleapis.com/auth/tasks";
const state = randomBytes(24).toString("hex");
const codeVerifier = randomBytes(48).toString("base64url");
const codeChallenge = createHash("sha256").update(codeVerifier).digest("base64url");

function openBrowser(url) {
  const command = process.platform === "darwin" ? "open" : process.platform === "win32" ? "cmd" : "xdg-open";
  const args = process.platform === "win32" ? ["/c", "start", "", url] : [url];
  const child = spawn(command, args, { detached: true, stdio: "ignore" });
  child.unref();
}

const server = http.createServer();
await new Promise((resolve, reject) => {
  server.once("error", reject);
  // Port 0 asks the OS for an available local port, which is the recommended
  // loopback pattern for installed desktop OAuth clients.
  server.listen(0, "127.0.0.1", resolve);
});

const address = server.address();
if (!address || typeof address === "string") {
  server.close();
  throw new Error("Could not allocate a local OAuth callback port.");
}

const redirectUri = `http://127.0.0.1:${address.port}`;

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

const codePromise = new Promise((resolve, reject) => {
  server.on("request", (req, res) => {
    try {
      const url = new URL(req.url, redirectUri);
      if (url.pathname !== "/") {
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
      server.close();
      reject(error);
    }
  });
});

console.log("Opening Google authorization in your browser...");
console.log(auth.toString());
openBrowser(auth.toString());

const code = await codePromise;

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
  throw new Error(
    "Google did not return a refresh token. Revoke the prior grant and rerun with prompt=consent if necessary.",
  );
}

console.log("\nAuthorization succeeded.");
console.log("Store the following values as Cloudflare Worker secrets. Never commit them to Git:\n");
console.log(`GOOGLE_CLIENT_ID=${client.client_id}`);
console.log(`GOOGLE_CLIENT_SECRET=${client.client_secret}`);
console.log(`GOOGLE_REFRESH_TOKEN=${token.refresh_token}`);