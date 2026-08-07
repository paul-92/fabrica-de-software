import type {
  IntelligentEngineeringRequestDto,
  IntelligentEngineeringResponseDto,
} from "../api/dtos";
import { createPlatformClients, type PlatformClients } from "../api";

type IntelligentEngineeringClients = Readonly<{
  intelligentEngineering: Pick<PlatformClients["intelligentEngineering"], "execute">;
}>;

export interface IntelligentEngineeringWorkspaceExecutor {
  execute(request: IntelligentEngineeringRequestDto): Promise<IntelligentEngineeringResponseDto>;
}

export class IntelligentEngineeringWorkspaceService implements IntelligentEngineeringWorkspaceExecutor {
  constructor(private readonly client: IntelligentEngineeringClients["intelligentEngineering"]) {}

  execute(request: IntelligentEngineeringRequestDto): Promise<IntelligentEngineeringResponseDto> {
    return this.client.execute(request);
  }
}

export function createIntelligentEngineeringWorkspaceExecutor(
  clientsFactory: () => IntelligentEngineeringClients = createPlatformClients,
): IntelligentEngineeringWorkspaceExecutor {
  let service: IntelligentEngineeringWorkspaceService | undefined;
  const getService = () => {
    service ??= new IntelligentEngineeringWorkspaceService(clientsFactory().intelligentEngineering);
    return service;
  };
  return { execute: (request) => getService().execute(request) };
}
