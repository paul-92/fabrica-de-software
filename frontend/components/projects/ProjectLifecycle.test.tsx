// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { ProjectLifecycle } from "./ProjectLifecycle";
import { render, screen } from "@testing-library/react";
describe("project lifecycle",()=>{ it("uses backend state as source of truth",()=>{ render(<ProjectLifecycle projectName="P" state={{project_id:"p",phase:"DEVELOPMENT",phase_status:"blocked",current_sprint:"Sprint 1",blocker:"Deps",next_action:"Approve",updated_at:"2026-01-01",version:2}}/>); expect(screen.getByText("Desenvolvimento")).toBeTruthy(); expect(screen.getByText("Sprint 1")).toBeTruthy(); expect(screen.getByText("Deps")).toBeTruthy(); }); it("handles loading and error",()=>{ const view=render(<ProjectLifecycle projectName="P" state={null} loading/>); expect(screen.getByText(/Carregando/)).toBeTruthy(); view.rerender(<ProjectLifecycle projectName="P" state={null} error/>); expect(screen.getByRole("alert")).toBeTruthy(); }); });
