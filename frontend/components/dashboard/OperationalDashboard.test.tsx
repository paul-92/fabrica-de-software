// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { MetricsSummaryDto, RunDto } from "../../lib/api/dtos";
import type {
  DashboardData,
  DashboardLoader,
} from "../../lib/services/dashboard";
import { OperationalDashboard } from "./OperationalDashboard";
import { RunStatusBadge } from "./RunStatusBadge";
import { ApiNetworkError, ApiTimeoutError } from "../../lib/api/errors";

afterEach(cleanup);

const metrics: MetricsSummaryDto = {
  total_runs: 12,
  successful_runs: 7,
  failed_runs: 2,
  running_runs: 1,
  pending_runs: 2,
  cancelled_runs: 0,
  unknown_status_runs: 0,
  eligible_runs: 9,
  success_rate: 77.8,
  failure_rate: 22.2,
  duration: {
    count: 9,
    ignored_count: 3,
    minimum_seconds: 4,
    maximum_seconds: 180,
    average_seconds: 90,
    median_seconds: 80,
  },
};

function run(id: string, status = "failed"): RunDto {
  return {
    id,
    status,
    started_at: "2026-08-05T14:00:00Z",
    finished_at: "2026-08-05T14:01:30Z",
    project_id: "project-one",
    workflow_id: "workflow-one",
    stage_id: "analysis",
    provider_name: "provider-one",
    summary: "Execution summary",
    error: status === "failed" ? { type: "Failure", message: "Validation failed", details: {} } : null,
    metadata: {},
  };
}

function loaderWith(...results: Array<DashboardData | Error>): DashboardLoader {
  return {
    load: vi.fn(async () => {
      const result = results.shift();
      if (result instanceof Error) throw result;
      if (!result) throw new Error("No fake result configured");
      return result;
    }),
  };
}

describe("OperationalDashboard", () => {
  it("announces its loading state", () => {
    const loader: DashboardLoader = { load: () => new Promise(() => undefined) };

    render(<OperationalDashboard loader={loader} />);

    expect(screen.getByRole("status").textContent).toContain("Loading dashboard");
  });

  it("renders API metrics and recent runs", async () => {
    render(
      <OperationalDashboard
        loader={loaderWith({ metrics, recentRuns: [run("run-123")] })}
      />,
    );

    expect(await screen.findByText("run-123")).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
    expect(screen.getByText("7")).toBeTruthy();
    expect(screen.getByText("1.5 min")).toBeTruthy();
    expect(screen.getByText("project-one")).toBeTruthy();
    expect(screen.getByText("provider-one")).toBeTruthy();
    expect(screen.getByText("Validation failed")).toBeTruthy();
  });

  it("distinguishes a legitimate empty run list", async () => {
    render(
      <OperationalDashboard loader={loaderWith({ metrics, recentRuns: [] })} />,
    );

    expect(await screen.findByText("No executions yet")).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
    expect(screen.queryByText("Dashboard unavailable")).toBeNull();
  });

  it("shows a safe error without exposing internal details", async () => {
    render(
      <OperationalDashboard loader={loaderWith(new Error("secret stack"))} />,
    );

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText("Dashboard unavailable")).toBeTruthy();
    expect(document.body.textContent).not.toContain("secret stack");
  });

  it.each([
    new ApiNetworkError("Unable to communicate with the API.", new TypeError("Failed to fetch")),
    new ApiTimeoutError(50, new DOMException("Aborted", "AbortError")),
  ])("leaves loading and shows an error when the API request fails", async (error) => {
    render(<OperationalDashboard loader={loaderWith(error)} />);

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByText("Loading dashboard")).toBeNull();
  });

  it("loads again when the user retries", async () => {
    const loader = loaderWith(
      new Error("offline"),
      { metrics, recentRuns: [run("run-after-retry", "succeeded")] },
    );
    render(<OperationalDashboard loader={loader} />);
    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));

    expect(await screen.findByText("run-after-retry")).toBeTruthy();
    await waitFor(() => expect(loader.load).toHaveBeenCalledTimes(2));
  });

  it("renders status as text rather than color alone", () => {
    render(<RunStatusBadge status="failed" />);

    expect(screen.getByText("Failed").textContent).toBe("Failed");
  });
});
