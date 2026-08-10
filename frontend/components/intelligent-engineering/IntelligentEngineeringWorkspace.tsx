"use client";

import { FormEvent, useMemo, useState } from "react";
import type { IntelligentEngineeringRequestDto, IntelligentEngineeringResponseDto } from "../../lib/api/dtos";
import { createIntelligentEngineeringWorkspaceExecutor, type IntelligentEngineeringWorkspaceExecutor } from "../../lib/services/intelligentEngineeringWorkspace";
import { Button } from "../Button";
import { Card } from "../Card";
import { PageHeader } from "../layout/PageHeader";
import { EngineeringResult } from "./EngineeringResult";

type SubmissionState = "idle" | "submitting" | "success" | "error";

export function IntelligentEngineeringWorkspace({ executor }: { executor?: IntelligentEngineeringWorkspaceExecutor }) {
  const effectiveExecutor = useMemo(() => executor ?? createIntelligentEngineeringWorkspaceExecutor(), [executor]);
  const [goal, setGoal] = useState("");
  const [objective, setObjective] = useState("");
  const [failureSummary, setFailureSummary] = useState("");
  const [targetPath, setTargetPath] = useState("");
  const [replacementContent, setReplacementContent] = useState("");
  const [testPaths, setTestPaths] = useState("tests");
  const [state, setState] = useState<SubmissionState>("idle");
  const [response, setResponse] = useState<IntelligentEngineeringResponseDto | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state === "submitting") return;
    if (![goal, objective, failureSummary, targetPath, replacementContent].every((value) => value.trim())) {
      setValidationError("Preencha todos os campos obrigatórios antes de executar.");
      return;
    }
    setValidationError(null); setState("submitting"); setResponse(null);
    const normalizedTargetPath = targetPath.trim();
    const request: IntelligentEngineeringRequestDto = {
      planning_request: { goal: goal.trim(), context: { objective: objective.trim() } },
      knowledge_context: { learned_entries: [], knowledge_count: 0 },
      engineering_request: {
        analysis: {
          summary: failureSummary.trim(),
          affected_paths: [normalizedTargetPath],
        },
        replacement_contents: {
          [normalizedTargetPath]: replacementContent,
        },
        test_paths: testPaths.split(",").map((path) => path.trim()).filter(Boolean),
      },
    };
    try {
      const result = await effectiveExecutor.execute(request);
      setResponse(result); setState("success");
    } catch {
      setState("error");
    }
  }

  return <div className="page-stack">
    <PageHeader eyebrow="Engenharia" title="Engenharia inteligente" description="Defina um objetivo para planejamento, reparo e reflexão controlados pela plataforma." />
    <Card title="Solicitação de engenharia" eyebrow="Executar">
      <form className="engineering-form" onSubmit={submit}>
        <label>Objetivo de engenharia<span>Obrigatório</span><textarea value={goal} onChange={(event) => setGoal(event.target.value)} disabled={state === "submitting"} /></label>
        <label>Objetivo do planejamento<span>Obrigatório</span><textarea value={objective} onChange={(event) => setObjective(event.target.value)} disabled={state === "submitting"} /></label>
        <label>Resumo da análise da falha<span>Obrigatório</span><textarea value={failureSummary} onChange={(event) => setFailureSummary(event.target.value)} disabled={state === "submitting"} /></label>
        <div className="engineering-form__columns">
          <label>Caminho do arquivo a substituir<span>Obrigatório</span><input value={targetPath} onChange={(event) => setTargetPath(event.target.value)} disabled={state === "submitting"} /></label>
          <label>Caminhos de teste<span>Separados por vírgulas</span><input value={testPaths} onChange={(event) => setTestPaths(event.target.value)} disabled={state === "submitting"} /></label>
        </div>
        <label>Conteúdo explícito da substituição<span>Obrigatório</span><textarea className="engineering-form__code" value={replacementContent} onChange={(event) => setReplacementContent(event.target.value)} disabled={state === "submitting"} /></label>
        {validationError ? <p className="engineering-form__error" role="alert">{validationError}</p> : null}
        {state === "error" ? <p className="engineering-form__error" role="alert">Não foi possível concluir a solicitação. Revise os dados e tente novamente.</p> : null}
        <Button type="submit" disabled={state === "submitting"}>{state === "submitting" ? "Executando…" : state === "error" ? "Tentar novamente" : "Executar engenharia inteligente"}</Button>
      </form>
    </Card>
    {state === "success" && response ? <EngineeringResult response={response} /> : null}
  </div>;
}
