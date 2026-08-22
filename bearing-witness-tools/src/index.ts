import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";
import { analyze, decide, replay } from "./cli.js";

export default defineToolPlugin({
  id: "bearing-witness-tools",
  name: "Bearing Witness Tools",
  description: "Local bearing vibration analysis via the Bearing Witness CLI.",
  tools: (tool) => [

    tool({
      name: "diagnose_bearing",
      description: "Full analysis of one window: status, evidence, and inspection draft.",
      parameters: Type.Object({
        condition: Type.String(),
        bearing: Type.String(),
        record: Type.Number(),
      }),
      execute: async ({ condition, bearing, record }) => {
        return analyze(condition, bearing, record);
      },
    }),

    tool({
      name: "check_blockers",
      description: "Why can't this window be analyzed or localized, trust state and refusal reasons only.",
      parameters: Type.Object({
        condition: Type.String(),
        bearing: Type.String(),
        record: Type.Number(),
      }),
      execute: async ({ condition, bearing, record }) => {
        const r = await analyze(condition, bearing, record);
        return {
          status: r.status,
          input_trust: r.input_trust ?? null,
          refusal_reasons: r.refusal_reasons,
        };
      },
    }),

    tool({
      name: "get_evidence",
      description: "Bearing fault evidence for one window, candidate families and both spectrum views.",
      parameters: Type.Object({
        condition: Type.String(),
        bearing: Type.String(),
        record: Type.Number(),
      }),
      execute: async ({ condition, bearing, record }) => {
        const r = await analyze(condition, bearing, record);
        return {
          candidate_families: r.candidate_families,
          ordinary_spectrum_evidence: r.ordinary_spectrum_evidence ?? null,
          envelope_evidence: r.envelope_evidence ?? null,
        };
      },
    }),

    tool({
      name: "submit_decision",
      description:
        "Approve, reject, or defer the inspection draft for one window. Only valid on a window whose " +
        "status is ANALYST_REVIEW_REQUIRED (call diagnose_bearing first). Requires human confirmation.",
      parameters: Type.Object({
        condition: Type.String(),
        bearing: Type.String(),
        record: Type.Number(),
        decision: Type.Union([Type.Literal("APPROVE"), Type.Literal("REJECT"), Type.Literal("DEFER")]),
        reason: Type.String(),
      }),
      execute: async ({ condition, bearing, record, decision, reason }) => {
        return decide(condition, bearing, record, decision, reason);
      },
    }),

    tool({
      name: "test_without_geometry",
      description: "Rerun analysis with bearing geometry marked unverified.",
      parameters: Type.Object({
        condition: Type.String(),
        bearing: Type.String(),
        record: Type.Number(),
      }),
      execute: async ({ condition, bearing, record }) => {
        return analyze(condition, bearing, record, { geometryUnverified: true });
      },
    }),

    tool({
      name: "replay_timeline",
      description: "Per-window status history for one bearing, from window 1 up to N.",
      parameters: Type.Object({
        condition: Type.String(),
        bearing: Type.String(),
        to: Type.Number(),
      }),
      execute: async ({ condition, bearing, to }) => {
        return replay(condition, bearing, to);
      },
    }),

  ],
});
