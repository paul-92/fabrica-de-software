import { ApiClient } from "./client";
import { loadApiConfig } from "./config";
import { FetchHttpTransport } from "./http";
import { IntelligentEngineeringClient } from "../services/intelligentEngineering";
import { MetricsClient } from "../services/metrics";
import { RunsClient } from "../services/runs";
import { ProjectsClient } from "../services/projects";
import { AIRuntimesClient } from "../services/aiRuntimes";

export type PlatformClients = Readonly<{
  intelligentEngineering: IntelligentEngineeringClient;
  runs: RunsClient;
  metrics: MetricsClient;
  projects: ProjectsClient;
  aiRuntimes: AIRuntimesClient;
}>;

export function createPlatformClients(): PlatformClients {
  const api = new ApiClient(loadApiConfig(), new FetchHttpTransport());
  return Object.freeze({
    intelligentEngineering: new IntelligentEngineeringClient(api),
    runs: new RunsClient(api),
    metrics: new MetricsClient(api),
    projects: new ProjectsClient(api),
    aiRuntimes: new AIRuntimesClient(api),
  });
}
