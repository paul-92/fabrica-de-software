export class ApiError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiError";
  }
}

export class ApiHttpError extends ApiError {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly responseBody?: unknown,
  ) {
    super(message);
    this.name = "ApiHttpError";
  }
}

export class ApiNetworkError extends ApiError {
  constructor(message: string, cause: unknown) {
    super(message, { cause });
    this.name = "ApiNetworkError";
  }
}

export class ApiTimeoutError extends ApiNetworkError {
  constructor(public readonly timeoutMs: number, cause: unknown) {
    super(`API request timed out after ${timeoutMs} ms.`, cause);
    this.name = "ApiTimeoutError";
  }
}

export class ApiResponseError extends ApiError {
  constructor(message: string, public readonly responseBody?: unknown) {
    super(message);
    this.name = "ApiResponseError";
  }
}
