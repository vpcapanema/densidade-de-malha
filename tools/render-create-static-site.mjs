/*
 * Cria um Static Site no Render via API.
 *
 * Uso:
 *   node tools/render-create-static-site.mjs --owner-name "<NOME_DO_WORKSPACE>"
 *
 * Pré-requisito:
 *   set RENDER_API_KEY=rnd_...
 */

const API_BASE = "https://api.render.com/v1";

function getArg(flag) {
  const idx = process.argv.indexOf(flag);
  if (idx === -1) return undefined;
  return process.argv[idx + 1];
}

function hasFlag(flag) {
  return process.argv.includes(flag);
}

async function apiRequest(path, { method = "GET", body } = {}) {
  const apiKey = process.env.RENDER_API_KEY;
  if (!apiKey) {
    throw new Error(
      "RENDER_API_KEY não está definido. Crie um API key no Render e defina a env var RENDER_API_KEY."
    );
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${apiKey}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json") && text ? JSON.parse(text) : text;

  if (!res.ok) {
    const msg = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    throw new Error(`Render API ${method} ${path} falhou (${res.status}): ${msg}`);
  }

  return data;
}

async function main() {
  const ownerId = getArg("--owner-id");
  const ownerName = getArg("--owner-name");

  if (!ownerId && !ownerName) {
    throw new Error(
      "Informe --owner-name \"<NOME_DO_WORKSPACE>\" (recomendado) ou --owner-id <ID>."
    );
  }

  const name = getArg("--name") || "densidade-de-malha-relatorio";
  const repo =
    getArg("--repo") || "https://github.com/vpcapanema/densidade-de-malha";
  const branch = getArg("--branch") || "main";
  const rootDir = getArg("--root-dir") || "";
  const publishPath = getArg("--publish-path") || "relatorio";
  const buildCommand = getArg("--build-command") || "";
  const autoDeploy = getArg("--auto-deploy") || "yes";

  let resolvedOwnerId = ownerId;
  if (!resolvedOwnerId) {
    const owners = await apiRequest("/owners", { method: "GET" });
    const matches = owners.filter(
      (o) => (o?.owner?.name || "").toLowerCase() === ownerName.toLowerCase()
    );
    if (matches.length === 0) {
      const names = owners
        .map((o) => o?.owner?.name)
        .filter(Boolean)
        .sort();
      throw new Error(
        `Workspace não encontrado: "${ownerName}". Disponíveis: ${names.join(", ")}`
      );
    }
    if (matches.length > 1) {
      throw new Error(
        `Workspace ambíguo: "${ownerName}". Use --owner-id para escolher exatamente.`
      );
    }
    resolvedOwnerId = matches[0].owner.id;
  }

  const payload = {
    type: "static_site",
    name,
    ownerId: resolvedOwnerId,
    repo,
    branch,
    autoDeploy,
    ...(rootDir ? { rootDir } : {}),
    serviceDetails: {
      buildCommand,
      publishPath,
    },
  };

  if (hasFlag("--print-payload")) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }

  const created = await apiRequest("/services", { method: "POST", body: payload });
  const service = created?.service;

  process.stdout.write(
    JSON.stringify(
      {
        serviceId: service?.id,
        name: service?.name,
        dashboardUrl: service?.dashboardUrl,
        url: service?.serviceDetails?.url,
        deployId: created?.deployId,
      },
      null,
      2
    ) + "\n"
  );
}

main().catch((err) => {
  process.stderr.write(`${err.message}\n`);
  process.exit(1);
});
