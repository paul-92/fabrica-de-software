import { ApiClient } from "./client";
import { loadApiConfig } from "./config";
import { FetchHttpTransport } from "./http";
import { IntelligentEngineeringClient } from "../services/intelligentEngineering";
import { MetricsClient } from "../services/metrics";
import { RunsClient } from "../services/runs";
import { ProjectsClient } from "../services/projects";
import { AIRuntimesClient } from "../services/aiRuntimes";
import { ProjectHistoryClient, ProjectRuntimeClient } from "../services/projectRuntime";
import { ProjectWorkspaceClient } from "../services/projectWorkspace";
import { AgentsClient } from "../services/agents";
import { SequentialQualityClient } from "../services/sequentialQuality";
import { BrandingClient } from "../services/branding";

export type PlatformClients = Readonly<{
  intelligentEngineering: IntelligentEngineeringClient;
  runs: RunsClient;
  metrics: MetricsClient;
  projects: ProjectsClient;
  aiRuntimes: AIRuntimesClient;
  projectRuntime: ProjectRuntimeClient;
  projectHistory: ProjectHistoryClient;
  projectWorkspace: ProjectWorkspaceClient;
  agents: AgentsClient;
  sequentialQuality: SequentialQualityClient;
  branding: BrandingClient;
}>;

export function createPlatformClients(): PlatformClients {
  const api = new ApiClient(loadApiConfig(), new FetchHttpTransport());
  return Object.freeze({
    intelligentEngineering: new IntelligentEngineeringClient(api),
    runs: new RunsClient(api),
    metrics: new MetricsClient(api),
    projects: new ProjectsClient(api),
    aiRuntimes: new AIRuntimesClient(api),
    projectRuntime: new ProjectRuntimeClient(api),
    projectHistory: new ProjectHistoryClient(api),
    projectWorkspace: new ProjectWorkspaceClient(api),
    agents: new AgentsClient(api),
    sequentialQuality: new SequentialQualityClient(api),
    branding: new BrandingClient(api),
  });
}
