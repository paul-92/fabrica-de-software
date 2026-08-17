import { describe, expect, it } from "vitest";
import type { ProjectEngineeringEvidenceDto, ProjectValidationDto } from "./dtos";

describe("project engineering DTO contract", () => {
  it("accepts skipped validation and published idempotent no-op evidence", () => {
    const validation = { status: "skipped" } as const satisfies Pick<ProjectValidationDto, "status">;
    const evidence = {
      idempotent_noop_evidence: {
        prior_execution_id: "e-prior",
        workspace_fingerprint: "sha256:workspace",
        artifact_paths: ["README.md"],
      },
    } satisfies ProjectEngineeringEvidenceDto;

    expect(validation.status).toBe("skipped");
    expect(evidence.idempotent_noop_evidence.artifact_paths).toEqual(["README.md"]);
  });
});
