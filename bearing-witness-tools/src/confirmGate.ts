import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

// Separate entry module from index.ts on purpose: this only registers a
// trusted-tool policy (task 3.2), it does not touch the five working tools'
// definitions or execute paths.
const GATED_TOOL = "submit_decision";
const POLICY_ID = "bearing-witness-confirm-submit-decision";

const entry: ReturnType<typeof definePluginEntry> = definePluginEntry({
  id: "bearing-witness-tools",
  name: "Bearing Witness Tools",
  description: "Local bearing vibration analysis via the Bearing Witness CLI.",
  register: (api) => {
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
  },
});

export default entry;
