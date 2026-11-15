'use strict';
// No dependencies. Mirrors deploy-pages' Results ArtifactService/ListArtifacts
// read, plus REST provenance checks. Never calls a deployment/collection API.
const REPO = 'cornhskr1/active-offerings-review';
function backendRequest(token, base) {
  const url = new URL(base);
  if (url.protocol !== 'https:' || !url.hostname.endsWith('.actions.githubusercontent.com') || url.username || url.password || url.port || url.search || url.hash) throw Error('Untrusted Results origin');
  const claim = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8'));
  const scopes = (claim.scp || '').split(' ').filter(s => s.startsWith('Actions.Results:'));
  if (scopes.length !== 1) throw Error('Results scope unavailable');
  const parts = scopes[0].split(':');
  const uuid = /^[0-9a-f-]{36}$/i;
  if (parts.length !== 3 || !uuid.test(parts[1]) || !uuid.test(parts[2])) throw Error('Invalid backend identity');
  return {url: new URL('/twirp/github.actions.results.api.v1.ArtifactService/ListArtifacts', url).href,
    body: {workflow_run_backend_id: parts[1], workflow_job_run_backend_id: parts[2]}};
}
function resultsReady(payload, id) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw Error('Results list unavailable');
  if (payload.artifacts === undefined && Object.keys(payload).length === 0) return false; // protobuf empty repeated field
  if (!Array.isArray(payload.artifacts)) throw Error('Results list unavailable');
  const rows = payload.artifacts.filter(a => a && a.name === 'github-pages');
  if (!rows.length) return false;
  if (rows.length !== 1 || String(rows[0].database_id ?? rows[0].databaseId) !== id || (rows[0].database_id !== undefined && rows[0].databaseId !== undefined && String(rows[0].database_id) !== String(rows[0].databaseId)) || !(Number(rows[0].size) > 0)) throw Error('Results artifact mismatch or ambiguity');
  return true;
}
function restReady(payload, id, runId, sha) {
  if (!payload || !Array.isArray(payload.artifacts) || payload.total_count !== payload.artifacts.length) throw Error('REST artifact list incomplete');
  if (!payload.artifacts.length) return false;
  const a = payload.artifacts[0];
  if (payload.artifacts.length !== 1 || String(a.id) !== id || a.name !== 'github-pages' || a.expired !== false || !(a.size_in_bytes > 0) || String(a.workflow_run?.id) !== runId || a.workflow_run?.head_branch !== 'main' || a.workflow_run?.head_sha !== sha) throw Error('REST artifact provenance mismatch');
  return true;
}
async function request(url, token, body) {
  let response;
  try {
    response = await fetch(url, {method: body ? 'POST' : 'GET', redirect: 'error', signal: AbortSignal.timeout(8000), headers: {Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28'}, ...(body ? {body: JSON.stringify(body)} : {})});
  } catch (_) { throw Object.assign(Error('Artifact transport unavailable'), {retryable: true}); }
  if (!response.ok) throw Object.assign(Error(`Artifact API HTTP ${response.status}`), {retryable: [404,429,500,502,503,504].includes(response.status)});
  const raw = await response.text();
  if (raw.length > 1000000) throw Error('Artifact response too large');
  return JSON.parse(raw);
}
async function waitForArtifact(readResults, readRest, id, runId, sha, sleep = ms => new Promise(r => setTimeout(r, ms))) {
  for (let attempt = 0; attempt < 7; attempt++) {
    try {
      if (resultsReady(await readResults(), id) && restReady(await readRest(), id, runId, sha)) return;
    } catch (e) { if (!e.retryable) throw e; }
    if (attempt < 6) await sleep(10000);
  }
  throw Error('Exact uploaded Pages artifact not visible after bounded wait');
}
async function main(env = process.env) {
  const id = env['INPUT_ARTIFACT-ID'], runId = env.GITHUB_RUN_ID, sha = env.GITHUB_SHA;
  if (env.GITHUB_REPOSITORY !== REPO || !/^[1-9][0-9]*$/.test(id || '') || !/^[1-9][0-9]*$/.test(runId || '') || !/^[0-9a-f]{40}$/.test(sha || '') || !env['INPUT_GITHUB-TOKEN'] || !env.ACTIONS_RUNTIME_TOKEN) throw Error('Artifact verification identity missing');
  const results = backendRequest(env.ACTIONS_RUNTIME_TOKEN, env.ACTIONS_RESULTS_URL);
  await waitForArtifact(() => request(results.url, env.ACTIONS_RUNTIME_TOKEN, results.body),
    () => request(`https://api.github.com/repos/${REPO}/actions/runs/${runId}/artifacts?name=github-pages&per_page=100`, env['INPUT_GITHUB-TOKEN']), id, runId, sha);
  console.log(`Exact Pages artifact ${id} visible to deploy-pages and verified for run ${runId}.`);
}
module.exports = {backendRequest, resultsReady, restReady, waitForArtifact};
if (require.main === module) main().catch(() => { console.error('Artifact readiness failed closed; no deployment retried.'); process.exitCode = 1; });
