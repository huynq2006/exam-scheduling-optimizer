import fs from "node:fs";
import path from "node:path";
import mysql from "mysql2/promise";

/**
 * Káº¿t ná»‘i MySQL cho phÃ­a server (route handlers).
 *
 * Chuá»—i káº¿t ná»‘i láº¥y tá»« `DB_SLAVE_URL` / `DB_MASTER_URL`. Next.js chá»‰ tá»± náº¡p
 * .env trong thÆ° má»¥c `src/ui`, cÃ²n .env tháº­t cá»§a dá»± Ã¡n náº±m á»Ÿ gá»‘c repo, nÃªn ta
 * Ä‘á»c thá»§ cÃ´ng file Ä‘Ã³ khi biáº¿n mÃ´i trÆ°á»ng chÆ°a cÃ³.
 */

type Role = "master" | "slave";

interface DbConfig {
  host: string;
  port: number;
  user: string;
  password: string;
  database: string;
}

let rootEnvLoaded = false;

function loadRootEnv() {
  if (rootEnvLoaded) return;
  rootEnvLoaded = true;

  const candidates = [
    path.resolve(process.cwd(), "..", "..", ".env"),
    path.resolve(process.cwd(), "..", ".env"),
    path.resolve(process.cwd(), ".env"),
  ];

  for (const file of candidates) {
    if (!fs.existsSync(file)) continue;
    const text = fs.readFileSync(file, "utf8");
    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq < 0) continue;
      const key = trimmed.slice(0, eq).trim();
      const value = trimmed.slice(eq + 1).trim();
      if (key && process.env[key] === undefined) process.env[key] = value;
    }
    break;
  }
}

/**
 * `mysql+pymysql://app_user:App_Pass@123@127.0.0.1:23307/quan_ly_thi`
 * Máº­t kháº©u cÃ³ thá»ƒ chá»©a '@', nÃªn tÃ¡ch theo dáº¥u '@' CUá»I CÃ™NG chá»© khÃ´ng dÃ¹ng new URL().
 */
function parseDbUrl(raw: string): DbConfig {
  let rest = raw.trim();
  const schemeIdx = rest.indexOf("://");
  if (schemeIdx >= 0) rest = rest.slice(schemeIdx + 3);

  const at = rest.lastIndexOf("@");
  if (at < 0) throw new Error("Chuá»—i káº¿t ná»‘i DB khÃ´ng há»£p lá»‡: thiáº¿u '@'");

  const credentials = rest.slice(0, at);
  const hostPart = rest.slice(at + 1);

  const colon = credentials.indexOf(":");
  const user = colon >= 0 ? credentials.slice(0, colon) : credentials;
  const password = colon >= 0 ? credentials.slice(colon + 1) : "";

  const slash = hostPart.indexOf("/");
  const hostPort = slash >= 0 ? hostPart.slice(0, slash) : hostPart;
  const database = slash >= 0 ? hostPart.slice(slash + 1) : "";

  const portSep = hostPort.lastIndexOf(":");
  const host = portSep >= 0 ? hostPort.slice(0, portSep) : hostPort;
  const port = portSep >= 0 ? Number(hostPort.slice(portSep + 1)) : 3306;

  return { host, port, user, password, database };
}

function configFor(role: Role): DbConfig {
  loadRootEnv();
  const key = role === "master" ? "DB_MASTER_URL" : "DB_SLAVE_URL";
  const raw = process.env[key];
  if (!raw) {
    throw new Error(
      `Thiáº¿u biáº¿n mÃ´i trÆ°á»ng ${key}. ThÃªm vÃ o .env á»Ÿ gá»‘c dá»± Ã¡n, vÃ­ dá»¥: ` +
        `${key}=mysql+pymysql://app_user:password@127.0.0.1:23307/quan_ly_thi`,
    );
  }
  return parseDbUrl(raw);
}

const pools = new Map<Role, mysql.Pool>();

/**
 * Pool pháº£i sá»‘ng qua cÃ¡c láº§n hot reload.
 *
 * Next.js dev náº¡p láº¡i module nÃ y má»—i khi cÃ³ file thay Ä‘á»•i. Náº¿u Ä‘á»ƒ pool trong
 * biáº¿n module thÆ°á»ng, má»—i láº§n reload sáº½ táº¡o má»™t pool má»›i mÃ  pool cÅ© váº«n giá»¯
 * connection Ä‘ang má»Ÿ â€” sá»­a vÃ i file lÃ  MySQL háº¿t `max_connections` vÃ  má»i
 * truy váº¥n tráº£ vá» "Too many connections". Neo vÃ o globalThis Ä‘á»ƒ cáº£ tiáº¿n trÃ¬nh
 * dÃ¹ng chung Ä‘Ãºng má»™t pool cho má»—i role.
 */
const globalForPools = globalThis as unknown as {
  __examSchedulerPools?: Map<Role, mysql.Pool>;
};

function poolRegistry(): Map<Role, mysql.Pool> {
  if (!globalForPools.__examSchedulerPools) {
    globalForPools.__examSchedulerPools = pools;
  }
  return globalForPools.__examSchedulerPools;
}

export function getPool(role: Role = "slave"): mysql.Pool {
  const registry = poolRegistry();
  const existing = registry.get(role);
  if (existing) return existing;

  const cfg = configFor(role);
  const pool = mysql.createPool({
    ...cfg,
    charset: "utf8mb4",
    waitForConnections: true,
    connectionLimit: 5,
    // Tráº£ connection vá» pool sau khi ráº£nh, Ä‘á»ƒ khÃ´ng giá»¯ káº¿t ná»‘i vÃ´ Ã­ch.
    maxIdle: 2,
    idleTimeout: 60_000,
    // DATE/TIME tráº£ vá» chuá»—i thay vÃ¬ Ä‘á»‘i tÆ°á»£ng Date Ä‘á»ƒ giá»¯ nguyÃªn ngÃ y thi.
    dateStrings: true,
  });
  registry.set(role, pool);
  return pool;
}

export async function query<T = Record<string, unknown>>(
  sql: string,
  params: unknown[] = [],
  role: Role = "slave",
): Promise<T[]> {
  const [rows] = await getPool(role).query(sql, params);
  return rows as T[];
}
