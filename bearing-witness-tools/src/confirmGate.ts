import type { OpenClawPluginApi } from "openclaw/plugin-sdk/plugin-entry";

// Kept as a separate module from index.ts on purpose: this only registers a
// trusted-tool policy (task 3.2), it does not touch the five working tools'
// definitions or execute paths.
//
// NOTE: this used to be its own `definePluginEntry` plugin, loaded as a second
// entry in package.json's `openclaw.extensions` array (["./dist/index.js",
// "./dist/confirmGate.js"]). OpenClaw's plugin loader only loads the first
// listed extension for a path-installed plugin, so that second entry was
// silently never imported — the policy was registered in source and in the
// manifest's static `contracts` field, but never at runtime. `submit_decision`
// fired with no confirmation gate as a result. Fixed by exporting a plain
// registration function that index.ts's single loaded entry point calls
// directly — see `registerConfirmGate` in index.ts.
export const GATED_TOOL = "submit_decision";
export const POLICY_ID = "bearing-witness-confirm-submit-decision";

export function registerConfirmGate(api: OpenClawPluginApi): void {
  api.registerTrustedToolPolicy({
    id: POLICY_ID,
    description: "Require human confirmation before submit_decision records an inspection decision.",
    evaluate: (event) => {
      if (event.toolName !== GATED_TOOL) return;
      const { decision, condition, bearing, record } = event.params as {
        decision?: string;
        condition?: string;
        bearing?: string;
        record?: number;
      };
      return {
        requireApproval: {
          title: `Confirm ${decision ?? "decision"} — ${condition ?? "?"}/${bearing ?? "?"} w${record ?? "?"}`,
          description:
            "submit_decision writes a human review (APPROVE/REJECT/DEFER) to the decision store. " +
            "The agent cannot undo this.",
          severity: "warning",
          allowedDecisions: ["allow-once", "allow-always", "deny"],
        },
      };
    },
  });
}
