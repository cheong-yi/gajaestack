// Explicit native Bun test binding. Earlier preloads/startup remain trusted.
import { check } from "./check";
const status = await check(false, true);
if (status !== 0) process.exit(status);
